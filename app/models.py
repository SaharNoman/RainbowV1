from sqlalchemy import Column, Integer, String, Float
from .database import Base


class Inventory(Base):
    __tablename__ = "inventory"

    id = Column(Integer, primary_key=True, index=True)

    item_name = Column(String, index=True)
    store_name = Column(String, index=True)   # ✅ MUST EXIST

    category = Column(String)

    current_stock = Column(Float)
    threshold = Column(Float)


class Store(Base):
    __tablename__ = "stores"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True)