from datetime import date
from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.orm import Session
from ..database import get_db
from ..deps import current_user
from ..ledger_models import Document, Audit, DocumentLine
from ..document_schemas import DocumentIn, ReasonIn, RecomputeIn
from ..ledger import post, void, document_dict, calculate, fingerprint, recompute
from ..utils import ok, abort

router = APIRouter(
    prefix="/api/documents", tags=["documents"], dependencies=[Depends(current_user)]
)


@router.get("")
def listing(
    kind: str | None = None,
    status: str | None = None,
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
    from sqlalchemy.orm import selectinload
    from ..models import Product

    q = db.query(Document)
    if kind:
        q = q.filter_by(kind=kind)
    if status:
        q = q.filter_by(status=status)
    from sqlalchemy import and_

    predicates = []
    if style_code:
        predicates.append(
            DocumentLine.product.has(
                Product.style_code.contains(style_code, autoescape=True)
            )
        )
    if category_id:
        predicates.append(DocumentLine.product.has(Product.category_id == category_id))
    if supplier_id:
        predicates.append(DocumentLine.supplier_id == supplier_id)
    if size_id:
        predicates.append(DocumentLine.size_id == size_id)
    if predicates:
        q = q.filter(Document.lines.any(and_(*predicates)))
    if date_from:
        q = q.filter(Document.date >= str(date_from))
    if date_to:
        q = q.filter(Document.date <= str(date_to))
    total = q.count()
    q = q.options(
        selectinload(Document.lines)
        .joinedload(DocumentLine.product)
        .joinedload(Product.category),
        selectinload(Document.lines).joinedload(DocumentLine.size),
        selectinload(Document.lines).joinedload(DocumentLine.supplier),
    )
    return ok(
        {
            "items": [
                document_dict(d)
                for d in q.order_by(Document.id.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            ],
            "total": total,
        }
    )


@router.post("")
def create(
    payload: DocumentIn,
    idempotency_key: str = Header(..., min_length=1, max_length=100),
    db: Session = Depends(get_db),
    user: str = Depends(current_user),
):
    doc = post(db, payload, user, idempotency_key)
    db.commit()
    return ok(document_dict(doc))


@router.get("/cost-preview")
def preview(db: Session = Depends(get_db)):
    result = calculate(db, settle_negative=True)
    changes = []
    for lid, (cost, status) in result.items():
        line = db.get(DocumentLine, lid)
        if line.dirty or (line.cost_micro, line.cost_status) != (cost, status):
            changes.append(
                {
                    "line_id": lid,
                    "document_id": line.document_id,
                    "before": line.cost_micro,
                    "after": cost,
                    "status": status,
                }
            )
    return ok({"fingerprint": fingerprint(db), "changes": changes})


@router.post("/cost-recompute")
def confirm(
    payload: RecomputeIn,
    db: Session = Depends(get_db),
    user: str = Depends(current_user),
):
    changes = recompute(db, user, payload.fingerprint)
    db.commit()
    return ok({"changed": len(changes)})


@router.get("/audit")
def audits(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    q = db.query(Audit)
    return ok(
        {
            "total": q.count(),
            "items": [
                {
                    "id": a.id,
                    "actor": a.actor,
                    "action": a.action,
                    "document_id": a.document_id,
                    "detail": a.detail,
                    "created_at": a.created_at.isoformat(),
                }
                for a in q.order_by(Audit.id.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            ],
        }
    )


@router.get("/{doc_id}")
def detail(doc_id: int, db: Session = Depends(get_db)):
    doc = db.get(Document, doc_id)
    if not doc:
        abort("单据不存在", 404)
    return ok(document_dict(doc))


@router.post("/{doc_id}/void")
def cancel(
    doc_id: int,
    payload: ReasonIn,
    db: Session = Depends(get_db),
    user: str = Depends(current_user),
):
    doc = void(db, doc_id, payload.reason, user)
    db.commit()
    return ok(document_dict(doc))
