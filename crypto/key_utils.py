"""密钥工具：生成、读写、格式转换。"""

from __future__ import annotations

import os
from base64 import b64decode, b64encode
from pathlib import Path
from typing import Tuple

from Cryptodome.Random import get_random_bytes

from crypto.sm2_adapter import generate_keypair


def gen_sm2_keypair() -> Tuple[str, str]:
    """生成 SM2 密钥对，返回 (私钥hex, 公钥hex含04前缀)。"""
    return generate_keypair()


def gen_sm4_key() -> bytes:
    """生成 16 字节随机 SM4 密钥。"""
    return get_random_bytes(16)


def gen_iv(size: int = 16) -> bytes:
    """生成随机 IV/nonce。"""
    return os.urandom(size)


# ── 文件读写 ──────────────────────────────────────────────────────────────────

def save_key_hex(path: Path | str, key_hex: str) -> None:
    Path(path).write_text(key_hex, encoding="utf-8")


def load_key_hex(path: Path | str) -> str:
    return Path(path).read_text(encoding="utf-8").strip()


def save_key_b64(path: Path | str, key_bytes: bytes) -> None:
    Path(path).write_text(b64encode(key_bytes).decode(), encoding="utf-8")


def load_key_b64(path: Path | str) -> bytes:
    return b64decode(Path(path).read_text(encoding="utf-8").strip())


def sm4_key_to_bytes(key_str: str) -> bytes:
    """将 base64 或 hex 格式的 SM4 密钥字符串转为 16 字节。"""
    s = key_str.strip()
    try:
        raw = b64decode(s)
        if len(raw) == 16:
            return raw
    except Exception:
        pass
    try:
        raw = bytes.fromhex(s)
        if len(raw) == 16:
            return raw
    except Exception:
        pass
    # 直接当 UTF-8 字节（兼容原项目）
    raw = s.encode("utf-8")
    if len(raw) == 16:
        return raw
    raise ValueError(f"Cannot parse SM4 key from: {s!r}")
