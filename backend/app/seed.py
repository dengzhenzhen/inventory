"""初始化数据库：默认账号、字典，以及可选的演示数据。"""
from . import models
from .config import DEFAULT_PASSWORD, DEFAULT_USERNAME
from .database import SessionLocal
from .security import hash_password


def init_db() -> None:
    db = SessionLocal()
    try:
        if not db.query(models.User).first():
            db.add(models.User(username=DEFAULT_USERNAME, password_hash=hash_password(DEFAULT_PASSWORD)))
        if not db.query(models.Category).first():
            for i, n in enumerate(["上衣", "裤装", "裙装", "外套", "配饰"]):
                db.add(models.Category(name=n, sort_order=i))
        if not db.query(models.Size).first():
            for i, n in enumerate(["S", "M", "L", "XL", "均码"]):
                db.add(models.Size(name=n, sort_order=i))
        if not db.query(models.Supplier).first():
            for n in ["杭州优品服饰", "广州锦程制衣", "义乌恒达针织"]:
                db.add(models.Supplier(name=n))
        db.commit()
        _seed_demo(db)
    finally:
        db.close()


def _seed_demo(db) -> None:
    if db.query(models.Product).first():
        return
    from .crud import get_or_create_product, get_or_create_size

    demo_products = [
        ("HT2024-001", "基础圆领T恤", "上衣", "杭州优品服饰", 129),
        ("HT2024-002", "休闲直筒牛仔裤", "裤装", "广州锦程制衣", 259),
        ("HT2024-003", "碎花雪纺连衣裙", "裙装", "杭州优品服饰", 329),
        ("HT2024-004", "宽松针织开衫", "外套", "义乌恒达针织", 299),
        ("KD-8821", "高腰阔腿裤", "裤装", "广州锦程制衣", 239),
        ("KD-8822", "复古格纹衬衫", "上衣", "义乌恒达针织", 189),
        ("KD-8823", "百褶半身裙", "裙装", "杭州优品服饰", 219),
    ]
    for sc, name, cat, sup, price in demo_products:
        p, _ = get_or_create_product(db, sc, cat, sup)
        p.name = name
        p.retail_price = price

    purchases = [
        ("HT2024-001", "S", 10, 45, "2026-10-02", "秋季首单"),
        ("HT2024-001", "M", 15, 45, "2026-10-02", ""),
        ("HT2024-002", "L", 8, 88, "2026-10-05", ""),
        ("HT2024-003", "M", 12, 110, "2026-10-08", "爆款补货"),
        ("HT2024-004", "均码", 6, 120, "2026-10-10", ""),
        ("KD-8821", "L", 9, 95, "2026-10-12", ""),
        ("KD-8822", "M", 14, 70, "2026-10-13", ""),
        ("KD-8823", "S", 7, 82, "2026-10-15", ""),
    ]
    for sc, size, qty, cost, d, remark in purchases:
        product = db.query(models.Product).filter_by(style_code=sc).first()
        sz = get_or_create_size(db, size)
        db.add(models.Purchase(product_id=product.id, style_code=sc, size_id=sz.id, size_text=sz.name,
                               quantity=qty, cost_price=cost, purchase_date=d,
                               supplier_id=product.supplier_id, remark=remark))

    sales = [
        ("HT2024-001", "M", 3, 129, "2026-10-06", "老顾客"),
        ("HT2024-002", "L", 2, 259, "2026-10-09", ""),
        ("HT2024-003", "M", 4, 329, "2026-10-11", "双十一预热"),
        ("KD-8821", "L", 1, 239, "2026-10-13", ""),
        ("KD-8822", "M", 5, 189, "2026-10-14", ""),
        ("HT2024-004", "均码", 2, 299, "2026-10-16", ""),
    ]
    for sc, size, qty, price, d, remark in sales:
        product = db.query(models.Product).filter_by(style_code=sc).first()
        sz = get_or_create_size(db, size)
        db.add(models.Sale(product_id=product.id, style_code=sc, size_id=sz.id, size_text=sz.name,
                           quantity=qty, unit_price=price, sale_date=d, remark=remark))
    db.commit()
