from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db
from ..deps import current_user
from ..schemas import DictIn
from ..utils import abort, ok

router = APIRouter(
    prefix="/api/dict", tags=["dict"], dependencies=[Depends(current_user)]
)

MODELS = {"category": models.Category, "supplier": models.Supplier, "size": models.Size}


def _model(kind: str):
    m = MODELS.get(kind)
    if not m:
        abort("未知字典类型", 404)
    return m


def _serialize(kind: str, obj) -> dict:
    data = {"id": obj.id, "name": obj.name}
    if kind == "supplier":
        data.update(contact=obj.contact, phone=obj.phone, remark=obj.remark)
    else:
        data["sort_order"] = getattr(obj, "sort_order", 0)
    return data


@router.get("/{kind}")
def list_dict(kind: str, db: Session = Depends(get_db)):
    m = _model(kind)
    order = m.sort_order if hasattr(m, "sort_order") else m.name
    items = db.query(m).order_by(order, m.id).all()
    return ok([_serialize(kind, x) for x in items])


@router.post("/{kind}")
def create_dict(kind: str, payload: DictIn, db: Session = Depends(get_db)):
    m = _model(kind)
    name = payload.name.strip()
    if len(name) > ({"category": 50, "supplier": 100, "size": 20}[kind]):
        abort("名称过长", 422)
    if db.query(m).filter_by(name=name).first():
        abort("名称已存在", 409)
    obj = m(name=name)
    if kind == "supplier":
        obj.contact = payload.contact
        obj.phone = payload.phone
        obj.remark = payload.remark
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return ok(_serialize(kind, obj), "已添加")


@router.put("/{kind}/{item_id}")
def update_dict(
    kind: str, item_id: int, payload: DictIn, db: Session = Depends(get_db)
):
    m = _model(kind)
    obj = db.get(m, item_id)
    if not obj:
        abort("记录不存在", 404)
    duplicate = db.query(m).filter(m.name == payload.name, m.id != item_id).first()
    if duplicate:
        abort("名称已存在", 409)
    if len(payload.name) > ({"category": 50, "supplier": 100, "size": 20}[kind]):
        abort("名称过长", 422)
    obj.name = payload.name.strip()
    if kind == "supplier":
        obj.contact = payload.contact
        obj.phone = payload.phone
        obj.remark = payload.remark
    db.commit()
    db.refresh(obj)
    return ok(_serialize(kind, obj), "已更新")


@router.delete("/{kind}/{item_id}")
def delete_dict(kind: str, item_id: int, db: Session = Depends(get_db)):
    m = _model(kind)
    obj = db.get(m, item_id)
    if not obj:
        abort("记录不存在", 404)
    db.delete(obj)
    db.commit()
    return ok(None, "已删除")
