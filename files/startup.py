"""
startup.py — runs automatically when server starts on Render
Imports Excel data into SQLite if tables are empty
"""
import sqlite3
import os
import pandas as pd

EXCEL_PATH = "data/inventory.xlsx"
DB_PATH    = "inventory.db"
STORES     = ['WT','DFNR','BTL','EME','GUJ','MT','SHKP','RWP','SHDR','CW','BRL']

MONTH_ORDER = {
    'JAN':1,'FEB':2,'MAR':3,'APR':4,'MAY':5,'JUN':6,
    'JUL':7,'AUG':8,'SEP':9,'OCT':10,'NOV':11,'DEC':12
}

def sort_month(m):
    parts = m.split('-')
    return (int(parts[1]), MONTH_ORDER.get(parts[0][:3].upper(), 0))


def setup_database():
    print("[Startup] Checking database...")
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()

    # ── Inventory table ──────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            item_name     TEXT,
            store_name    TEXT,
            category      TEXT,
            current_stock REAL,
            threshold     REAL DEFAULT 5
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS stores (
            id   INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE
        )
    """)

    # Import stock data if empty
    cur.execute("SELECT COUNT(*) FROM inventory")
    if cur.fetchone()[0] == 0:
        print("[Startup] Importing stock data from Excel...")
        df = pd.read_excel(EXCEL_PATH, sheet_name="STOCK DATA")
        for _, row in df.iterrows():
            for store in STORES:
                val = row.get(store)
                if val != val:  # NaN
                    continue
                cur.execute("""
                    INSERT INTO inventory (item_name, store_name, category, current_stock, threshold)
                    VALUES (?,?,?,?,5)
                """, (str(row.get("Item", row.get("ARTICLE NAME", "Unknown"))).strip(),
                      store,
                      str(row.get("Category", row.get("Last Level Category", "GENERAL"))).strip(),
                      float(val)))
        print(f"[Startup] Stock data imported.")

    # ── Sales table ───────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sales (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            article          TEXT,
            category         TEXT,
            store_name       TEXT,
            month            TEXT,
            quantity         REAL,
            threshold        REAL DEFAULT 0,
            threshold_auto   REAL DEFAULT 0,
            threshold_manual INTEGER DEFAULT 0
        )
    """)

    cur.execute("SELECT COUNT(*) FROM sales")
    if cur.fetchone()[0] == 0:
        print("[Startup] Importing sales data from Excel...")
        df = pd.read_excel(EXCEL_PATH, sheet_name="SALES DATA")
        months = sorted(df['MONTH'].unique().tolist(), key=sort_month)
        prev3  = months[-4:-1]
        print(f"[Startup] Auto threshold basis: {prev3}")

        # Compute auto thresholds
        auto_thresholds = {}
        for article in df['ARTICLE NAME'].unique():
            article = str(article).strip()
            for store in STORES:
                vals = []
                for pm in prev3:
                    row = df[(df['ARTICLE NAME'] == article) & (df['MONTH'] == pm)]
                    if not row.empty:
                        v = row[store].values[0]
                        if v == v:
                            vals.append(float(v))
                auto_thresholds[(article, store)] = round(sum(vals)/len(vals), 1) if vals else 0.0

        rows = 0
        for month in months:
            for _, row in df[df['MONTH'] == month].iterrows():
                article  = str(row['ARTICLE NAME']).strip()
                category = str(row['Last Level Category']).strip()
                for store in STORES:
                    qty = row.get(store)
                    qty = 0.0 if (qty != qty) else float(qty)
                    auto_thresh = auto_thresholds.get((article, store), 0.0)
                    cur.execute("""
                        INSERT INTO sales
                            (article, category, store_name, month, quantity, threshold, threshold_auto, threshold_manual)
                        VALUES (?,?,?,?,?,?,?,0)
                    """, (article, category, store, month, qty, auto_thresh, auto_thresh))
                    rows += 1
        print(f"[Startup] Sales data imported: {rows} records.")

    conn.commit()
    conn.close()
    print("[Startup] Database ready.")


if __name__ == "__main__":
    setup_database()
