import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

# ── Email Config ─────────────────────────────────────────
SENDER_EMAIL     = "rainbowalertsystem@gmail.com"
SENDER_PASSWORD  = "plioaikmxzcjyfad"
HEADOFFICE_EMAIL = "sahar.noman.javed@gmail.com"


# ── Generic send helper ──────────────────────────────────
def _send(subject: str, html_body: str) -> dict:
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = SENDER_EMAIL
        msg["To"]      = HEADOFFICE_EMAIL
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, HEADOFFICE_EMAIL, msg.as_string())

        return {"status": "sent", "message": f"Alert sent to {HEADOFFICE_EMAIL}"}
    except smtplib.SMTPAuthenticationError:
        return {"status": "error", "message": "Gmail authentication failed. Check App Password in app/notifier.py"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ════════════════════════════════════════════════════════
# LOW STOCK EMAIL
# ════════════════════════════════════════════════════════

def build_stock_html(low_items: list) -> str:
    now = datetime.now().strftime("%d %b %Y, %I:%M %p")
    by_store = {}
    for item in low_items:
        by_store.setdefault(item["store_name"], []).append(item)

    store_blocks = ""
    for store, items in sorted(by_store.items()):
        rows = "".join(f"""
            <tr>
              <td style="padding:10px 14px;border-bottom:1px solid #f0f0f0">{i['item_name']}</td>
              <td style="padding:10px 14px;border-bottom:1px solid #f0f0f0">{i['category']}</td>
              <td style="padding:10px 14px;border-bottom:1px solid #f0f0f0;color:#c0392b;font-weight:700">{i['current_stock']}</td>
              <td style="padding:10px 14px;border-bottom:1px solid #f0f0f0">{i['threshold']}</td>
              <td style="padding:10px 14px;border-bottom:1px solid #f0f0f0;color:#e67e22;font-weight:600">+{round(i['threshold']-i['current_stock'],2)} needed</td>
            </tr>""" for i in items)

        store_blocks += f"""
        <div style="margin-bottom:28px">
          <div style="background:#1a6b3c;color:white;padding:10px 16px;border-radius:8px 8px 0 0;font-weight:700;font-size:15px">
            🏪 Store: {store} &nbsp;|&nbsp; {len(items)} low stock item{'s' if len(items)>1 else ''}
          </div>
          <table style="width:100%;border-collapse:collapse;background:white;border:1px solid #e0e0e0">
            <thead><tr style="background:#f8f9fa">
              <th style="padding:10px 14px;text-align:left;font-size:12px;color:#6c757d;text-transform:uppercase">Item</th>
              <th style="padding:10px 14px;text-align:left;font-size:12px;color:#6c757d;text-transform:uppercase">Category</th>
              <th style="padding:10px 14px;text-align:left;font-size:12px;color:#6c757d;text-transform:uppercase">Stock</th>
              <th style="padding:10px 14px;text-align:left;font-size:12px;color:#6c757d;text-transform:uppercase">Threshold</th>
              <th style="padding:10px 14px;text-align:left;font-size:12px;color:#6c757d;text-transform:uppercase">Deficit</th>
            </tr></thead>
            <tbody>{rows}</tbody>
          </table>
        </div>"""

    return f"""<!DOCTYPE html><html><body style="margin:0;padding:0;background:#f0f2f5;font-family:'Segoe UI',Arial,sans-serif">
      <div style="max-width:700px;margin:30px auto">
        <div style="background:#1a6b3c;padding:28px 32px;border-radius:12px 12px 0 0">
          <h1 style="margin:0;color:white;font-size:22px">🛒 Rainbow Grocery — Low Stock Alert</h1>
          <p style="margin:6px 0 0;color:rgba(255,255,255,0.75);font-size:14px">{now}</p>
        </div>
        <div style="background:#fdecea;border:1px solid #f5c6c2;padding:16px 32px;display:flex;gap:32px">
          <div><div style="font-size:28px;font-weight:700;color:#c0392b">{len(low_items)}</div><div style="font-size:12px;color:#6c757d;text-transform:uppercase">Low Stock Items</div></div>
          <div><div style="font-size:28px;font-weight:700;color:#c0392b">{len(by_store)}</div><div style="font-size:12px;color:#6c757d;text-transform:uppercase">Stores Affected</div></div>
        </div>
        <div style="padding:24px 32px;background:#f0f2f5">{store_blocks}</div>
        <div style="background:#e8f5ee;padding:16px 32px;border-radius:0 0 12px 12px;text-align:center">
          <p style="margin:0;font-size:13px;color:#1a6b3c">Automated alert from <strong>Rainbow Inventory System</strong>. Please reorder at the earliest.</p>
        </div>
      </div></body></html>"""


def send_low_stock_email(low_items: list) -> dict:
    if not low_items:
        return {"status": "skipped", "message": "No low stock items found"}
    subject = f"⚠ Low Stock Alert — {len(low_items)} items need reorder ({datetime.now().strftime('%d %b %Y')})"
    result = _send(subject, build_stock_html(low_items))
    result["items_reported"] = len(low_items)
    return result


# ════════════════════════════════════════════════════════
# LOW SALES EMAIL
# ════════════════════════════════════════════════════════

def build_sales_html(low_items: list, month: str) -> str:
    now = datetime.now().strftime("%d %b %Y, %I:%M %p")
    by_store = {}
    for item in low_items:
        by_store.setdefault(item["store_name"], []).append(item)

    store_blocks = ""
    for store, items in sorted(by_store.items()):
        rows = "".join(f"""
            <tr>
              <td style="padding:10px 14px;border-bottom:1px solid #f0f0f0">{i['article_name']}</td>
              <td style="padding:10px 14px;border-bottom:1px solid #f0f0f0">{i['category']}</td>
              <td style="padding:10px 14px;border-bottom:1px solid #f0f0f0;color:#c0392b;font-weight:700">{i['quantity']}</td>
              <td style="padding:10px 14px;border-bottom:1px solid #f0f0f0">{i['threshold']}</td>
              <td style="padding:10px 14px;border-bottom:1px solid #f0f0f0;color:#e67e22;font-weight:600">+{round(i['threshold']-i['quantity'],2)} short</td>
            </tr>""" for i in items)

        store_blocks += f"""
        <div style="margin-bottom:28px">
          <div style="background:#8e44ad;color:white;padding:10px 16px;border-radius:8px 8px 0 0;font-weight:700;font-size:15px">
            🏪 Store: {store} &nbsp;|&nbsp; {len(items)} low sales item{'s' if len(items)>1 else ''}
          </div>
          <table style="width:100%;border-collapse:collapse;background:white;border:1px solid #e0e0e0">
            <thead><tr style="background:#f8f9fa">
              <th style="padding:10px 14px;text-align:left;font-size:12px;color:#6c757d;text-transform:uppercase">Article</th>
              <th style="padding:10px 14px;text-align:left;font-size:12px;color:#6c757d;text-transform:uppercase">Category</th>
              <th style="padding:10px 14px;text-align:left;font-size:12px;color:#6c757d;text-transform:uppercase">Sales Qty</th>
              <th style="padding:10px 14px;text-align:left;font-size:12px;color:#6c757d;text-transform:uppercase">Threshold</th>
              <th style="padding:10px 14px;text-align:left;font-size:12px;color:#6c757d;text-transform:uppercase">Shortfall</th>
            </tr></thead>
            <tbody>{rows}</tbody>
          </table>
        </div>"""

    return f"""<!DOCTYPE html><html><body style="margin:0;padding:0;background:#f0f2f5;font-family:'Segoe UI',Arial,sans-serif">
      <div style="max-width:700px;margin:30px auto">
        <div style="background:#8e44ad;padding:28px 32px;border-radius:12px 12px 0 0">
          <h1 style="margin:0;color:white;font-size:22px">📉 Rainbow Grocery — Low Sales Alert</h1>
          <p style="margin:6px 0 0;color:rgba(255,255,255,0.75);font-size:14px">Month: {month} &nbsp;|&nbsp; {now}</p>
        </div>
        <div style="background:#f3e5f5;border:1px solid #ce93d8;padding:16px 32px;display:flex;gap:32px">
          <div><div style="font-size:28px;font-weight:700;color:#8e44ad">{len(low_items)}</div><div style="font-size:12px;color:#6c757d;text-transform:uppercase">Low Sales Items</div></div>
          <div><div style="font-size:28px;font-weight:700;color:#8e44ad">{len(by_store)}</div><div style="font-size:12px;color:#6c757d;text-transform:uppercase">Stores Affected</div></div>
        </div>
        <div style="padding:24px 32px;background:#f0f2f5">{store_blocks}</div>
        <div style="background:#f3e5f5;padding:16px 32px;border-radius:0 0 12px 12px;text-align:center">
          <p style="margin:0;font-size:13px;color:#8e44ad">Automated alert from <strong>Rainbow Inventory System</strong>. Please review sales performance.</p>
        </div>
      </div></body></html>"""


def send_low_sales_email(low_items: list, month: str) -> dict:
    if not low_items:
        return {"status": "skipped", "message": "No low sales items found"}
    subject = f"📉 Low Sales Alert — {len(low_items)} items below threshold ({month})"
    result = _send(subject, build_sales_html(low_items, month))
    result["items_reported"] = len(low_items)
    return result