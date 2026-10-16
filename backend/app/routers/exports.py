from io import BytesIO

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from sqlalchemy.orm import Session

from .. import models
from ..crud import purchase_dict, sale_dict, stock_rows
from ..database import get_db
from ..deps import current_user

router = APIRouter(prefix="/api/export", tags=["export"], dependencies=[Depends(current_user)])


def _response(wb: Workbook, filename: str) -> StreamingResponse:
    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/purchases.xlsx")
def export_purchases(db: Session = Depends(get_db)):
    wb = Workbook()
    ws = wb.active
    ws.title = "进货明细"
    ws.append(["款号", "分类", "厂家", "尺码", "数量", "进货价", "金额", "日期", "备注"])
    for r in db.query(models.Purchase).order_by(models.Purchase.purchase_date.desc(), models.Purchase.id.desc()).all():
        d = purchase_dict(r)
        ws.append([d["style_code"], d["category_name"], d["supplier_name"], d["size_text"], d["quantity"],
                   d["cost_price"], d["amount"], d["purchase_date"], d["remark"]])
    return _response(wb, "purchases.xlsx")


@router.get("/sales.xlsx")
def export_sales(db: Session = Depends(get_db)):
    wb = Workbook()
    ws = wb.active
    ws.title = "销售明细"
    ws.append(["款号", "分类", "尺码", "数量", "售价", "金额", "日期", "备注"])
    for r in db.query(models.Sale).order_by(models.Sale.sale_date.desc(), models.Sale.id.desc()).all():
        d = sale_dict(r)
        ws.append([d["style_code"], d["category_name"], d["size_text"], d["quantity"], d["unit_price"],
                   d["amount"], d["sale_date"], d["remark"]])
    return _response(wb, "sales.xlsx")


@router.get("/stock.xlsx")
def export_stock(db: Session = Depends(get_db)):
    wb = Workbook()
    ws = wb.active
    ws.title = "库存"
    ws.append(["款号", "品名", "分类", "尺码", "进货数量", "销售数量", "结存"])
    for r in stock_rows(db):
        p = r["product"]
        ws.append([r["style_code"], p.get("name"), r["category_name"], r["size_text"],
                   r["purchased"], r["sold"], r["stock"]])
    return _response(wb, "stock.xlsx")
