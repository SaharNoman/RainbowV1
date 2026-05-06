from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.database import SessionLocal
from app.models import Inventory
from app.notifier import send_low_stock_email, send_low_sales_email
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import sqlite3, os

# Run startup (import Excel data if DB is empty)
from startup import setup_database
setup_database()

app = FastAPI(title="Grocery Inventory API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve frontend static files
import os
if os.path.exists("frontend"):
    app.mount("/static", StaticFiles(directory="frontend"), name="static")

@app.get("/", response_class=FileResponse)
async def serve_frontend():
    return FileResponse("frontend/index.html", media_type="text/html")

@app.get("/dashboard", response_class=FileResponse)
async def serve_dashboard():
    return FileResponse("frontend/index.html", media_type="text/html")

DB_PATH = "inventory.db"

def get_raw_conn():
    return sqlite3.connect(DB_PATH)


# ════════════════════════════════════════════════════════
#  INVENTORY ENDPOINTS
# ════════════════════════════════════════════════════════

def fetch_low_sales(month: str, store=None):
    conn = get_raw_conn()
    cur  = conn.cursor()
    if store:
        cur.execute(
            "SELECT id, article, category, store_name, quantity, threshold FROM sales WHERE month=? AND store_name=? AND threshold>0 AND quantity<threshold ORDER BY quantity",
            (month, store)
        )
    else:
        cur.execute(
            "SELECT id, article, category, store_name, quantity, threshold FROM sales WHERE month=? AND threshold>0 AND quantity<threshold ORDER BY quantity",
            (month,)
        )
    rows = cur.fetchall()
    conn.close()
    return [
        {
            "id": r[0],
            "article_name": r[1],
            "category": r[2],
            "store_name": r[3],
            "quantity": r[4],
            "threshold": r[5],
            "deficit": round(r[5] - r[4], 2)
        }
        for r in rows
    ]


def fetch_low_stock(store=None):
    db = SessionLocal()
    query = db.query(Inventory)
    if store:
        query = query.filter(Inventory.store_name == store)
    items = query.all()
    db.close()
    alerts = [
        {
            "id": i.id,
            "item_name": i.item_name,
            "category": i.category,
            "store_name": i.store_name,
            "current_stock": i.current_stock,
            "threshold": i.threshold,
            "deficit": round(i.threshold - i.current_stock, 2),
        }
        for i in items if i.current_stock < i.threshold
    ]
    alerts.sort(key=lambda x: x["current_stock"])
    return alerts


def scheduled_alert():
    print(f"[{datetime.now()}] Running scheduled alerts...")

    # Stock alert
    stock_result = send_low_stock_email(fetch_low_stock())
    print(f"[{datetime.now()}] Stock alert: {stock_result}")

    # Sales alert — use latest month
    conn = get_raw_conn()
    cur  = conn.cursor()
    cur.execute("SELECT DISTINCT month FROM sales")
    months = [r[0] for r in cur.fetchall()]
    conn.close()

    month_order = {'JAN':1,'FEB':2,'MAR':3,'APR':4,'MAY':5,'JUN':6,'JUL':7,'AUG':8,'SEP':9,'OCT':10,'NOV':11,'DEC':12}
    def sort_key(m):
        parts = m.split('-')
        return (int(parts[1]), month_order.get(parts[0][:3].upper(), 0))
    months.sort(key=sort_key)
    latest_month = months[-1] if months else None

    if latest_month:
        sales_result = send_low_sales_email(fetch_low_sales(latest_month), latest_month)
        print(f"[{datetime.now()}] Sales alert: {sales_result}")

scheduler = BackgroundScheduler()
scheduler.add_job(scheduled_alert, "cron", hour=20, minute=0)
scheduler.start()


@app.get("/health")
def health():
    db = SessionLocal()
    count = db.query(Inventory).count()
    db.close()
    return {"status": "ok", "total_records": count}


@app.get("/stores")
def get_stores():
    db = SessionLocal()
    stores = db.query(Inventory.store_name).distinct().order_by(Inventory.store_name).all()
    db.close()
    return [s[0] for s in stores]


@app.get("/dashboard/stock-summary")
def stock_summary():
    db = SessionLocal()
    items = db.query(Inventory).all()
    db.close()
    summary = {}
    for i in items:
        s = i.store_name
        if s not in summary:
            summary[s] = {"total_items": 0, "low_stock_items": 0}
        summary[s]["total_items"] += 1
        if i.current_stock < i.threshold:
            summary[s]["low_stock_items"] += 1
    return summary


@app.get("/inventory")
def get_inventory(store: str = Query(None)):
    db = SessionLocal()
    query = db.query(Inventory)
    if store:
        query = query.filter(Inventory.store_name == store)
    items = query.order_by(Inventory.category, Inventory.item_name).all()
    db.close()
    return [
        {
            "id": i.id,
            "item_name": i.item_name,
            "category": i.category,
            "store_name": i.store_name,
            "current_stock": i.current_stock,
            "threshold": i.threshold,
            "is_low": i.current_stock < i.threshold,
        }
        for i in items
    ]


@app.get("/low-stock")
def low_stock(store: str = Query(None)):
    return fetch_low_stock(store)


@app.put("/inventory/{item_id}/threshold")
def update_threshold(item_id: int, threshold: float = Query(...)):
    db = SessionLocal()
    item = db.query(Inventory).filter(Inventory.id == item_id).first()
    if not item:
        db.close()
        return {"error": "Item not found"}
    item.threshold = threshold
    db.commit()
    db.close()
    return {"message": "Threshold updated", "item_id": item_id, "new_threshold": threshold}


@app.post("/notify/send-now")
def send_now(store: str = Query(None), month: str = Query(None)):
    # Send stock alert
    stock_result = send_low_stock_email(fetch_low_stock(store))

    # Determine month for sales alert
    if not month:
        conn = get_raw_conn()
        cur  = conn.cursor()
        cur.execute("SELECT DISTINCT month FROM sales")
        months = [r[0] for r in cur.fetchall()]
        conn.close()
        mo = {'JAN':1,'FEB':2,'MAR':3,'APR':4,'MAY':5,'JUN':6,'JUL':7,'AUG':8,'SEP':9,'OCT':10,'NOV':11,'DEC':12}
        months.sort(key=lambda m: (int(m.split('-')[1]), mo.get(m.split('-')[0][:3].upper(), 0)))
        month = months[-1] if months else None

    sales_result = send_low_sales_email(fetch_low_sales(month, store), month) if month else {"status": "skipped", "message": "No month found"}

    # Combine results
    stock_sent = stock_result.get("status") == "sent"
    sales_sent = sales_result.get("status") == "sent"
    total = (stock_result.get("items_reported", 0) or 0) + (sales_result.get("items_reported", 0) or 0)

    if stock_result.get("status") == "error":
        return stock_result
    if sales_result.get("status") == "error":
        return sales_result

    return {
        "status": "sent" if (stock_sent or sales_sent) else "skipped",
        "message": f"Stock alert: {stock_result['status']} | Sales alert ({month}): {sales_result['status']}",
        "items_reported": total,
        "stock": stock_result,
        "sales": sales_result
    }


@app.get("/notify/preview")
def notify_preview(store: str = Query(None)):
    low_items = fetch_low_stock(store)
    return {
        "total_low_items": len(low_items),
        "stores_affected": list(set(i["store_name"] for i in low_items)),
        "items": low_items
    }


# ════════════════════════════════════════════════════════
#  SALES ENDPOINTS
# ════════════════════════════════════════════════════════

@app.get("/sales/months")
def get_sales_months():
    """Return all available months in chronological order."""
    month_order = {
        'JAN': 1, 'FEB': 2, 'MAR': 3, 'APR': 4,
        'MAY': 5, 'JUN': 6, 'JUL': 7, 'AUG': 8,
        'SEP': 9, 'OCT': 10, 'NOV': 11, 'DEC': 12
    }
    conn = get_raw_conn()
    cur  = conn.cursor()
    cur.execute("SELECT DISTINCT month FROM sales")
    months = [r[0] for r in cur.fetchall()]
    conn.close()

    def sort_key(m):
        parts = m.split('-')
        mon = parts[0][:3].upper()
        yr  = int(parts[1]) if len(parts) > 1 else 0
        return (yr, month_order.get(mon, 0))

    months.sort(key=sort_key)
    return months


@app.get("/sales")
def get_sales(month: str = Query(...), store: str = Query(None)):
    """Return sales for a given month, optionally filtered by store."""
    conn = get_raw_conn()
    cur  = conn.cursor()
    if store:
        cur.execute(
            "SELECT id, article, category, store_name, quantity, threshold, threshold_auto, threshold_manual FROM sales WHERE month=? AND store_name=? ORDER BY category, article",
            (month, store)
        )
    else:
        cur.execute(
            "SELECT id, article, category, store_name, quantity, threshold, threshold_auto, threshold_manual FROM sales WHERE month=? ORDER BY category, article",
            (month,)
        )
    rows = cur.fetchall()
    conn.close()

    return [
        {
            "id": r[0],
            "article": r[1],
            "category": r[2],
            "store_name": r[3],
            "quantity": r[4],
            "threshold": r[5],
            "threshold_auto": r[6],
            "threshold_manual": bool(r[7]),
            "is_low": r[5] > 0 and r[4] < r[5],
        }
        for r in rows
    ]


@app.get("/sales/summary")
def get_sales_summary(month: str = Query(...)):
    """Return per-store sales summary for a month."""
    conn = get_raw_conn()
    cur  = conn.cursor()
    cur.execute("""
        SELECT store_name,
               COUNT(*) as total,
               SUM(CASE WHEN threshold > 0 AND quantity < threshold THEN 1 ELSE 0 END) as low_count,
               SUM(quantity) as total_qty
        FROM sales
        WHERE month = ?
        GROUP BY store_name
        ORDER BY store_name
    """, (month,))
    rows = cur.fetchall()
    conn.close()

    return {
        r[0]: {
            "total_items": r[1],
            "low_sales_items": r[2],
            "total_quantity": round(r[3], 1)
        }
        for r in rows
    }


# sales threshold update — see below


@app.get("/sales/low")
def get_low_sales(month: str = Query(...), store: str = Query(None)):
    """Return only low-sales items for a given month."""
    conn = get_raw_conn()
    cur  = conn.cursor()
    if store:
        cur.execute(
            "SELECT id, article, category, store_name, quantity, threshold FROM sales WHERE month=? AND store_name=? AND threshold > 0 AND quantity < threshold ORDER BY quantity",
            (month, store)
        )
    else:
        cur.execute(
            "SELECT id, article, category, store_name, quantity, threshold FROM sales WHERE month=? AND threshold > 0 AND quantity < threshold ORDER BY quantity",
            (month,)
        )
    rows = cur.fetchall()
    conn.close()
    return [
        {
            "id": r[0],
            "article": r[1],
            "category": r[2],
            "store_name": r[3],
            "quantity": r[4],
            "threshold": r[5],
            "deficit": round(r[5] - r[4], 2)
        }
        for r in rows
    ]


# ── Override: update sales threshold (marks as manual) ───
@app.put("/sales/{sale_id}/threshold")
def update_sales_threshold(sale_id: int, threshold: float = Query(...)):
    conn = get_raw_conn()
    cur  = conn.cursor()
    cur.execute("SELECT article, store_name FROM sales WHERE id=?", (sale_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return {"error": "Record not found"}
    article, store = row
    # Update threshold for this article+store across ALL months, mark as manual
    cur.execute(
        "UPDATE sales SET threshold=?, threshold_manual=1 WHERE article=? AND store_name=?",
        (threshold, article, store)
    )
    conn.commit()
    conn.close()
    return {"message": "Sales threshold updated", "article": article, "store": store, "threshold": threshold, "manual": True}


# ── Reset: revert sales threshold back to auto average ───
@app.put("/sales/{sale_id}/threshold/reset")
def reset_sales_threshold(sale_id: int):
    conn = get_raw_conn()
    cur  = conn.cursor()
    cur.execute("SELECT article, store_name FROM sales WHERE id=?", (sale_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return {"error": "Record not found"}
    article, store = row
    # Reset to auto threshold for all months
    cur.execute(
        "UPDATE sales SET threshold=threshold_auto, threshold_manual=0 WHERE article=? AND store_name=?",
        (article, store)
    )
    conn.commit()
    conn.close()
    return {"message": "Threshold reset to auto average", "article": article, "store": store}


# ── Get sales thresholds info for an article+store ───────
@app.get("/sales/{sale_id}/threshold-info")
def get_threshold_info(sale_id: int):
    conn = get_raw_conn()
    cur  = conn.cursor()
    cur.execute("SELECT article, store_name, threshold, threshold_auto, threshold_manual FROM sales WHERE id=?", (sale_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return {"error": "Not found"}
    return {
        "article": row[0],
        "store": row[1],
        "current_threshold": row[2],
        "auto_threshold": row[3],
        "is_manual": bool(row[4])
    }

# ════════════════════════════════════════════════════════
#  NEGATIVE STOCK ALERT ENDPOINTS
# ════════════════════════════════════════════════════════

@app.get("/alerts/negative-stock")
def negative_stock(store: str = Query(None)):
    """Items with stock below zero."""
    db = SessionLocal()
    query = db.query(Inventory).filter(Inventory.current_stock < 0)
    if store:
        query = query.filter(Inventory.store_name == store)
    items = query.order_by(Inventory.current_stock).all()
    db.close()
    return [
        {
            "id": i.id,
            "item_name": i.item_name,
            "category": i.category,
            "store_name": i.store_name,
            "current_stock": i.current_stock,
            "threshold": i.threshold,
            "deficit": round(abs(i.current_stock), 2),
        }
        for i in items
    ]


@app.get("/alerts/negative-stock/summary")
def negative_stock_summary():
    """Count of negative stock items per store."""
    db = SessionLocal()
    items = db.query(Inventory).filter(Inventory.current_stock < 0).all()
    db.close()
    summary = {}
    for i in items:
        s = i.store_name
        if s not in summary:
            summary[s] = {"count": 0, "total_deficit": 0}
        summary[s]["count"] += 1
        summary[s]["total_deficit"] += abs(i.current_stock)
    return summary


# ════════════════════════════════════════════════════════
#  SALES DROP ALERT ENDPOINTS
# ════════════════════════════════════════════════════════

@app.get("/alerts/sales-drop")
def sales_drop(drop_pct: float = Query(30.0), store: str = Query(None), month: str = Query(None)):
    """Items where sales dropped by more than drop_pct% vs previous month."""
    conn = get_raw_conn()
    cur  = conn.cursor()

    # Get sorted months
    cur.execute("SELECT DISTINCT month FROM sales")
    months_raw = [r[0] for r in cur.fetchall()]
    mo = {'JAN':1,'FEB':2,'MAR':3,'APR':4,'MAY':5,'JUN':6,'JUL':7,'AUG':8,'SEP':9,'OCT':10,'NOV':11,'DEC':12}
    months_raw.sort(key=lambda m: (int(m.split('-')[1]), mo.get(m.split('-')[0][:3].upper(), 0)))

    if not month:
        month = months_raw[-1] if months_raw else None
    if not month or month not in months_raw:
        conn.close()
        return []

    idx = months_raw.index(month)
    if idx == 0:
        conn.close()
        return []

    prev_month = months_raw[idx - 1]

    # Get current month data
    if store:
        cur.execute(
            "SELECT article, category, store_name, quantity FROM sales WHERE month=? AND store_name=?",
            (month, store)
        )
    else:
        cur.execute(
            "SELECT article, category, store_name, quantity FROM sales WHERE month=?",
            (month,)
        )
    curr_rows = {(r[0], r[2]): (r[1], r[3]) for r in cur.fetchall()}

    # Get previous month data
    if store:
        cur.execute(
            "SELECT article, store_name, quantity FROM sales WHERE month=? AND store_name=?",
            (prev_month, store)
        )
    else:
        cur.execute(
            "SELECT article, store_name, quantity FROM sales WHERE month=?",
            (prev_month,)
        )
    prev_rows = {(r[0], r[1]): r[2] for r in cur.fetchall()}
    conn.close()

    alerts = []
    for (article, store_name), (category, curr_qty) in curr_rows.items():
        prev_qty = prev_rows.get((article, store_name), None)
        if prev_qty is None or prev_qty <= 0:
            continue
        drop = round((prev_qty - curr_qty) / prev_qty * 100, 1)
        if drop >= drop_pct:
            alerts.append({
                "article": article,
                "category": category,
                "store_name": store_name,
                "current_month": month,
                "prev_month": prev_month,
                "current_qty": curr_qty,
                "prev_qty": prev_qty,
                "drop_pct": drop,
                "severity": "critical" if drop >= 50 else "warning"
            })

    alerts.sort(key=lambda x: x["drop_pct"], reverse=True)
    return alerts


@app.get("/alerts/sales-drop/summary")
def sales_drop_summary(drop_pct: float = Query(30.0), month: str = Query(None)):
    """Summary of sales drop alerts per store."""
    all_drops = sales_drop(drop_pct=drop_pct, month=month)
    summary = {}
    for item in all_drops:
        s = item["store_name"]
        if s not in summary:
            summary[s] = {"total_drops": 0, "critical": 0, "warning": 0}
        summary[s]["total_drops"] += 1
        summary[s][item["severity"]] += 1
    return summary