from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models
from ..crud import stock_rows
from ..database import get_db
from ..deps import current_user
from ..utils import ok

router = APIRouter(prefix="/api/stats", tags=["stats"], dependencies=[Depends(current_user)])


def _purchase_amount(db: Session, date_from, date_to) -> float:
    q = db.query(func.coalesce(func.sum(models.Purchase.quantity * models.Purchase.cost_price), 0))
    if date_from:
        q = q.filter(models.Purchase.purchase_date >= date_from)
    if date_to:
        q = q.filter(models.Purchase.purchase_date <= date_to)
    return float(q.scalar() or 0)


def _sale_amount(db: Session, date_from, date_to) -> float:
    q = db.query(func.coalesce(func.sum(models.Sale.quantity * models.Sale.unit_price), 0))
    if date_from:
        q = q.filter(models.Sale.sale_date >= date_from)
    if date_to:
        q = q.filter(models.Sale.sale_date <= date_to)
    return float(q.scalar() or 0)


def _estimated_cost(db: Session, date_from, date_to) -> float:
    q = db.query(models.Sale)
    if date_from:
        q = q.filter(models.Sale.sale_date >= date_from)
    if date_to:
        q = q.filter(models.Sale.sale_date <= date_to)
    sales = q.all()
    cache: dict = {}
    cost = 0.0
    for s in sales:
        if s.style_code not in cache:
            ps = db.query(models.Purchase).filter_by(style_code=s.style_code).all()
            total_q = sum(p.quantity for p in ps)
            total_c = sum(p.quantity * p.cost_price for p in ps)
            cache[s.style_code] = (total_c / total_q) if total_q else 0.0
        cost += cache[s.style_code] * s.quantity
    return cost


@router.get("/summary")
def summary(date_from: Optional[str] = None, date_to: Optional[str] = None, db: Session = Depends(get_db)):
    purchase_amount = _purchase_amount(db, date_from, date_to)
    sale_amount = _sale_amount(db, date_from, date_to)
    est_cost = _estimated_cost(db, date_from, date_to)
    styles = db.query(func.count(models.Product.id)).scalar() or 0
    pieces = sum(r["stock"] for r in stock_rows(db))
    return ok({
        "purchase_amount": round(purchase_amount, 2),
        "sale_amount": round(sale_amount, 2),
        "profit": round(sale_amount - est_cost, 2),
        "estimated_cost": round(est_cost, 2),
        "styles": int(styles),
        "pieces": int(pieces),
    })


@router.get("/daily-sales")
def daily_sales(date_from: Optional[str] = None, date_to: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(models.Sale.sale_date, func.coalesce(func.sum(models.Sale.quantity * models.Sale.unit_price), 0))
    if date_from:
        q = q.filter(models.Sale.sale_date >= date_from)
    if date_to:
        q = q.filter(models.Sale.sale_date <= date_to)
    rows = q.group_by(models.Sale.sale_date).order_by(models.Sale.sale_date).all()
    return ok([{"date": r[0], "amount": round(float(r[1] or 0), 2)} for r in rows])


@router.get("/category-rank")
def category_rank(date_from: Optional[str] = None, date_to: Optional[str] = None, db: Session = Depends(get_db)):
    q = (
        db.query(models.Category.name, func.coalesce(func.sum(models.Purchase.quantity * models.Purchase.cost_price), 0))
        .select_from(models.Purchase)
        .join(models.Product, models.Purchase.product_id == models.Product.id)
        .join(models.Category, models.Product.category_id == models.Category.id)
    )
    if date_from:
        q = q.filter(models.Purchase.purchase_date >= date_from)
    if date_to:
        q = q.filter(models.Purchase.purchase_date <= date_to)
    rows = q.group_by(models.Category.name).all()
    total = sum(float(r[1] or 0) for r in rows) or 1.0
    data = [
        {"name": r[0], "amount": round(float(r[1] or 0), 2), "pct": round(float(r[1] or 0) / total * 100)}
        for r in rows
    ]
    data.sort(key=lambda x: x["amount"], reverse=True)
    return ok(data)
