"""Legacy single-line adapters for immutable v2 documents."""

from datetime import date
from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.orm import Session
from ..database import get_db
from ..deps import current_user
from ..schemas import PurchaseIn, PurchaseBatchIn
from ..document_schemas import DocumentIn, LineIn
from ..ledger import post, lines_query, line_dict
from ..utils import ok, abort

router = APIRouter(
    prefix="/api/purchases", tags=["purchases"], dependencies=[Depends(current_user)]
)


def adapt(x):
    return LineIn(
        style_code=x.style_code,
        size=x.size or "未指定",
        quantity=x.quantity,
        price=x.cost_price,
        category=x.category,
        supplier=x.supplier,
        main_image=x.main_image,
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
        "purchase",
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
    payload: PurchaseIn,
    idempotency_key: str | None = Header(None),
    db: Session = Depends(get_db),
    user: str = Depends(current_user),
):
    doc = post(
        db,
        DocumentIn(
            kind="purchase",
            date=payload.purchase_date or date.today().isoformat(),
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


@router.post("/batch")
def batch(
    payload: PurchaseBatchIn,
    idempotency_key: str | None = Header(None),
    db: Session = Depends(get_db),
    user: str = Depends(current_user),
):
    # The adapter preserves each historical row's date while making the complete request atomic.
    import hashlib, json
    from ..ledger_models import SystemState

    digest = hashlib.sha256(payload.model_dump_json().encode()).hexdigest()
    key = (
        "batch:" + hashlib.sha256(idempotency_key.encode()).hexdigest()
        if idempotency_key
        else None
    )
    old = db.get(SystemState, key) if key else None
    if old:
        saved = json.loads(old.value)
        if saved["hash"] != digest:
            abort("幂等键已用于其他内容", 409)
        return ok(saved["result"])
    docs = []
    for i, x in enumerate(payload.items):
        docs.append(
            post(
                db,
                DocumentIn(
                    kind="purchase",
                    date=x.purchase_date or date.today().isoformat(),
                    remark=x.remark or "",
                    lines=[adapt(x)],
                ),
                user,
                None,
            )
        )
    result = {"created": len(docs), "document_ids": [d.id for d in docs]}
    if key:
        db.add(
            SystemState(key=key, value=json.dumps({"hash": digest, "result": result}))
        )
    db.commit()
    return ok(result)
