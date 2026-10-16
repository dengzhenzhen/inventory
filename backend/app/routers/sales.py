from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import models
from ..crud import current_stock, get_or_create_size, sale_dict
from ..database import get_db
from ..deps import current_user
from ..schemas import SaleIn, SaleUpdate
from ..utils import abort, ok

router = APIRouter(prefix="/api/sales", tags=["sales"], dependencies=[Depends(current_user)])


@router.get("")
def list_sales(
    style_code: Optional[str] = None,
    category_id: Optional[int] = None,
    size_id: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
):
    q = db.query(models.Sale).join(models.Product, models.Sale.product_id == models.Product.id)
    if style_code:
        q = q.filter(models.Sale.style_code.like(f"%{style_code}%"))
    if category_id:
        q = q.filter(models.Product.category_id == category_id)
    if size_id:
        q = q.filter(models.Sale.size_id == size_id)
    if date_from:
        q = q.filter(models.Sale.sale_date >= date_from)
    if date_to:
        q = q.filter(models.Sale.sale_date <= date_to)
    total = q.count()
    items = (
        q.order_by(models.Sale.sale_date.desc(), models.Sale.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return ok({"items": [sale_dict(x) for x in items], "total": total})


@router.post("")
def create_sale(payload: SaleIn, db: Session = Depends(get_db)):
    product = db.query(models.Product).filter_by(style_code=payload.style_code.strip()).first()
    if not product:
        abort("款号不存在，请先在商品档案中建档")
    size = get_or_create_size(db, payload.size)
    size_text = size.name if size else payload.size.strip()
    stock_before = current_stock(db, product.style_code, size_text)
    rec = models.Sale(
        product_id=product.id,
        style_code=product.style_code,
        size_id=size.id if size else None,
        size_text=size_text,
        quantity=payload.quantity,
        unit_price=payload.unit_price,
        sale_date=payload.sale_date or date.today().isoformat(),
        remark=payload.remark,
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    data = sale_dict(rec)
    data["stock_before"] = stock_before
    data["stock_after"] = stock_before - payload.quantity
    if payload.quantity > stock_before:
        data["warning"] = f"库存不足：当前库存 {stock_before} 件，本次销售 {payload.quantity} 件，已产生负库存 {stock_before - payload.quantity}"
    else:
        data["warning"] = None
    return ok(data, data["warning"] or "出库成功")


@router.put("/{sid}")
def update_sale(sid: int, payload: SaleUpdate, db: Session = Depends(get_db)):
    rec = db.get(models.Sale, sid)
    if not rec:
        abort("销售记录不存在", 404)
    data = payload.model_dump(exclude_unset=True)
    if "size" in data and data["size"]:
        size = get_or_create_size(db, data["size"])
        rec.size_id = size.id if size else None
        rec.size_text = size.name if size else data["size"]
    if data.get("quantity") is not None:
        rec.quantity = data["quantity"]
    if data.get("unit_price") is not None:
        rec.unit_price = data["unit_price"]
    if data.get("sale_date"):
        rec.sale_date = data["sale_date"]
    if "remark" in data:
        rec.remark = data["remark"]
    db.commit()
    db.refresh(rec)
    return ok(sale_dict(rec), "已更新")


@router.delete("/{sid}")
def delete_sale(sid: int, db: Session = Depends(get_db)):
    rec = db.get(models.Sale, sid)
    if not rec:
        abort("销售记录不存在", 404)
    db.delete(rec)
    db.commit()
    return ok(None, "已删除")
