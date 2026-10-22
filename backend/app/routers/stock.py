from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..crud import current_stock, stock_rows, stock_query
from ..database import get_db
from ..deps import current_user
from ..utils import ok

router = APIRouter(
    prefix="/api/stock", tags=["stock"], dependencies=[Depends(current_user)]
)


@router.get("")
def list_stock(
    keyword: Optional[str] = None,
    category_id: Optional[int] = None,
    only_negative: bool = False,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return ok(
        {
            "items": stock_rows(
                db, keyword, category_id, only_negative, page, page_size
            ),
            "total": stock_query(db, keyword, category_id, only_negative).count(),
        }
    )


@router.get("/current")
def get_current(style_code: str, size: str, db: Session = Depends(get_db)):
    from ..models import Product, Size
    from ..ledger import version

    p = db.query(Product).filter_by(style_code=style_code).first()
    z = db.query(Size).filter_by(name=size or "未指定").first()
    return ok(
        {
            "style_code": style_code,
            "size_text": size,
            "stock": current_stock(db, style_code, size),
            "stock_version": version(db, p.id, z.id) if p and z else 0,
        }
    )
