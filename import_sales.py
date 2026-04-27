import pandas as pd
import sqlite3
import sys

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

def compute_auto_thresholds(df, months):
    prev3 = months[-4:-1]
    print(f"Auto threshold basis - avg of: {prev3}")
    thresholds = {}
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
            thresholds[(article, store)] = round(sum(vals)/len(vals), 1) if vals else 0.0
    return thresholds

def import_sales(keep_thresholds=False):
    df = pd.read_excel(EXCEL_PATH, sheet_name="SALES DATA")
    print(f"Read {len(df)} rows from SALES DATA sheet")

    months = sorted(df['MONTH'].unique().tolist(), key=sort_month)
    print(f"Months found ({len(months)}): {months}")
    print(f"Latest month: {months[-1]}")

    auto_thresholds = compute_auto_thresholds(df, months)

    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()

    cur.execute("DROP TABLE IF EXISTS sales")
    cur.execute("""
        CREATE TABLE sales (
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

    manual_overrides = {}
    if keep_thresholds:
        try:
            cur.execute("SELECT article, store_name, threshold FROM sales WHERE threshold_manual=1 GROUP BY article, store_name")
            for row in cur.fetchall():
                manual_overrides[(row[0], row[1])] = row[2]
            print(f"Preserving {len(manual_overrides)} manual overrides")
        except:
            pass

    rows_inserted = 0
    for month in months:
        for _, row in df[df['MONTH'] == month].iterrows():
            article  = str(row['ARTICLE NAME']).strip()
            category = str(row['Last Level Category']).strip()
            for store in STORES:
                qty = row.get(store)
                qty = 0.0 if (qty != qty) else float(qty)
                auto_thresh = auto_thresholds.get((article, store), 0.0)
                key = (article, store)
                if keep_thresholds and key in manual_overrides:
                    threshold        = manual_overrides[key]
                    threshold_manual = 1
                else:
                    threshold        = auto_thresh
                    threshold_manual = 0
                cur.execute("""
                    INSERT INTO sales
                        (article, category, store_name, month, quantity, threshold, threshold_auto, threshold_manual)
                    VALUES (?,?,?,?,?,?,?,?)
                """, (article, category, store, month, qty, threshold, auto_thresh, threshold_manual))
                rows_inserted += 1

    conn.commit()
    conn.close()
    print(f"Inserted {rows_inserted} records.")
    print(f"Default threshold = avg of {months[-4:-1]}")
    print("Done!")

if __name__ == "__main__":
    import_sales(keep_thresholds="--keep-thresholds" in sys.argv)