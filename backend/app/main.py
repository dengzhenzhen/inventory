from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import models  # noqa: F401  # 注册模型
from .config import CORS_ORIGINS, STATIC_DIR
from .database import Base, engine
from .routers import auth, dicts, exports, products, purchases, sales, stats, stock, upload
from .seed import init_db

app = FastAPI(title="服装店进销存管理系统 API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup() -> None:
    Base.metadata.create_all(bind=engine)
    init_db()


@app.exception_handler(StarletteHTTPException)
async def _http_exception_handler(_request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.status_code, "message": str(exc.detail), "data": None},
    )


@app.exception_handler(RequestValidationError)
async def _validation_exception_handler(_request, exc):
    return JSONResponse(
        status_code=422,
        content={"code": 422, "message": "参数校验失败", "data": exc.errors()},
    )


for _router in (
    auth.router,
    dicts.router,
    products.router,
    upload.router,
    purchases.router,
    sales.router,
    stock.router,
    stats.router,
    exports.router,
):
    app.include_router(_router)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/api/health")
def health():
    return {"code": 0, "message": "ok", "data": {"status": "healthy"}}
