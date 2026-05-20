"""SM3 摘要适配器。"""

from __future__ import annotations

from gmssl import sm3 as _sm3


def sm3_hash(data: bytes) -> str:
    """计算 SM3 摘要，返回 64 位十六进制字符串。"""
    return _sm3.sm3_hash(list(data))
