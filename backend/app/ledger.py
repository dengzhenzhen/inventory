"""Transactional document posting, stable SKU inventory, and deterministic costing."""

import hashlib
import json
from sqlalchemy import func
from sqlalchemy.orm import joinedload
from . import models as m
from .ledger_models import Document, DocumentLine as Line, Movement, Audit
from .crud import get_or_create_product, get_or_create_size, get_or_create_supplier
from .money import cents, rounded_div, amount
from .utils import abort

SIGNS = {"purchase": 1, "sale": -1, "purchase_return": -1, "sale_return": 1}


def audit(db, actor, action, detail, document_id=None):
    db.add(
        Audit(
            actor=actor,
            action=action,
            detail=json.dumps(detail, ensure_ascii=False, default=str),
            document_id=document_id,
        )
    )


def stock(db, product_id, size_id):
    return int(
        db.query(func.coalesce(func.sum(Movement.quantity), 0))
        .filter_by(product_id=product_id, size_id=size_id)
        .scalar()
    )


def version(db, product_id, size_id):
    return int(
        db.query(func.coalesce(func.max(Movement.id), 0))
        .filter_by(product_id=product_id, size_id=size_id)
        .scalar()
    )


def fingerprint(db):
    docs = db.query(Document).order_by(Document.id).all()
    lines = db.query(Line).order_by(Line.id).all()
    raw = (
        [(d.id, d.kind, d.date, d.status) for d in docs],
        [
            (x.id, x.quantity, x.price_cents, x.cost_micro, x.cost_status, x.dirty)
            for x in lines
        ],
    )
    return hashlib.sha256(json.dumps(raw, ensure_ascii=False).encode()).hexdigest()


def calculate(db, skus=None, settle_negative=False):
    """Replay posted events; existing snapshots remain untouched until explicit confirmation."""
    query = db.query(Line).join(Document).filter(Document.status == "posted")
    if skus:
        from sqlalchemy import tuple_

        query = query.filter(tuple_(Line.product_id, Line.size_id).in_(skus))
    rows = query.options(joinedload(Line.document)).all()
    by_id = {x.id: x for x in rows}
    deficits = {}

    priority = {
        "purchase": 0,
        "sale_return": 2,
        "purchase_return": 3,
        "sale": 4,
        "count": 5,
        "adjustment": 5,
    }
    rows.sort(
        key=lambda x: (
            x.document.date,
            x.document.created_at,
            priority[x.document.kind],
            x.id,
        )
    )
    # Legacy same-day creation order does not encode actual transaction time.
    rows.sort(
        key=lambda x: (
            x.document.date,
            0 if x.document.legacy_id and x.document.kind == "purchase" else 1,
            x.document.created_at,
            priority[x.document.kind],
            x.id,
        )
    )
    state, result = {}, {}
    for line in rows:
        key = (line.product_id, line.size_id)
        qty, value, last = state.get(key, (0, 0, None))
        kind = line.document.kind
        q = line.quantity
        status = "known"
        if kind == "purchase":
            cost = line.price_cents * 10_000
            if settle_negative:
                available = q
                queue = deficits.setdefault(key, [])
                while available > 0 and queue:
                    debt = queue[0]
                    used = min(available, debt["remaining"])
                    debt["value"] += used * cost
                    debt["covered"] += used
                    debt["remaining"] -= used
                    available -= used
                    assumed = debt["remaining"] * (debt["fallback"] or 0)
                    new_cost = rounded_div(debt["value"] + assumed, debt["quantity"])
                    result[debt["id"]] = (
                        new_cost,
                        "known" if not debt["remaining"] else "provisional",
                    )
                    if not debt["remaining"]:
                        queue.pop(0)

        elif kind in ("sale_return", "purchase_return"):
            original = by_id.get(line.original_line_id)
            original_result = (
                result.get(original.id) if original and settle_negative else None
            )
            cost = (
                original_result[0]
                if original_result
                else (original.cost_micro if original else None)
            )
            status = (
                original_result[1]
                if original_result
                else (original.cost_status if original else "unknown")
            )
        elif kind in ("adjustment", "count") and q > 0 and line.price_cents:
            cost = line.price_cents * 10_000
        else:
            cost = (
                rounded_div(value, qty)
                if qty > 0 and value is not None and value >= 0
                else last
            )
            if cost is None:
                status = "unknown"
            elif qty <= 0 or (value is not None and value < 0) or (q < 0 and -q > qty):
                status = "provisional"
        result[line.id] = (cost, status)
        if kind == "sale" and -q > max(qty, 0):
            covered = min(-q, max(qty, 0))
            deficits.setdefault(key, []).append(
                {
                    "id": line.id,
                    "remaining": -q - covered,
                    "quantity": -q,
                    "value": covered * (cost or 0),
                    "covered": covered,
                    "fallback": cost,
                }
            )
        if q > 0:
            if qty <= 0:
                # An incoming lot covers negative units; remaining positive inventory uses its cost.
                qty += q
                value = qty * cost if cost is not None else None
            else:
                value = (
                    value + q * cost if value is not None and cost is not None else None
                )
                qty += q
            if qty > 0 and value is not None:
                last = rounded_div(value, qty)
            elif cost is not None:
                last = cost
        else:
            value = value + q * cost if value is not None and cost is not None else None
            qty += q
            if cost is not None:
                last = cost
            if qty <= 0:
                value = 0
        state[key] = (qty, value, last)
    return result


def recompute(db, actor, expected=None):
    if expected and expected != fingerprint(db):
        abort("预览后数据已变化，请重新预览", 409)
    result = calculate(db, settle_negative=True)
    changed = []
    for lid, (cost, status) in result.items():
        line = db.get(Line, lid)
        if (line.cost_micro, line.cost_status) != (cost, status) or line.dirty:
            changed.append(
                {
                    "line_id": lid,
                    "before": line.cost_micro,
                    "after": cost,
                    "status": status,
                }
            )
            line.cost_micro = cost
            line.cost_status = status
            line.dirty = 0
    audit(db, actor, "cost_recompute", changed)
    return changed


def line_dict(line):
    d = line.document
    p = line.product
    return {
        "id": line.id,
        "document_id": d.id,
        "kind": d.kind,
        "status": d.status,
        "product_id": line.product_id,
        "style_code": p.style_code,
        "style_snapshot": line.style_snapshot,
        "size_id": line.size_id,
        "size_text": line.size.name,
        "size_snapshot": line.size_snapshot,
        "category_id": p.category_id,
        "category_name": p.category.name if p.category else None,
        "supplier_id": line.supplier_id,
        "supplier_name": line.supplier.name if line.supplier else None,
        "quantity": abs(line.quantity),
        "signed_quantity": line.quantity,
        "unit_price": line.price_cents / 100,
        "cost_price": line.price_cents / 100,
        "amount": abs(line.quantity) * line.price_cents / 100,
        "cost": amount(line.cost_micro, abs(line.quantity)) / 100
        if line.cost_micro is not None
        else None,
        "cost_status": line.cost_status,
        "cost_dirty": bool(line.dirty),
        "sale_date": d.date,
        "purchase_date": d.date,
        "date": d.date,
        "remark": d.remark,
        "original_line_id": line.original_line_id,
    }


def document_dict(doc):
    return {
        "id": doc.id,
        "kind": doc.kind,
        "date": doc.date,
        "status": doc.status,
        "remark": doc.remark,
        "actor": doc.actor,
        "created_at": doc.created_at.isoformat(),
        "lines": [line_dict(x) for x in doc.lines],
    }


def post(db, payload, actor, key=None):
    raw = payload.model_dump(mode="json")
    digest = hashlib.sha256(
        json.dumps(raw, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()
    if key:
        if not 1 <= len(key) <= 100:
            abort("幂等键长度须为 1–100", 422)
        old = db.query(Document).filter_by(idempotency_key=key).first()
        if old:
            if old.request_hash != digest:
                abort("幂等键已用于其他内容", 409)
            return old
    doc = Document(
        kind=payload.kind,
        date=payload.date,
        remark=payload.remark,
        actor=actor,
        idempotency_key=key,
        request_hash=digest,
    )
    db.add(doc)
    db.flush()
    seen = set()
    for item in payload.lines:
        if payload.kind == "purchase":
            product, _ = get_or_create_product(
                db, item.style_code, item.category, item.supplier
            )
            if item.main_image and not product.main_image:
                product.main_image = item.main_image
        else:
            product = db.query(m.Product).filter_by(style_code=item.style_code).first()
            if not product:
                abort("款号不存在", 404)
        size = get_or_create_size(db, item.size or "未指定")
        sku = (product.id, size.id)
        q = item.quantity * SIGNS.get(payload.kind, 1)
        original = None
        if payload.kind in ("sale_return", "purchase_return"):
            original = (
                db.get(Line, item.original_line_id) if item.original_line_id else None
            )
            expected = "sale" if payload.kind == "sale_return" else "purchase"
            if (
                not original
                or original.document.status != "posted"
                or original.document.kind != expected
                or (original.product_id, original.size_id) != sku
            ):
                abort("退货必须关联相同商品尺码的有效原单明细")
            if payload.date < original.document.date:
                abort("退货日期不能早于原单")
            returned = (
                db.query(func.coalesce(func.sum(func.abs(Line.quantity)), 0))
                .join(Document)
                .filter(
                    Line.original_line_id == original.id, Document.status == "posted"
                )
                .scalar()
            )
            if returned + item.quantity > abs(original.quantity):
                abort("累计退货数量超过原单数量", 409)
        if payload.kind in ("count", "adjustment"):
            if not payload.remark:
                abort("盘点或调整必须填写原因")
            if sku in seen:
                abort("同一盘点单不能重复商品尺码")
            seen.add(sku)
            if item.stock_version is None or item.stock_version != version(db, *sku):
                abort("库存已变化，请刷新库存后重新核对", 409)
            if payload.kind == "count":
                if item.counted is None:
                    abort("请填写实盘数量")
                q = item.counted - stock(db, *sku)
            else:
                if item.adjustment_sign not in (-1, 1):
                    abort("调整方向无效")
                q = item.quantity * item.adjustment_sign
        supplier = get_or_create_supplier(db, item.supplier) if item.supplier else None
        line = Line(
            document_id=doc.id,
            product_id=product.id,
            size_id=size.id,
            supplier_id=supplier.id if supplier else product.supplier_id,
            style_snapshot=product.style_code,
            size_snapshot=size.name,
            quantity=q,
            price_cents=original.price_cents if original else cents(item.price),
            original_line_id=original.id if original else None,
        )
        db.add(line)
        db.flush()
        db.add(
            Movement(
                line_id=line.id, product_id=product.id, size_id=size.id, quantity=q
            )
        )
        db.flush()
    # Cost snapshots for new lines are computed as of their event position.
    computed = calculate(db, {(x.product_id, x.size_id) for x in doc.lines})
    for line in doc.lines:
        line.cost_micro, line.cost_status = computed[line.id]
        if (
            payload.kind in ("count", "adjustment")
            and line.quantity > 0
            and line.cost_micro is None
        ):
            abort("无历史成本的盘盈或调增必须输入成本")
    affected = {(x.product_id, x.size_id) for x in doc.lines}
    from sqlalchemy import tuple_

    for line in (
        db.query(Line)
        .join(Document)
        .filter(
            Document.status == "posted",
            Document.date >= doc.date,
            Line.document_id != doc.id,
            tuple_(Line.product_id, Line.size_id).in_(affected),
        )
    ):
        if (line.cost_micro, line.cost_status) != computed.get(
            line.id, (line.cost_micro, line.cost_status)
        ):
            line.dirty = 1
    if payload.kind == "purchase":
        db.query(Line).filter(
            tuple_(Line.product_id, Line.size_id).in_(affected),
            Line.cost_status.in_(["unknown", "provisional"]),
        ).update({"dirty": 1}, synchronize_session="fetch")
    audit(db, actor, "post", raw, doc.id)
    db.flush()
    return doc


def void(db, doc_id, reason, actor):
    doc = db.get(Document, doc_id)
    if not doc:
        abort("单据不存在", 404)
    if doc.status == "void":
        return doc
    ids = [x.id for x in doc.lines]
    if (
        db.query(Line)
        .join(Document)
        .filter(Line.original_line_id.in_(ids), Document.status == "posted")
        .first()
    ):
        abort("请先作废关联退货单", 409)
    doc.status = "void"
    for line in doc.lines:
        db.add(
            Movement(
                line_id=line.id,
                product_id=line.product_id,
                size_id=line.size_id,
                quantity=-line.quantity,
                reversal=1,
            )
        )
        db.query(Line).filter(
            Line.product_id == line.product_id, Line.size_id == line.size_id
        ).update({"dirty": 1})
    audit(db, actor, "void", {"reason": reason}, doc.id)
    db.flush()
    return doc


def lines_query(
    db,
    kind=None,
    style_code=None,
    category_id=None,
    supplier_id=None,
    size_id=None,
    date_from=None,
    date_to=None,
    status="posted",
):
    q = db.query(Line).join(Document).join(m.Product, Line.product_id == m.Product.id)
    if kind:
        q = q.filter(Document.kind == kind)
    if status:
        q = q.filter(Document.status == status)
    if style_code:
        q = q.filter(m.Product.style_code.contains(style_code, autoescape=True))
    if category_id:
        q = q.filter(m.Product.category_id == category_id)
    if supplier_id:
        q = q.filter(Line.supplier_id == supplier_id)
    if size_id:
        q = q.filter(Line.size_id == size_id)
    if date_from:
        q = q.filter(Document.date >= date_from)
    if date_to:
        q = q.filter(Document.date <= date_to)
    return q.options(
        joinedload(Line.document),
        joinedload(Line.product).joinedload(m.Product.category),
        joinedload(Line.size),
        joinedload(Line.supplier),
    ).order_by(Document.date.desc(), Line.id.desc())
