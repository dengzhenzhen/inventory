"""Version 2 immutable documents and inventory ledger."""

from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    CheckConstraint,
    Index,
)
from sqlalchemy.orm import relationship
from .database import Base


class Document(Base):
    __tablename__ = "document"
    id = Column(Integer, primary_key=True)
    kind = Column(String(30), nullable=False, index=True)
    date = Column(String(10), nullable=False, index=True)
    status = Column(String(20), nullable=False, default="posted", index=True)
    remark = Column(Text)
    actor = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    idempotency_key = Column(String(100), unique=True)
    request_hash = Column(String(64))
    legacy_kind = Column(String(20))
    legacy_id = Column(Integer)
    lines = relationship(
        "DocumentLine", back_populates="document", order_by="DocumentLine.id"
    )
    __table_args__ = (
        UniqueConstraint("legacy_kind", "legacy_id"),
        CheckConstraint("status IN ('posted','void')"),
        CheckConstraint(
            "kind IN ('purchase','sale','purchase_return','sale_return','count','adjustment')"
        ),
    )


class DocumentLine(Base):
    __tablename__ = "document_line"
    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey("document.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("product.id"), nullable=False, index=True)
    size_id = Column(Integer, ForeignKey("size.id"), nullable=False, index=True)
    supplier_id = Column(Integer, ForeignKey("supplier.id"))
    style_snapshot = Column(String(64), nullable=False)
    size_snapshot = Column(String(20), nullable=False)
    quantity = Column(Integer, nullable=False)
    price_cents = Column(Integer, nullable=False, default=0)
    cost_micro = Column(Integer)
    cost_status = Column(String(20), default="known", nullable=False)
    dirty = Column(Integer, default=0, nullable=False)
    original_line_id = Column(Integer, ForeignKey("document_line.id"), index=True)
    document = relationship("Document", back_populates="lines")
    product = relationship("Product")
    size = relationship("Size")
    supplier = relationship("Supplier")
    __table_args__ = (
        CheckConstraint("price_cents >= 0"),
        Index("ix_line_sku", "product_id", "size_id"),
    )


class Movement(Base):
    __tablename__ = "movement"
    id = Column(Integer, primary_key=True)
    line_id = Column(
        Integer, ForeignKey("document_line.id"), nullable=False, index=True
    )
    product_id = Column(Integer, ForeignKey("product.id"), nullable=False, index=True)
    size_id = Column(Integer, ForeignKey("size.id"), nullable=False, index=True)
    quantity = Column(Integer, nullable=False)
    reversal = Column(Integer, default=0, nullable=False)
    __table_args__ = (
        UniqueConstraint("line_id", "reversal"),
        Index("ix_movement_sku", "product_id", "size_id"),
    )


class Audit(Base):
    __tablename__ = "audit"
    id = Column(Integer, primary_key=True)
    actor = Column(String(50), nullable=False)
    action = Column(String(50), nullable=False)
    document_id = Column(Integer, ForeignKey("document.id"))
    detail = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.now, nullable=False)


class AuthSession(Base):
    __tablename__ = "auth_session"
    id = Column(String(64), primary_key=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)


class SystemState(Base):
    __tablename__ = "system_state"
    key = Column(String(50), primary_key=True)
    value = Column(Text, nullable=False)
