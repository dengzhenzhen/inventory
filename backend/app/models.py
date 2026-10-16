"""数据模型（对应 PRD 第 5 节表结构）。"""
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from .database import Base


class Category(Base):
    __tablename__ = "category"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False, unique=True)
    sort_order = Column(Integer, default=0)


class Supplier(Base):
    __tablename__ = "supplier"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    contact = Column(String(50))
    phone = Column(String(30))
    remark = Column(Text)


class Size(Base):
    __tablename__ = "size"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(20), nullable=False, unique=True)
    sort_order = Column(Integer, default=0)


class Product(Base):
    __tablename__ = "product"
    id = Column(Integer, primary_key=True, autoincrement=True)
    style_code = Column(String(64), nullable=False, unique=True, index=True)
    name = Column(String(120))
    category_id = Column(Integer, ForeignKey("category.id"))
    supplier_id = Column(Integer, ForeignKey("supplier.id"))
    retail_price = Column(Float, default=0)
    main_image = Column(String(255))
    remark = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    category = relationship("Category")
    supplier = relationship("Supplier")


class Purchase(Base):
    __tablename__ = "purchase"
    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("product.id"), nullable=False)
    style_code = Column(String(64), nullable=False, index=True)
    size_id = Column(Integer, ForeignKey("size.id"))
    size_text = Column(String(20))
    quantity = Column(Integer, nullable=False, default=0)
    cost_price = Column(Float, nullable=False, default=0)
    purchase_date = Column(String(10), nullable=False, index=True)
    supplier_id = Column(Integer, ForeignKey("supplier.id"))
    remark = Column(Text)
    created_at = Column(DateTime, default=datetime.now)

    product = relationship("Product")
    size = relationship("Size")
    supplier = relationship("Supplier")

    __table_args__ = (
        CheckConstraint("quantity >= 0", name="ck_purchase_qty"),
        CheckConstraint("cost_price >= 0", name="ck_purchase_cost"),
    )


class Sale(Base):
    __tablename__ = "sale"
    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("product.id"), nullable=False)
    style_code = Column(String(64), nullable=False, index=True)
    size_id = Column(Integer, ForeignKey("size.id"))
    size_text = Column(String(20))
    quantity = Column(Integer, nullable=False, default=0)
    unit_price = Column(Float, nullable=False, default=0)
    sale_date = Column(String(10), nullable=False, index=True)
    remark = Column(Text)
    created_at = Column(DateTime, default=datetime.now)

    product = relationship("Product")
    size = relationship("Size")

    __table_args__ = (
        CheckConstraint("quantity >= 0", name="ck_sale_qty"),
        CheckConstraint("unit_price >= 0", name="ck_sale_price"),
    )


class User(Base):
    __tablename__ = "user"
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.now)
