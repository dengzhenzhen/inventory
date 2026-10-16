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


def get_or_create_product(db: Session, style_code: str, category_name: Optional[str] = None,
                          supplier_name: Optional[str] = None):
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
        "retail_price": p.retail_price or 0,
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
        "category_name": r.product.category.name if (r.product and r.product.category) else None,
        "supplier_id": r.supplier_id,
        "supplier_name": (r.supplier.name if r.supplier else (r.product.supplier.name if (r.product and r.product.supplier) else None)),
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
        "category_name": r.product.category.name if (r.product and r.product.category) else None,
        "size_id": r.size_id,
        "size_text": r.size_text,
        "quantity": r.quantity,
        "unit_price": r.unit_price,
        "amount": round((r.quantity or 0) * (r.unit_price or 0), 2),
        "sale_date": r.sale_date,
        "remark": r.remark,
    }


# ---------- 库存聚合 ----------
def _aggregate(db: Session, model) -> dict:
    rows = (
        db.query(model.style_code, model.size_text, func.sum(model.quantity))
        .group_by(model.style_code, model.size_text)
        .all()
    )
    return {(r[0], r[1] or ""): int(r[2] or 0) for r in rows}


def current_stock(db: Session, style_code: str, size_text: str) -> int:
    purchased = (
        db.query(func.coalesce(func.sum(models.Purchase.quantity), 0))
        .filter(models.Purchase.style_code == style_code, models.Purchase.size_text == size_text)
        .scalar()
    )
    sold = (
        db.query(func.coalesce(func.sum(models.Sale.quantity), 0))
        .filter(models.Sale.style_code == style_code, models.Sale.size_text == size_text)
        .scalar()
    )
    return int(purchased or 0) - int(sold or 0)


def stock_rows(db: Session, keyword: Optional[str] = None, category_id: Optional[int] = None,
               only_negative: bool = False) -> list:
    purchased = _aggregate(db, models.Purchase)
    sold = _aggregate(db, models.Sale)
    keys = set(purchased) | set(sold)

    products = {p.style_code: p for p in db.query(models.Product).all()}
    size_ids = {s.name: s.id for s in db.query(models.Size).all()}

    result = []
    for style_code, size_text in keys:
        p = products.get(style_code)
        if keyword and keyword not in style_code and not (p and p.name and keyword in p.name):
            continue
        if category_id and (not p or p.category_id != category_id):
            continue
        purchased_qty = purchased.get((style_code, size_text), 0)
        sold_qty = sold.get((style_code, size_text), 0)
        stock = purchased_qty - sold_qty
        if only_negative and stock >= 0:
            continue
        result.append({
            "style_code": style_code,
            "size_id": size_ids.get(size_text),
            "size_text": size_text,
            "product": product_dict(p) if p else {"style_code": style_code, "name": "(未建档)"},
            "category_name": p.category.name if (p and p.category) else None,
            "purchased": purchased_qty,
            "sold": sold_qty,
            "stock": stock,
        })
    result.sort(key=lambda r: (r["style_code"], r["size_text"]))
    return result
