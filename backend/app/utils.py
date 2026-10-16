"""统一响应封装。"""
from fastapi import HTTPException, status


def ok(data=None, message: str = "ok") -> dict:
    return {"code": 0, "message": message, "data": data}


def abort(message: str, http_status: int = status.HTTP_400_BAD_REQUEST) -> None:
    raise HTTPException(status_code=http_status, detail=message)
