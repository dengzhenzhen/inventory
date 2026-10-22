"""请求校验模型（Pydantic v2）。响应统一用 dict（见 utils.ok）。"""

from typing import List, Optional

from datetime import date
import math
from pydantic import (
    BaseModel as PydanticBaseModel,
    Field,
    field_validator,
    model_validator,
)


class BaseModel(PydanticBaseModel):
    @field_validator("*", mode="before")
    @classmethod
    def normalize(cls, value, info):
        if isinstance(value, str) and "password" not in info.field_name:
            value = value.strip()
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError("数值必须有限")
        return value

    @model_validator(mode="after")
    def validate_fields(self):
        limits = {
            "style_code": 64,
            "size": 20,
            "name": 120,
            "remark": 2000,
            "category_name": 50,
            "category": 50,
            "supplier_name": 100,
            "supplier": 100,
            "main_image": 255,
            "contact": 50,
            "phone": 30,
            "username": 50,
        }
        for key, limit in limits.items():
            value = getattr(self, key, None)
            if value is not None and len(value) > limit:
                raise ValueError(f"{key} 最多 {limit} 字符")
        for key in ("style_code",):
            if (
                key in self.model_fields_set
                and getattr(self, key, None) is not None
                and not getattr(self, key)
            ):
                raise ValueError(f"{key} 不能为空")
        for key in ("retail_price", "style_code"):
            if key in self.model_fields_set and getattr(self, key, None) is None:
                raise ValueError(f"{key} 不能为 null")
        for key in ("purchase_date", "sale_date", "date"):
            value = getattr(self, key, None)
            if value is not None:
                date.fromisoformat(value)
                if len(value) != 10:
                    raise ValueError("日期必须为 YYYY-MM-DD")
        return self


class LoginIn(BaseModel):
    username: str
    password: str


class PasswordChangeIn(BaseModel):
    old_password: str
    new_password: str = Field(min_length=8, max_length=128)


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
    retail_price: float = Field(default=0, ge=0, allow_inf_nan=False)
    main_image: Optional[str] = None
    remark: Optional[str] = None


class ProductUpdate(BaseModel):
    style_code: Optional[str] = None
    name: Optional[str] = None
    category_id: Optional[int] = None
    category_name: Optional[str] = None
    supplier_id: Optional[int] = None
    supplier_name: Optional[str] = None
    retail_price: Optional[float] = Field(default=None, ge=0, allow_inf_nan=False)
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
    items: List[PurchaseIn] = Field(min_length=1, max_length=500)


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
