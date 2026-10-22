from datetime import date
from io import BytesIO
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from openpyxl.cell import WriteOnlyCell
from sqlalchemy.orm import Session
from ..database import get_db
from ..deps import current_user
from ..crud import stock_rows
from ..ledger import lines_query, line_dict

router = APIRouter(
    prefix="/api/export", tags=["export"], dependencies=[Depends(current_user)]
)


def workbook(headers):
    wb = Workbook(write_only=True)
    ws = wb.create_sheet("明细")
    ws.append(headers)
    return wb, ws


def append(ws, values):
    cells = []
    for value in values:
        cell = WriteOnlyCell(ws, value=value)
        if isinstance(value, str):
            cell.data_type = "s"
        cells.append(cell)
    ws.append(cells)


def response(wb, name):
    stream = BytesIO()
    wb.save(stream)
    stream.seek(0)
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{name}.xlsx"'},
    )


def details(
    db,
    kind,
    style_code,
    category_id,
    supplier_id,
    size_id,
    date_from,
    date_to,
    status="posted",
):
    wb, ws = workbook(
        [
            "单据号",
            "类型",
            "状态",
            "款号",
            "原款号",
            "分类",
            "厂家",
            "尺码",
            "数量",
            "单价",
            "金额",
            "日期",
            "成本状态",
            "备注",
        ]
    )
    q = lines_query(
        db,
        kind,
        style_code,
        category_id,
        supplier_id,
        size_id,
        str(date_from) if date_from else None,
        str(date_to) if date_to else None,
        status=None if status == "all" else status,
    )
    for line in q:
        d = line_dict(line)
        append(
            ws,
            [
                d["document_id"],
                d["kind"],
                d["status"],
                d["style_code"],
                d["style_snapshot"],
                d["category_name"],
                d["supplier_name"],
                d["size_text"],
                d["signed_quantity"],
                d["unit_price"],
                d["amount"],
                d["date"],
                "待重算" if d["cost_dirty"] else d["cost_status"],
                d["remark"],
            ],
        )
    return response(wb, kind or "documents")


@router.get("/purchases.xlsx")
def purchases(
    style_code: str | None = None,
    category_id: int | None = None,
    supplier_id: int | None = None,
    size_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    db: Session = Depends(get_db),
):
    return details(
        db,
        "purchase",
        style_code,
        category_id,
        supplier_id,
        size_id,
        date_from,
        date_to,
    )


@router.get("/sales.xlsx")
def sales(
    style_code: str | None = None,
    category_id: int | None = None,
    supplier_id: int | None = None,
    size_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    db: Session = Depends(get_db),
):
    return details(
        db, "sale", style_code, category_id, supplier_id, size_id, date_from, date_to
    )


@router.get("/stock.xlsx")
def stock(
    keyword: str | None = None,
    category_id: int | None = None,
    only_negative: bool = False,
    db: Session = Depends(get_db),
):
    wb, ws = workbook(["款号", "品名", "分类", "尺码", "累计入库", "累计出库", "结存"])
    for r in stock_rows(db, keyword, category_id, only_negative):
        append(
            ws,
            [
                r["style_code"],
                r["product"]["name"],
                r["category_name"],
                r["size_text"],
                r["purchased"],
                r["sold"],
                r["stock"],
            ],
        )
    return response(wb, "stock")


@router.get("/documents.xlsx")
def documents(
    kind: str | None = None,
    status: str = "all",
    style_code: str | None = None,
    category_id: int | None = None,
    supplier_id: int | None = None,
    size_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    db: Session = Depends(get_db),
):
    return details(
        db,
        kind,
        style_code,
        category_id,
        supplier_id,
        size_id,
        date_from,
        date_to,
        status,
    )
