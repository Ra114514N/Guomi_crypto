"""SM2 会话密钥封装模块。

职责：仅用于会话主密钥的安全传输（密钥封装），不承担业务签名。

实现模式：sm2_wrap
  使用 SM2 公钥加密封装随机会话主密钥（16 字节）。
  接收方用 SM2 私钥解密恢复会话主密钥。

设计说明：
  gmssl 3.2.2 不提供标准 SM2-ECDH 密钥协商接口，
  因此采用"SM2 公钥加密封装"方案作为现实落地方案。
  系统设计意图是 SM2 密钥建立，实际代码为 SM2 封装。
"""

from __future__ import annotations

import os
from base64 import b64decode, b64encode
from typing import Tuple

from crypto.sm2_adapter import SM2Adapter, generate_keypair

KEX_MODE = "sm2_wrap"  # 实际实现模式标识


def generate_sm2_keypair() -> Tuple[str, str]:
    """生成 SM2 密钥对，返回 (私钥hex, 公钥hex含04前缀)。"""
    return generate_keypair()


def wrap_session_key(session_key: bytes, receiver_pub: str) -> bytes:
    """用接收方 SM2 公钥加密封装会话主密钥。

    Args:
        session_key:  16 字节会话主密钥
        receiver_pub: 接收方 SM2 公钥（hex，含04前缀）

    Returns:
        加密封装结果（base64 编码字节）
    """
    if len(session_key) != 16:
        raise ValueError("session_key must be 16 bytes")
    enc = SM2Adapter(pub_key=receiver_pub)
    return enc.encrypt(session_key)


def unwrap_session_key(wrapped: bytes, receiver_pri: str, receiver_pub: str) -> bytes:
    """用接收方 SM2 私钥解封装会话主密钥。

    Args:
        wrapped:      wrap_session_key 的输出
        receiver_pri: 接收方 SM2 私钥（hex）
        receiver_pub: 接收方 SM2 公钥（hex，含04前缀）

    Returns:
        16 字节会话主密钥
    """
    dec = SM2Adapter(pub_key=receiver_pub, pri_key=receiver_pri)
    key = dec.decrypt(wrapped)
    if len(key) != 16:
        raise ValueError(f"Unwrapped key length {len(key)} != 16")
    return key
