# -*- coding: utf-8 -*-
"""
connectivity.py — 网络连通性自动探测与代理管理
用于三级回退的前置决策：判断走 local/cloud/offline
"""

import os
import time
import socket
from typing import Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class NetStatus:
    online: bool = False
    latency_ms: float = 999.0
    dns_ok: bool = False
    proxy_alive: bool = False
    last_check: float = 0.0


_status_cache: Optional[NetStatus] = None
_check_interval = 60  # 秒


def _test_tcp(host: str, port: int, timeout: float = 3.0) -> Tuple[bool, float]:
    """TCP 连通测试，返回 (成功, 延迟ms)"""
    start = time.time()
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect((host, port))
        s.close()
        return True, (time.time() - start) * 1000
    except Exception:
        return False, 999.0


def _test_dns(host: str = "dns.google", timeout: float = 3.0) -> bool:
    """DNS 解析测试"""
    try:
        socket.setdefaulttimeout(timeout)
        socket.getaddrinfo(host, 443)
        return True
    except Exception:
        return False


def check_connectivity() -> NetStatus:
    """获取当前网络状态（带 60 秒缓存）"""
    global _status_cache
    if _status_cache and time.time() - _status_cache.last_check < _check_interval:
        return _status_cache

    # DNS 测试
    dns_ok = _test_dns()

    # TCP 测试（Google DNS / Cloudflare）
    online = False
    latency = 999.0
    for endpoint in [("8.8.8.8", 53), ("1.1.1.1", 53), ("114.114.114.114", 53)]:
        ok, ms = _test_tcp(*endpoint, timeout=4.0)
        if ok:
            online = True
            latency = ms
            break

    # 代理检测（取环境变量中的代理地址）
    proxy_alive = False
    proxy_url = os.environ.get("HTTP_PROXY") or os.environ.get("http_proxy")
    if proxy_url:
        try:
            host = proxy_url.split("//")[-1].split(":")[0]
            port = int(proxy_url.rsplit(":", 1)[-1].rstrip("/"))
            proxy_alive, _ = _test_tcp(host, port, timeout=2.0)
        except Exception:
            proxy_alive = False

    _status_cache = NetStatus(
        online=online,
        latency_ms=latency,
        dns_ok=dns_ok,
        proxy_alive=proxy_alive,
        last_check=time.time(),
    )
    return _status_cache


def connectivity_summary() -> dict:
    """可读的连通性摘要"""
    s = check_connectivity()
    return {
        "online": s.online,
        "dns": s.dns_ok,
        "latency_ms": round(s.latency_ms, 1),
        "proxy_alive": s.proxy_alive,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(s.last_check)),
    }


# CLI
if __name__ == "__main__":
    import sys
    if "--json" in sys.argv:
        import json
        print(json.dumps(connectivity_summary(), indent=2, ensure_ascii=False))
    else:
        s = check_connectivity()
        status = "ONLINE" if s.online else "OFFLINE"
        print(f"Net: {status} | DNS: {'OK' if s.dns_ok else 'FAIL'} | Latency: {s.latency_ms:.0f}ms | Proxy: {'OK' if s.proxy_alive else 'N/A'}")
