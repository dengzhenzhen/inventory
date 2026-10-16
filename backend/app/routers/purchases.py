from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import models
from ..crud import get_or_create_product, get_or_create_size, get_or_create_supplier, purchase_dict
from ..database import get_db
from ..deps import current_user
from ..schemas import PurchaseBatchIn, PurchaseIn, PurchaseUpdate
from ..utils import abort, ok

router = APIRouter(prefix="/api/purchases", tags=["purchases"], dependencies=[Depends(current_user)])


def _create_one(db: Session, payload: PurchaseIn) -> models.Purchase:
    today = date.today().isoformat()
    product, _ = get_or_create_product(db, payload.style_code, payload.category, payload.supplier)
    if payload.main_image and not product.main_image:
        product.main_image = payload.main_image
    size = get_or_create_size(db, payload.size)
    supplier = get_or_create_supplier(db, payload.supplier) if payload.supplier else None
    rec = models.Purchase(
        product_id=product.id,
        style_code=product.style_code,
        size_id=size.id if size else None,
        size_text=size.name if size else None,
        quantity=payload.quantity,
        cost_price=payload.cost_price,
        purchase_date=payload.purchase_date or today,
        supplier_id=supplier.id if supplier else product.supplier_id,
        remark=payload.remark,
    )
    db.add(rec)
    db.flush()
    return rec


@router.get("")
def list_purchases(
    style_code: Optional[str] = None,
    category_id: Optional[int] = None,
    supplier_id: Optional[int] = None,
    size_id: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
):
    q = db.query(models.Purchase).join(models.Product, models.Purchase.product_id == models.Product.id)
    if style_code:
        q = q.filter(models.Purchase.style_code.like(f"%{style_code}%"))
    if category_id:
        q = q.filter(models.Product.category_id == category_id)
    if supplier_id:
        q = q.filter(models.Purchase.supplier_id == supplier_id)
    if size_id:
        q = q.filter(models.Purchase.size_id == size_id)
    if date_from:
        q = q.filter(models.Purchase.purchase_date >= date_from)
    if date_to:
        q = q.filter(models.Purchase.purchase_date <= date_to)
    total = q.count()
    items = (
        q.order_by(models.Purchase.purchase_date.desc(), models.Purchase.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return ok({"items": [purchase_dict(x) for x in items], "total": total})


@router.post("")
def create_purchase(payload: PurchaseIn, db: Session = Depends(get_db)):
    rec = _create_one(db, payload)
    db.commit()
    db.refresh(rec)
    return ok(purchase_dict(rec), "进货已保存")


@router.post("/batch")
def create_batch(payload: PurchaseBatchIn, db: Session = Depends(get_db)):
    if not payload.items:
        abort("没有可保存的数据")
    created = [_create_one(db, item) for item in payload.items]
    db.commit()
    return ok({"created": len(created)}, f"已保存 {len(created)} 条进货")


@router.put("/{pid}")
def update_purchase(pid: int, payload: PurchaseUpdate, db: Session = Depends(get_db)):
    rec = db.get(models.Purchase, pid)
    if not rec:
        abort("进货记录不存在", 404)
    data = payload.model_dump(exclude_unset=True)
    if "size" in data:
        size = get_or_create_size(db, data["size"])
        rec.size_id = size.id if size else None
        rec.size_text = size.name if size else None
    if data.get("quantity") is not None:
        rec.quantity = data["quantity"]
    if data.get("cost_price") is not None:
        rec.cost_price = data["cost_price"]
    if data.get("purchase_date"):
        rec.purchase_date = data["purchase_date"]
    if "supplier" in data:
        supplier = get_or_create_supplier(db, data["supplier"]) if data["supplier"] else None
        rec.supplier_id = supplier.id if supplier else None
    if "remark" in data:
        rec.remark = data["remark"]
    db.commit()
    db.refresh(rec)
    return ok(purchase_dict(rec), "已更新")


@router.delete("/{pid}")
def delete_purchase(pid: int, db: Session = Depends(get_db)):
    rec = db.get(models.Purchase, pid)
    if not rec:
        abort("进货记录不存在", 404)
    db.delete(rec)
    db.commit()
    return ok(None, "已删除")
