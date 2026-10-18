"""系统信息接口：供前端生成手机端局域网访问二维码。"""
import socket

from fastapi import APIRouter, Depends, Query, Request

from ..config import PORT
from ..deps import current_user
from ..runtime_config import load_runtime_config
from ..utils import ok

router = APIRouter(prefix="/api/system", tags=["system"], dependencies=[Depends(current_user)])

_WILDCARD_HOSTS = {"", "0.0.0.0", "::", "localhost", "127.0.0.1", "::1"}


def _configured_lan_ip() -> str | None:
    """如果配置里显式绑定了具体网卡地址，直接使用。"""
    host = str(load_runtime_config().get("host") or "")
    return host if host not in _WILDCARD_HOSTS else None


def _default_route_ip() -> str | None:
    """通过 UDP connect 让系统选择默认出口网卡（不会真正发包）。"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        ip = sock.getsockname()[0]
        return ip if ip and not ip.startswith("127.") else None
    except OSError:
        return None
    finally:
        sock.close()


def _hostname_ip() -> str | None:
    """离线/无默认路由时，从主机名解析可用的私网 IPv4。"""
    try:
        infos = socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET)
    except OSError:
        return None
    for info in infos:
        ip = info[4][0]
        if ip and not ip.startswith("127.") and not ip.startswith("169.254."):
            return ip
    return None


def _lan_ipv4() -> str | None:
    return _configured_lan_ip() or _default_route_ip() or _hostname_ip()


@router.get("/lan-url")
def lan_url(request: Request, port: int | None = Query(default=None, ge=1, le=65535)):
    """返回当前电脑的局域网访问地址，供手机同一 WiFi 下扫码打开。"""
    effective_port = port or request.url.port or PORT
    ip = _lan_ipv4()
    if not ip:
        return ok(
            {"ip": None, "port": effective_port, "url": None, "reachable": False},
            "无法获取局域网 IP",
        )
    url = f"{request.url.scheme}://{ip}:{effective_port}/"
    return ok({"ip": ip, "port": effective_port, "url": url, "reachable": True})
