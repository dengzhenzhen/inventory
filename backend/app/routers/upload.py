import os
import uuid
from io import BytesIO

from fastapi import APIRouter, Depends, File, UploadFile
from PIL import Image

from ..config import ALLOWED_IMAGE_EXT, IMAGE_DIR, MAX_UPLOAD_MB
from ..deps import current_user
from ..utils import abort, ok

router = APIRouter(
    prefix="/api/upload", tags=["upload"], dependencies=[Depends(current_user)]
)


@router.post("/image")
async def upload_image(file: UploadFile = File(...)):
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_IMAGE_EXT:
        abort("不支持的图片格式（仅支持 jpg/png/webp/gif）")
    chunks = []
    total = 0
    while chunk := await file.read(1024 * 1024):
        total += len(chunk)
        if total > MAX_UPLOAD_MB * 1024 * 1024:
            await file.close()
            abort(f"图片不能超过 {MAX_UPLOAD_MB}MB")
        chunks.append(chunk)
    await file.close()
    data = b"".join(chunks)
    if len(data) > MAX_UPLOAD_MB * 1024 * 1024:
        abort(f"图片不能超过 {MAX_UPLOAD_MB}MB")
    try:
        Image.open(BytesIO(data)).verify()
        source = Image.open(BytesIO(data))
        if source.width * source.height > 25_000_000:
            abort("图片像素过大")
        source.thumbnail((1200, 1200))
        img = source.convert("RGB")
    except Exception:
        abort("图片文件无效或已损坏")
    img.thumbnail((1200, 1200))
    name = f"{uuid.uuid4().hex}.jpg"
    img.save(IMAGE_DIR / name, "JPEG", quality=85)
    return ok({"path": f"images/{name}"}, "上传成功")
