"""Adopt legacy inventory, preserving IDs and reconstructing cost snapshots."""

from datetime import date
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.orm import Session
from app.database import Base
from app import models as m, ledger_models as lm
from app.money import cents

revision = "v2_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    names = inspect(conn).get_table_names()
    if "product" in names:
        cols = {x["name"] for x in inspect(conn).get_columns("product")}
        if "retail_cents" not in cols:
            op.execute(
                "ALTER TABLE product ADD COLUMN retail_cents INTEGER NOT NULL DEFAULT 0"
            )
        if "must_change_password" not in {
            x["name"] for x in inspect(conn).get_columns("user")
        }:
            op.execute(
                "ALTER TABLE user ADD COLUMN must_change_password INTEGER NOT NULL DEFAULT 1"
            )
    Base.metadata.create_all(conn)
    db = Session(bind=conn, join_transaction_mode="create_savepoint")
    try:
        from app.security import verify_password

        for u in db.query(m.User):
            u.must_change_password = int(verify_password("admin123", u.password_hash))
        for p in db.query(m.Product):
            p.retail_cents = cents(p.retail_price or 0)
            if p.retail_cents < 0:
                raise RuntimeError(f"商品 {p.id} 零售价为负，请修正旧数据")
        from app.crud import get_or_create_size

        for kind, model in [("purchase", m.Purchase), ("sale", m.Sale)]:
            for r in db.query(model).order_by(model.id):
                if (
                    db.query(lm.Document)
                    .filter_by(legacy_kind=kind, legacy_id=r.id)
                    .first()
                ):
                    continue
                if not db.get(m.Product, r.product_id):
                    raise RuntimeError(f"{kind} {r.id} 商品关联损坏")
                value = r.purchase_date if kind == "purchase" else r.sale_date
                try:
                    if len(value) != 10:
                        raise ValueError()
                    date.fromisoformat(value)
                except (ValueError, TypeError):
                    raise RuntimeError(f"{kind} {r.id} 日期无效：{value}")
                size = (
                    db.get(m.Size, r.size_id)
                    if r.size_id
                    else get_or_create_size(db, r.size_text or "未指定")
                )
                if not size:
                    raise RuntimeError(f"{kind} {r.id} 尺码关联损坏")
                price = cents(r.cost_price if kind == "purchase" else r.unit_price)
                if r.quantity <= 0 or price < 0:
                    raise RuntimeError(f"{kind} {r.id} 数量或金额无效")
                d = lm.Document(
                    kind=kind,
                    date=value,
                    actor="migration",
                    remark=r.remark,
                    created_at=r.created_at,
                    legacy_kind=kind,
                    legacy_id=r.id,
                )
                db.add(d)
                db.flush()
                line = lm.DocumentLine(
                    document_id=d.id,
                    product_id=r.product_id,
                    size_id=size.id,
                    style_snapshot=r.style_code,
                    size_snapshot=r.size_text or "未指定",
                    supplier_id=r.supplier_id if kind == "purchase" else None,
                    quantity=r.quantity * (1 if kind == "purchase" else -1),
                    price_cents=price,
                )
                db.add(line)
                db.flush()
                db.add(
                    lm.Movement(
                        line_id=line.id,
                        product_id=r.product_id,
                        size_id=size.id,
                        quantity=line.quantity,
                    )
                )
        db.flush()
        from app.ledger import recompute

        recompute(db, "migration")
        db.merge(
            lm.SystemState(
                key="upgrade_notice",
                value="已升级到 v2，历史毛利已按商品尺码移动加权成本重建，请核对待核算记录。",
            )
        )
        db.commit()
    finally:
        db.close()


def downgrade():
    raise RuntimeError("请使用升级前完整备份回退，禁止丢失 v2 单据")
