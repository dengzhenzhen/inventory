import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import __version__
from . import models  # noqa: F401  # 注册模型
from .config import CORS_ORIGINS, STATIC_DIR
from .database import engine
from .paths import default_spa_dist
from .routers import (
    documents,
    backup,
    auth,
    dicts,
    exports,
    products,
    purchases,
    sales,
    stats,
    stock,
    system,
    upload,
)
from .seed import init_db

SPA_DIST = Path(os.getenv("SPA_DIST", str(default_spa_dist())))

from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(_app):
    _startup()
    yield
    engine.dispose()


app = FastAPI(lifespan=lifespan, title="服装店进销存管理系统 API", version=__version__)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _startup() -> None:
    from .backups import apply_pending
    from .upgrades import migrate

    engine.dispose()
    apply_pending()
    migrate()
    init_db()


# Single-worker SQLite application: serialize API requests to protect posting,
# idempotency, backup snapshots and maintenance transitions from concurrent writers.
import asyncio
from sqlalchemy.exc import IntegrityError, OperationalError

_api_lock = asyncio.Lock()


@app.middleware("http")
async def consistency_boundary(request, call_next):
    if not request.url.path.startswith("/api/"):
        return await call_next(request)
    async with _api_lock:
        from .backups import maintenance

        allowed = (
            request.url.path.startswith(("/api/auth/", "/api/backups/"))
            or request.url.path == "/api/health"
        )
        if maintenance() and not allowed:
            return JSONResponse(
                status_code=503,
                content={
                    "code": 503,
                    "message": "系统处于恢复维护模式，请到设置查看状态或重启程序",
                    "data": None,
                },
            )
        return await call_next(request)


@app.exception_handler(IntegrityError)
async def integrity_error(_request, exc):
    return JSONResponse(
        status_code=409,
        content={
            "code": 409,
            "message": "名称重复或数据仍被引用，请刷新后重试",
            "data": None,
        },
    )


@app.exception_handler(OperationalError)
async def database_error(_request, exc):
    import logging

    logging.getLogger(__name__).exception("Database operation failed", exc_info=exc)
    return JSONResponse(
        status_code=503,
        content={"code": 503, "message": "数据库暂不可用，请稍后重试", "data": None},
    )


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
        content={
            "code": 422,
            "message": "参数校验失败",
            "data": [
                {"loc": e.get("loc"), "message": e.get("msg"), "type": e.get("type")}
                for e in exc.errors()
            ],
        },
    )


for _router in (
    documents.router,
    backup.router,
    auth.router,
    dicts.router,
    products.router,
    upload.router,
    purchases.router,
    sales.router,
    stock.router,
    stats.router,
    exports.router,
    system.router,
):
    app.include_router(_router)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/api/health")
def health():
    return {"code": 0, "message": "ok", "data": {"status": "healthy"}}


# ---------------------------------------------------------------------------
# 同源托管 Vue SPA（history 模式）
# 注册顺序：routers -> /static -> /assets -> catch-all，确保 catch-all 永远最后。
# ---------------------------------------------------------------------------
_spa_index = SPA_DIST / "index.html"

if _spa_index.is_file():
    _spa_assets = SPA_DIST / "assets"
    if _spa_assets.is_dir():
        app.mount("/assets", StaticFiles(directory=str(_spa_assets)), name="assets")
    else:
        print(
            f"[WARN] SPA assets directory not found at {_spa_assets}; /assets will not be served."
        )

    @app.get("/{full_path:path}", include_in_schema=False)
    def _spa_fallback(full_path: str):
        # 不遮蔽 API、静态资源与文档路由。
        if (
            full_path.startswith("api/")
            or full_path.startswith("static/")
            or full_path in {"docs", "redoc", "openapi.json"}
        ):
            raise HTTPException(status_code=404, detail="Not Found")

        # 仅允许访问 SPA_DIST 内的真实文件，阻止 ../ 路径穿越。
        candidate = (SPA_DIST / full_path).resolve()
        spa_root = SPA_DIST.resolve()
        if spa_root != candidate and spa_root not in candidate.parents:
            raise HTTPException(status_code=404, detail="Not Found")

        if candidate.is_file():
            return FileResponse(candidate)

        # 未知的非保留路径回退到 index.html（Vue Router history 模式）。
        return FileResponse(_spa_index)

else:
    print(
        f"[WARN] SPA build not found: expected {_spa_index}. "
        "SPA routes are disabled; API remains available."
    )
