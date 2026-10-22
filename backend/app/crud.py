"""领域辅助：字典/商品自动创建、序列化、库存聚合。"""

from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from . import models


# ---------- 字典 & 商品自动创建 ----------
def get_or_create_category(db: Session, name: Optional[str]):
    if not name or not name.strip():
        return None
    name = name.strip()
    obj = db.query(models.Category).filter_by(name=name).first()
    if not obj:
        obj = models.Category(name=name)
        db.add(obj)
        db.flush()
    return obj


def get_or_create_supplier(db: Session, name: Optional[str]):
    if not name or not name.strip():
        return None
    name = name.strip()
    obj = db.query(models.Supplier).filter_by(name=name).first()
    if not obj:
        obj = models.Supplier(name=name)
        db.add(obj)
        db.flush()
    return obj


def get_or_create_size(db: Session, name: Optional[str]):
    if not name or not name.strip():
        return None
    name = name.strip()
    obj = db.query(models.Size).filter_by(name=name).first()
    if not obj:
        obj = models.Size(name=name)
        db.add(obj)
        db.flush()
    return obj


def get_or_create_product(
    db: Session,
    style_code: str,
    category_name: Optional[str] = None,
    supplier_name: Optional[str] = None,
):
    """按款号取/建商品档案；返回 (product, created)。"""
    style_code = (style_code or "").strip()
    product = db.query(models.Product).filter_by(style_code=style_code).first()
    if product:
        if not product.category_id and category_name:
            cat = get_or_create_category(db, category_name)
            if cat:
                product.category_id = cat.id
        if not product.supplier_id and supplier_name:
            sup = get_or_create_supplier(db, supplier_name)
            if sup:
                product.supplier_id = sup.id
        return product, False
    cat = get_or_create_category(db, category_name)
    sup = get_or_create_supplier(db, supplier_name)
    product = models.Product(
        style_code=style_code,
        category_id=cat.id if cat else None,
        supplier_id=sup.id if sup else None,
    )
    db.add(product)
    db.flush()
    return product, True


# ---------- 序列化 ----------
def product_dict(p: models.Product) -> dict:
    return {
        "id": p.id,
        "style_code": p.style_code,
        "name": p.name,
        "category_id": p.category_id,
        "category_name": p.category.name if p.category else None,
        "supplier_id": p.supplier_id,
        "supplier_name": p.supplier.name if p.supplier else None,
        "retail_price": p.retail_cents / 100,
        "main_image": p.main_image,
        "remark": p.remark,
        "created_at": p.created_at.isoformat() if p.created_at else None,
    }


def purchase_dict(r: models.Purchase) -> dict:
    return {
        "id": r.id,
        "product_id": r.product_id,
        "style_code": r.style_code,
        "category_id": r.product.category_id if r.product else None,
        "category_name": r.product.category.name
        if (r.product and r.product.category)
        else None,
        "supplier_id": r.supplier_id,
        "supplier_name": (
            r.supplier.name
            if r.supplier
            else (
                r.product.supplier.name if (r.product and r.product.supplier) else None
            )
        ),
        "size_id": r.size_id,
        "size_text": r.size_text,
        "quantity": r.quantity,
        "cost_price": r.cost_price,
        "amount": round((r.quantity or 0) * (r.cost_price or 0), 2),
        "purchase_date": r.purchase_date,
        "remark": r.remark,
    }


def sale_dict(r: models.Sale) -> dict:
    return {
        "id": r.id,
        "product_id": r.product_id,
        "style_code": r.style_code,
        "category_id": r.product.category_id if r.product else None,
        "category_name": r.product.category.name
        if (r.product and r.product.category)
        else None,
        "size_id": r.size_id,
        "size_text": r.size_text,
        "quantity": r.quantity,
        "unit_price": r.unit_price,
        "amount": round((r.quantity or 0) * (r.unit_price or 0), 2),
        "sale_date": r.sale_date,
        "remark": r.remark,
    }


# ---------- stable SKU ledger aggregation ----------
def current_stock(db, style_code, size_text):
    from .ledger import stock

    p = db.query(models.Product).filter_by(style_code=style_code.strip()).first()
    z = db.query(models.Size).filter_by(name=size_text.strip() or "未指定").first()
    return stock(db, p.id, z.id) if p and z else 0


def stock_query(db, keyword=None, category_id=None, only_negative=False):
    from .ledger_models import Movement
    from sqlalchemy import case, or_

    agg = (
        db.query(
            Movement.product_id.label("pid"),
            Movement.size_id.label("sid"),
            func.sum(Movement.quantity).label("stock"),
            func.max(Movement.id).label("version"),
            func.sum(case((Movement.quantity > 0, Movement.quantity), else_=0)).label(
                "incoming"
            ),
            func.sum(case((Movement.quantity < 0, -Movement.quantity), else_=0)).label(
                "outgoing"
            ),
        )
        .group_by(Movement.product_id, Movement.size_id)
        .subquery()
    )
    q = (
        db.query(
            models.Product,
            models.Size,
            agg.c.stock,
            agg.c.version,
            agg.c.incoming,
            agg.c.outgoing,
        )
        .join(agg, models.Product.id == agg.c.pid)
        .join(models.Size, models.Size.id == agg.c.sid)
    )
    if keyword:
        q = q.filter(
            or_(
                models.Product.style_code.contains(keyword, autoescape=True),
                models.Product.name.contains(keyword, autoescape=True),
            )
        )
    if category_id:
        q = q.filter(models.Product.category_id == category_id)
    if only_negative:
        q = q.filter(agg.c.stock < 0)
    from sqlalchemy.orm import joinedload

    return q.options(
        joinedload(models.Product.category), joinedload(models.Product.supplier)
    ).order_by(models.Product.style_code, models.Size.sort_order, models.Size.id)


def stock_rows(
    db, keyword=None, category_id=None, only_negative=False, page=None, page_size=20
):
    q = stock_query(db, keyword, category_id, only_negative)
    if page:
        q = q.offset((page - 1) * page_size).limit(page_size)
    return [
        {
            "product_id": p.id,
            "style_code": p.style_code,
            "size_id": z.id,
            "size_text": z.name,
            "product": product_dict(p),
            "category_name": p.category.name if p.category else None,
            "purchased": int(incoming),
            "sold": int(outgoing),
            "stock": int(qty),
            "stock_version": int(ver),
        }
        for p, z, qty, ver, incoming, outgoing in q.all()
    ]
