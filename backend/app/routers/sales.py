"""Legacy single-line adapters for immutable v2 documents."""

from datetime import date
from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.orm import Session
from ..database import get_db
from ..deps import current_user
from ..schemas import SaleIn
from ..document_schemas import DocumentIn, LineIn
from ..ledger import post, lines_query, line_dict
from ..utils import ok, abort

router = APIRouter(
    prefix="/api/sales", tags=["sales"], dependencies=[Depends(current_user)]
)


def adapt(x):
    return LineIn(
        style_code=x.style_code,
        size=x.size or "未指定",
        quantity=x.quantity,
        price=x.unit_price,
    )


@router.get("")
def listing(
    style_code: str | None = None,
    category_id: int | None = None,
    supplier_id: int | None = None,
    size_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    q = lines_query(
        db,
        "sale",
        style_code,
        category_id,
        supplier_id,
        size_id,
        str(date_from) if date_from else None,
        str(date_to) if date_to else None,
    )
    return ok(
        {
            "items": [
                line_dict(x) for x in q.offset((page - 1) * page_size).limit(page_size)
            ],
            "total": q.count(),
        }
    )


@router.post("")
def create(
    payload: SaleIn,
    idempotency_key: str | None = Header(None),
    db: Session = Depends(get_db),
    user: str = Depends(current_user),
):
    doc = post(
        db,
        DocumentIn(
            kind="sale",
            date=payload.sale_date or date.today().isoformat(),
            remark=payload.remark or "",
            lines=[adapt(payload)],
        ),
        user,
        idempotency_key,
    )
    db.commit()
    result = line_dict(doc.lines[0])
    from ..ledger import stock

    line = doc.lines[0]
    result["warning"] = (
        "已产生负库存，请核对或补货"
        if stock(db, line.product_id, line.size_id) < 0
        else None
    )
    return ok(result)


@router.put("/{record_id}")
@router.delete("/{record_id}")
def immutable(record_id: int):
    abort("正式单据不能修改或删除，请在单据中心作废并复制重开", 409)
