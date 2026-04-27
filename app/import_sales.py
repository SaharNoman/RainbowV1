"""
import_sales.py
Run from E:/0WorkFolder/RainbowV1:
    python import_sales.py

Threshold logic:
  - ONE threshold per article+store = average sales over the
    3 most recent months in the dataset (currently DEC-25, JAN-26, FEB-26)
  - This threshold applies to ALL months in the table
  - Manual overrides made via dashboard are preserved when you
    pass --keep-thresholds flag on re-import
"""

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
    """
    For each article+store, compute avg of the 3 most recent months.
    Returns dict: { (article, store): avg_value }
    """
    # 3 most recent months (excluding the latest/current month)
    # e.g. if months = [..., DEC-25, JAN-26, FEB-26, MAR-26]
    # prev3 = [DEC-25, JAN-26, FEB-26]
    prev3 = months[-4:-1]   # last 3 before the latest
    print(f"Auto threshold basis — avg of: {prev3}")

    thresholds = {}
    articles = df['ARTICLE NAME'].unique()

    for article in articles:
        article = str(article).strip()
        for store in STORES:
            vals = []
            for pm in prev3:
                row = df[(df['ARTICLE NAME'] == article) & (df['MONTH'] == pm)]
                if not row.empty:
                    v = row[store].values[0]
                    if v == v:   # not NaN
                        vals.append(float(v))
            avg = round(sum(vals) / len(vals), 1) if vals else 0.0
            thresholds[(article, store)] = avg

    return thresholds


def import_sales(keep_thresholds=False):
    df = pd.read_excel(EXCEL_PATH, sheet_name="SALES DATA")
    print(f"Read {len(df)} rows from SALES DATA sheet")

    months = sorted(df['MONTH'].unique().tolist(), key=sort_month)
    print(f"Months found ({len(months)}): {months}")
    print(f"Latest month: {months[-1]}")

    # Compute auto thresholds once for all article+store combos
    auto_thresholds = compute_auto_thresholds(df, months)

    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()

    # Create table with new columns if not exists
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

    # Preserve manual overrides if requested
    manual_overrides = {}
    if keep_thresholds:
        cur.execute("""
            SELECT article, store_name, threshold
            FROM sales
            WHERE threshold_manual = 1
            GROUP BY article, store_name
        """)
        for row in cur.fetchall():
            manual_overrides[(row[0], row[1])] = row[2]
        print(f"Preserving {len(manual_overrides)} manual threshold overrides")

    cur.execute("DELETE FROM sales")

    rows_inserted = 0
    for month in months:
        month_df = df[df['MONTH'] == month]
        for _, row in month_df.iterrows():
            article  = str(row['ARTICLE NAME']).strip()
            category = str(row['Last Level Category']).strip()

            for store in STORES:
                qty = row.get(store)
                qty = 0.0 if (qty != qty) else float(qty)

                auto_thresh = auto_thresholds.get((article, store), 0.0)

                # Use manual override if it exists
                key = (article, store)
                if keep_thresholds and key in manual_overrides:
                    threshold        = manual_overrides[key]
                    threshold_manual = 1
                else:
                    threshold        = auto_thresh
                    threshold_manual = 0

                cur.execute("""
                    INSERT INTO sales
                        (article, category, store_name, month, quantity,
                         threshold, threshold_auto, threshold_manual)
                    VALUES (?,?,?,?,?,?,?,?)
                """, (article, category, store, month, qty,
                      threshold, auto_thresh, threshold_manual))
                rows_inserted += 1

    conn.commit()
    conn.close()

    print(f"\nInserted {rows_inserted} records.")
    print(f"Default threshold = avg of {months[-4:-1]}")
    print("Done!")


if __name__ == "__main__":
    keep = "--keep-thresholds" in sys.argv
    import_sales(keep_thresholds=keep)