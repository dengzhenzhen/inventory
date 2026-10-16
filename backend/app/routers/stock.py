from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..crud import current_stock, stock_rows
from ..database import get_db
from ..deps import current_user
from ..utils import ok

router = APIRouter(prefix="/api/stock", tags=["stock"], dependencies=[Depends(current_user)])


@router.get("")
def list_stock(
    keyword: Optional[str] = None,
    category_id: Optional[int] = None,
    only_negative: bool = False,
    db: Session = Depends(get_db),
):
    return ok(stock_rows(db, keyword=keyword, category_id=category_id, only_negative=only_negative))


@router.get("/current")
def get_current(style_code: str, size: str, db: Session = Depends(get_db)):
    return ok({"style_code": style_code, "size_text": size, "stock": current_stock(db, style_code, size)})
