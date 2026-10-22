from datetime import date
from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session
from ..database import get_db
from ..deps import current_user
from ..ledger_models import Document as D, DocumentLine as L, Movement, SystemState
from ..models import Product, Category
from ..utils import ok

router = APIRouter(
    prefix="/api/stats", tags=["stats"], dependencies=[Depends(current_user)]
)


def base(db, date_from, date_to):
    q = db.query(L).join(D).filter(D.status == "posted")
    if date_from:
        q = q.filter(D.date >= str(date_from))
    if date_to:
        q = q.filter(D.date <= str(date_to))
    return q


@router.get("/summary")
def summary(
    date_from: date | None = None,
    date_to: date | None = None,
    db: Session = Depends(get_db),
):
    q = base(db, date_from, date_to)
    purchase = (
        q.filter(D.kind.in_(["purchase", "purchase_return"]))
        .with_entities(func.coalesce(func.sum(L.quantity * L.price_cents), 0))
        .scalar()
    )
    sales = (
        q.filter(D.kind.in_(["sale", "sale_return"]))
        .with_entities(func.coalesce(func.sum(-L.quantity * L.price_cents), 0))
        .scalar()
    )
    # Cost is stored in millionths of currency; integer rounding is performed per line.
    cost = 0
    unknown = provisional = dirty = 0
    from ..money import amount

    for qty, c, status, changed in q.filter(
        D.kind.in_(["sale", "sale_return"])
    ).with_entities(L.quantity, L.cost_micro, L.cost_status, L.dirty):
        if c is None:
            unknown += 1
        else:
            cost += amount(c, -qty)
        provisional += int(status == "provisional")
        dirty += int(bool(changed))
    notice = db.get(SystemState, "upgrade_notice")
    return ok(
        {
            "purchase_amount": purchase / 100,
            "sale_amount": sales / 100,
            "estimated_cost": cost / 100,
            "profit": (sales - cost) / 100 if not unknown else None,
            "unknown_cost_lines": unknown,
            "provisional_cost_lines": provisional,
            "dirty_cost_lines": dirty,
            "styles": db.query(func.count(Product.id)).scalar(),
            "pieces": int(
                db.query(func.coalesce(func.sum(Movement.quantity), 0)).scalar()
            ),
            "upgrade_notice": notice.value if notice else None,
        }
    )


@router.get("/daily-sales")
def daily(
    date_from: date | None = None,
    date_to: date | None = None,
    db: Session = Depends(get_db),
):
    q = base(db, date_from, date_to).filter(D.kind.in_(["sale", "sale_return"]))
    rows = (
        q.with_entities(D.date, func.sum(-L.quantity * L.price_cents))
        .group_by(D.date)
        .order_by(D.date)
    )
    return ok([{"date": d, "amount": v / 100} for d, v in rows])


@router.get("/category-rank")
def rank(
    date_from: date | None = None,
    date_to: date | None = None,
    db: Session = Depends(get_db),
):
    rows = (
        base(db, date_from, date_to)
        .filter(D.kind.in_(["purchase", "purchase_return"]))
        .join(Product, L.product_id == Product.id)
        .outerjoin(Category, Product.category_id == Category.id)
        .with_entities(Category.name, func.sum(L.quantity * L.price_cents))
        .group_by(Category.name)
        .all()
    )
    total = sum(v for _, v in rows)
    return ok(
        sorted(
            [
                {
                    "name": n or "未分类",
                    "amount": v / 100,
                    "pct": max(0, min(100, round(v / total * 100))) if total > 0 else 0,
                }
                for n, v in rows
            ],
            key=lambda r: r["amount"],
            reverse=True,
        )
    )
