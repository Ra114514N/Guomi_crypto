"""SM4 对称加密适配器，支持 CBC / CTR / GCM 三种模式。

CBC  — 使用 gmssl 原生实现（与原项目兼容）
CTR  — 使用 gmssl ECB 块 + 纯 Python CTR 模式包装
GCM  — 使用 gmssl ECB 块 + 纯 Python GCM 模式包装（GHASH 认证）

接口统一：
    sm4_encrypt(key, plaintext, mode, iv) -> (ciphertext: bytes, tag: bytes | None)
    sm4_decrypt(key, ciphertext, mode, iv, tag) -> plaintext: bytes
"""

from __future__ import annotations

import os
import struct
from typing import Literal, Tuple

from gmssl import sm4 as _gm_sm4

SM4Mode = Literal["cbc", "ctr", "gcm"]

_BLOCK = 16


# ── 内部：gmssl ECB 单块加密 ──────────────────────────────────────────────────

def _ecb_encrypt_block(key: bytes, block: bytes) -> bytes:
    """用 SM4-ECB 加密单个 16 字节块。"""
    alg = _gm_sm4.CryptSM4()
    alg.set_key(key, _gm_sm4.SM4_ENCRYPT)
    return alg.crypt_ecb(block)[:16]


# ── CBC（gmssl 原生）─────────────────────────────────────────────────────────

def _cbc_encrypt(key: bytes, plaintext: bytes, iv: bytes) -> bytes:
    alg = _gm_sm4.CryptSM4()
    alg.set_key(key, _gm_sm4.SM4_ENCRYPT)
    return alg.crypt_cbc(input_data=plaintext, iv=iv)


def _cbc_decrypt(key: bytes, ciphertext: bytes, iv: bytes) -> bytes:
    alg = _gm_sm4.CryptSM4()
    alg.set_key(key, _gm_sm4.SM4_DECRYPT)
    # gmssl 的 crypt_cbc 解密内部已做 pkcs7_unpadding，不可再二次去填充：
    # 二次去填充会把恰好以「疑似填充字节」结尾的二进制明文（如 ...\x01）多剥一截。
    return alg.crypt_cbc(input_data=ciphertext, iv=iv)


# ── CTR（gmssl ECB 块 + Python CTR 包装）────────────────────────────────────

def _ctr_process(key: bytes, data: bytes, nonce: bytes) -> bytes:
    """CTR 模式：nonce 作为初始计数器（大端 128 位）。"""
    counter = int.from_bytes(nonce, "big")
    out = bytearray()
    for i in range(0, len(data), _BLOCK):
        ctr_block = counter.to_bytes(16, "big")
        keystream = _ecb_encrypt_block(key, ctr_block)
        chunk = data[i:i + _BLOCK]
        out.extend(a ^ b for a, b in zip(chunk, keystream))
        counter = (counter + 1) & ((1 << 128) - 1)
    return bytes(out)


# ── GCM（gmssl ECB 块 + GHASH 认证）─────────────────────────────────────────

def _ghash(h: bytes, data: bytes) -> bytes:
    """GHASH 函数，用于 GCM 认证。"""
    R = 0xE1000000000000000000000000000000
    y = 0
    h_int = int.from_bytes(h, "big")

    # 填充到 16 字节倍数
    padded = data + b"\x00" * ((-len(data)) % 16)
    for i in range(0, len(padded), 16):
        block = int.from_bytes(padded[i:i + 16], "big")
        y ^= block
        # GF(2^128) 乘法
        result = 0
        v = h_int
        for bit in range(128):
            if (y >> (127 - bit)) & 1:
                result ^= v
            if v & 1:
                v = (v >> 1) ^ R
            else:
                v >>= 1
        y = result
    return y.to_bytes(16, "big")


def _gcm_encrypt(key: bytes, plaintext: bytes, nonce: bytes) -> Tuple[bytes, bytes]:
    """GCM 加密，返回 (密文, 认证标签)。"""
    # H = E(K, 0^128)
    h = _ecb_encrypt_block(key, b"\x00" * 16)

    # 初始计数器 J0
    if len(nonce) == 12:
        j0 = nonce + b"\x00\x00\x00\x01"
    else:
        j0 = _ghash(h, nonce + b"\x00" * ((-len(nonce)) % 16) +
                    struct.pack(">QQ", 0, len(nonce) * 8))

    # CTR 加密（从 J0+1 开始）
    ctr_start = (int.from_bytes(j0, "big") + 1) & ((1 << 128) - 1)
    ctr_nonce = ctr_start.to_bytes(16, "big")
    ct = _ctr_process(key, plaintext, ctr_nonce)

    # 计算认证标签
    aad = b""  # 本实现不使用 AAD
    ghash_input = (
        aad + b"\x00" * ((-len(aad)) % 16) +
        ct + b"\x00" * ((-len(ct)) % 16) +
        struct.pack(">QQ", len(aad) * 8, len(ct) * 8)
    )
    s = _ghash(h, ghash_input)
    e_j0 = _ecb_encrypt_block(key, j0)
    tag = bytes(a ^ b for a, b in zip(s, e_j0))

    return ct, tag


def _gcm_decrypt(key: bytes, ciphertext: bytes, nonce: bytes, tag: bytes) -> bytes:
    """GCM 解密，验证认证标签后返回明文。"""
    h = _ecb_encrypt_block(key, b"\x00" * 16)

    if len(nonce) == 12:
        j0 = nonce + b"\x00\x00\x00\x01"
    else:
        j0 = _ghash(h, nonce + b"\x00" * ((-len(nonce)) % 16) +
                    struct.pack(">QQ", 0, len(nonce) * 8))

    # 验证标签
    aad = b""
    ghash_input = (
        aad + b"\x00" * ((-len(aad)) % 16) +
        ciphertext + b"\x00" * ((-len(ciphertext)) % 16) +
        struct.pack(">QQ", len(aad) * 8, len(ciphertext) * 8)
    )
    s = _ghash(h, ghash_input)
    e_j0 = _ecb_encrypt_block(key, j0)
    expected_tag = bytes(a ^ b for a, b in zip(s, e_j0))

    if expected_tag != tag:
        raise ValueError("GCM authentication failed: ciphertext has been tampered")

    # CTR 解密
    ctr_start = (int.from_bytes(j0, "big") + 1) & ((1 << 128) - 1)
    ctr_nonce = ctr_start.to_bytes(16, "big")
    return _ctr_process(key, ciphertext, ctr_nonce)


# ── 公共接口 ─────────────────────────────────────────────────────────────────

def sm4_encrypt(
    key: bytes,
    plaintext: bytes,
    mode: SM4Mode = "cbc",
    iv: bytes | None = None,
) -> Tuple[bytes, bytes | None]:
    """SM4 加密。

    Args:
        key:       16 字节密钥
        plaintext: 明文字节
        mode:      'cbc' | 'ctr' | 'gcm'
        iv:        CBC/CTR 用 16 字节 IV；GCM 用 12 字节 nonce；None 则自动生成

    Returns:
        (ciphertext, tag)  — GCM 模式 tag 为 16 字节，其余为 None
    """
    if len(key) != 16:
        raise ValueError("SM4 key must be 16 bytes")

    if mode == "cbc":
        iv = iv or os.urandom(16)
        ct = _cbc_encrypt(key, plaintext, iv)
        return ct, None
    elif mode == "ctr":
        iv = iv or os.urandom(16)
        ct = _ctr_process(key, plaintext, iv)
        return ct, None
    elif mode == "gcm":
        nonce = iv or os.urandom(12)
        ct, tag = _gcm_encrypt(key, plaintext, nonce)
        return ct, tag
    else:
        raise ValueError(f"Unsupported SM4 mode: {mode}. Choose cbc/ctr/gcm")


def sm4_decrypt(
    key: bytes,
    ciphertext: bytes,
    mode: SM4Mode = "cbc",
    iv: bytes | None = None,
    tag: bytes | None = None,
) -> bytes:
    """SM4 解密。

    Args:
        key:        16 字节密钥
        ciphertext: 密文字节
        mode:       'cbc' | 'ctr' | 'gcm'
        iv:         与加密时相同的 IV/nonce
        tag:        GCM 认证标签（仅 GCM 模式需要）

    Returns:
        明文字节
    """
    if len(key) != 16:
        raise ValueError("SM4 key must be 16 bytes")
    if iv is None:
        raise ValueError("iv/nonce is required for decryption")

    if mode == "cbc":
        return _cbc_decrypt(key, ciphertext, iv)
    elif mode == "ctr":
        return _ctr_process(key, ciphertext, iv)
    elif mode == "gcm":
        if tag is None:
            raise ValueError("GCM mode requires authentication tag")
        return _gcm_decrypt(key, ciphertext, iv, tag)
    else:
        raise ValueError(f"Unsupported SM4 mode: {mode}. Choose cbc/ctr/gcm")
