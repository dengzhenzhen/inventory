import uuid
from fastapi import APIRouter, Depends, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from ..deps import current_user
from ..database import get_db
from ..config import DATA_DIR
from .. import backups as b
from ..utils import ok, abort
from ..ledger import audit

router = APIRouter(
    prefix="/api/backups", tags=["backups"], dependencies=[Depends(current_user)]
)


class RestoreIn(BaseModel):
    token: str = Field(pattern="^[0-9a-f]{32}$")


@router.get("")
def download(user: str = Depends(current_user), db=Depends(get_db)):
    result = b.create_backup()
    audit(db, user, "backup", {"file": result.name})
    db.commit()
    return FileResponse(result, filename=result.name, media_type="application/zip")


@router.get("/status")
def status():
    return ok(
        {
            "maintenance": b.maintenance(),
            "pending": b.PENDING.exists(),
            "failure": b.FAILURE.read_text(encoding="utf-8")
            if b.FAILURE.exists()
            else None,
        }
    )


@router.post("/validate")
async def validate(file: UploadFile = File(...)):
    token = uuid.uuid4().hex
    folder = DATA_DIR / "restore"
    folder.mkdir(exist_ok=True)
    path = folder / f"{token}.zip"
    size = 0
    try:
        with path.open("wb") as target:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > b.MAX_ARCHIVE:
                    raise ValueError("备份不能超过 256MB")
                target.write(chunk)
        manifest = b.validate_archive(path)
    except Exception as exc:
        path.unlink(missing_ok=True)
        abort(f"备份无效：{exc}", 422)
    finally:
        await file.close()
    return ok({"token": token, "manifest": manifest})


@router.post("/restore")
def restore(payload: RestoreIn, user: str = Depends(current_user), db=Depends(get_db)):
    if b.maintenance():
        abort("已有维护任务，请先完成或取消", 409)
    path = DATA_DIR / "restore" / f"{payload.token}.zip"
    try:
        b.validate_archive(path)
    except Exception as exc:
        abort(f"备份无效：{exc}", 422)
    rollback = b.create_backup()
    audit(
        db, user, "restore_requested", {"archive": path.name, "rollback": rollback.name}
    )
    db.commit()
    b.atomic_json(b.PENDING, {"archive": str(path), "rollback": str(rollback)})
    return ok(
        {"restart_required": True}, "已进入维护模式，请关闭并重新启动程序完成恢复"
    )


@router.post("/cancel")
def cancel(user: str = Depends(current_user), db=Depends(get_db)):
    if b.JOURNAL.exists():
        abort("恢复正在执行，不能取消", 409)
    b.PENDING.unlink(missing_ok=True)
    b.FAILURE.unlink(missing_ok=True)
    audit(db, user, "maintenance_cancel", {})
    db.commit()
    return ok(None)
