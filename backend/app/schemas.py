"""请求校验模型（Pydantic v2）。响应统一用 dict（见 utils.ok）。"""
from typing import List, Optional

from pydantic import BaseModel, Field


class LoginIn(BaseModel):
    username: str
    password: str


class PasswordChangeIn(BaseModel):
    old_password: str
    new_password: str = Field(min_length=4)


class DictIn(BaseModel):
    name: str = Field(min_length=1)
    contact: Optional[str] = None
    phone: Optional[str] = None
    remark: Optional[str] = None


class ProductIn(BaseModel):
    style_code: str = Field(min_length=1)
    name: Optional[str] = None
    category_id: Optional[int] = None
    category_name: Optional[str] = None
    supplier_id: Optional[int] = None
    supplier_name: Optional[str] = None
    retail_price: float = 0
    main_image: Optional[str] = None
    remark: Optional[str] = None


class ProductUpdate(BaseModel):
    style_code: Optional[str] = None
    name: Optional[str] = None
    category_id: Optional[int] = None
    category_name: Optional[str] = None
    supplier_id: Optional[int] = None
    supplier_name: Optional[str] = None
    retail_price: Optional[float] = None
    main_image: Optional[str] = None
    remark: Optional[str] = None


class PurchaseIn(BaseModel):
    style_code: str = Field(min_length=1)
    size: Optional[str] = None
    quantity: int = Field(gt=0)
    cost_price: float = Field(ge=0)
    purchase_date: Optional[str] = None
    category: Optional[str] = None
    supplier: Optional[str] = None
    main_image: Optional[str] = None
    remark: Optional[str] = None


class PurchaseBatchIn(BaseModel):
    items: List[PurchaseIn]


class PurchaseUpdate(BaseModel):
    size: Optional[str] = None
    quantity: Optional[int] = Field(default=None, gt=0)
    cost_price: Optional[float] = Field(default=None, ge=0)
    purchase_date: Optional[str] = None
    supplier: Optional[str] = None
    remark: Optional[str] = None


class SaleIn(BaseModel):
    style_code: str = Field(min_length=1)
    size: str = Field(min_length=1)
    quantity: int = Field(gt=0)
    unit_price: float = Field(ge=0)
    sale_date: Optional[str] = None
    remark: Optional[str] = None


class SaleUpdate(BaseModel):
    size: Optional[str] = None
    quantity: Optional[int] = Field(default=None, gt=0)
    unit_price: Optional[float] = Field(default=None, ge=0)
    sale_date: Optional[str] = None
    remark: Optional[str] = None
