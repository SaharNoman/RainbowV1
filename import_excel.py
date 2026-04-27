import pandas as pd
from app.database import SessionLocal
from app.models import Inventory

# ✅ Create DB session
db = SessionLocal()

# ✅ Read Excel
#df = pd.read_excel(r"E:\0WorkFolder\RainbowV1\data\inventory.xlsx", sheet_name="STOCK DATA")
df = pd.read_excel(r"data/inventory.xlsx", sheet_name="STOCK DATA")
#df = pd.read_excel("inventory.xlsx", sheet_name="STOCK DATA")

# ✅ Loop through rows
for _, row in df.iterrows():
    item_name = row["ARTICLE NAME"]
    category = row["Last Level Category"]

    # Loop through store columns
    store_columns = ["WT", "DFNR", "BTL", "EME", "GUJ", "MT", "SHKP", "RWP", "SHDR", "CW", "BRL"]

    for store in store_columns:
        stock = row[store]

        if pd.notna(stock):  # ignore empty cells
            db.add(Inventory(
                item_name=item_name,
                category=category,
                store_name=store,
                current_stock=float(stock),
                threshold=5
            ))

# ✅ Commit changes
db.commit()
db.close()

print("Multi-store inventory imported successfully!")