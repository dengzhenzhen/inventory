from typing import Optional
from pydantic import Field
from .schemas import BaseModel


class LineIn(BaseModel):
    style_code: str = Field(min_length=1, max_length=64)
    size: str = Field(default="未指定", min_length=1, max_length=20)
    quantity: int = Field(gt=0, le=1_000_000)
    price: float = Field(default=0, ge=0, le=1_000_000_000, allow_inf_nan=False)
    category: Optional[str] = None
    supplier: Optional[str] = None
    main_image: Optional[str] = None
    original_line_id: Optional[int] = None
    stock_version: Optional[int] = None
    counted: Optional[int] = Field(default=None, ge=0, le=1_000_000)
    adjustment_sign: int = Field(default=1, ge=-1, le=1)


class DocumentIn(BaseModel):
    kind: str = Field(
        pattern="^(purchase|sale|purchase_return|sale_return|count|adjustment)$"
    )
    date: str
    remark: str = Field(default="", max_length=2000)
    lines: list[LineIn] = Field(min_length=1, max_length=500)


class ReasonIn(BaseModel):
    reason: str = Field(min_length=1, max_length=2000)


class RecomputeIn(BaseModel):
    fingerprint: str = Field(min_length=64, max_length=64)
