from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy import or_
from sqlalchemy.orm import Session

from .. import models
from ..crud import get_or_create_category, get_or_create_supplier, product_dict
from ..database import get_db
from ..deps import current_user
from ..schemas import ProductIn, ProductUpdate
from ..utils import abort, ok

router = APIRouter(prefix="/api/products", tags=["products"], dependencies=[Depends(current_user)])


def _resolve_category(db: Session, cid: Optional[int], cname: Optional[str]):
    if cid:
        obj = db.get(models.Category, cid)
        return obj.id if obj else None
    if cname:
        obj = get_or_create_category(db, cname)
        return obj.id if obj else None
    return None


def _resolve_supplier(db: Session, sid: Optional[int], sname: Optional[str]):
    if sid:
        obj = db.get(models.Supplier, sid)
        return obj.id if obj else None
    if sname:
        obj = get_or_create_supplier(db, sname)
        return obj.id if obj else None
    return None


@router.get("")
def list_products(
    keyword: Optional[str] = None,
    category_id: Optional[int] = None,
    supplier_id: Optional[int] = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
):
    q = db.query(models.Product)
    if keyword:
        like = f"%{keyword}%"
        q = q.filter(or_(models.Product.style_code.like(like), models.Product.name.like(like)))
    if category_id:
        q = q.filter(models.Product.category_id == category_id)
    if supplier_id:
        q = q.filter(models.Product.supplier_id == supplier_id)
    total = q.count()
    items = q.order_by(models.Product.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return ok({"items": [product_dict(p) for p in items], "total": total})


@router.get("/by-code/{style_code}")
def get_by_code(style_code: str, db: Session = Depends(get_db)):
    p = db.query(models.Product).filter_by(style_code=style_code).first()
    if not p:
        abort("款号不存在", 404)
    return ok(product_dict(p))


@router.get("/{pid}")
def get_product(pid: int, db: Session = Depends(get_db)):
    p = db.get(models.Product, pid)
    if not p:
        abort("商品不存在", 404)
    return ok(product_dict(p))


@router.post("")
def create_product(payload: ProductIn, db: Session = Depends(get_db)):
    if db.query(models.Product).filter_by(style_code=payload.style_code.strip()).first():
        abort("款号已存在", 409)
    p = models.Product(
        style_code=payload.style_code.strip(),
        name=payload.name,
        category_id=_resolve_category(db, payload.category_id, payload.category_name),
        supplier_id=_resolve_supplier(db, payload.supplier_id, payload.supplier_name),
        retail_price=payload.retail_price or 0,
        main_image=payload.main_image,
        remark=payload.remark,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return ok(product_dict(p), "已保存")


@router.put("/{pid}")
def update_product(pid: int, payload: ProductUpdate, db: Session = Depends(get_db)):
    p = db.get(models.Product, pid)
    if not p:
        abort("商品不存在", 404)
    data = payload.model_dump(exclude_unset=True)
    if data.get("style_code"):
        dup = (
            db.query(models.Product)
            .filter(models.Product.style_code == data["style_code"].strip(), models.Product.id != pid)
            .first()
        )
        if dup:
            abort("款号已存在", 409)
        p.style_code = data["style_code"].strip()
    if "name" in data:
        p.name = data["name"]
    if "category_id" in data or "category_name" in data:
        p.category_id = _resolve_category(db, data.get("category_id"), data.get("category_name"))
    if "supplier_id" in data or "supplier_name" in data:
        p.supplier_id = _resolve_supplier(db, data.get("supplier_id"), data.get("supplier_name"))
    if "retail_price" in data:
        p.retail_price = data["retail_price"]
    if "main_image" in data:
        p.main_image = data["main_image"]
    if "remark" in data:
        p.remark = data["remark"]
    db.commit()
    db.refresh(p)
    return ok(product_dict(p), "已更新")


@router.delete("/{pid}")
def delete_product(pid: int, db: Session = Depends(get_db)):
    p = db.get(models.Product, pid)
    if not p:
        abort("商品不存在", 404)
    has_purchase = db.query(models.Purchase).filter_by(product_id=pid).first()
    has_sale = db.query(models.Sale).filter_by(product_id=pid).first()
    if has_purchase or has_sale:
        abort("该款式已有进销记录，不能删除")
    db.delete(p)
    db.commit()
    return ok(None, "已删除")
