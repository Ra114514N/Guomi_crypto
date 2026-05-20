"""SM9 数字签名适配器。

使用 gmssl-python 2.2.2 + GmSSL 3.1.1 动态库实现 SM9 签名与验签。

SM9 是基于身份的密码体制（IBC），签名者无需证书，
其身份 ID（如邮件地址）直接作为公钥标识。

密钥体系：
  - 签名主密钥（Sm9SignMasterKey）：由 KGC（密钥生成中心）持有
  - 签名主公钥：公开，验签方使用
  - 用户签名私钥（Sm9SignKey）：由 KGC 为每个用户 ID 生成
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Tuple

from crypto.gmssl_loader import get_gmssl


# 主密钥 PEM 文件默认密码（课程设计演示用）
_DEFAULT_PASSWD = "sm9demo2024"


def generate_master_key() -> Tuple[object, object]:
    """生成 SM9 签名主密钥对。

    Returns:
        (master_key, master_pub_key) — 同一对象，master_key 含私钥
    """
    gm = get_gmssl()
    master = gm.Sm9SignMasterKey()
    master.generate_master_key()
    return master, master


def extract_sign_key(master_key: object, user_id: str) -> object:
    """从主密钥为指定用户 ID 提取签名私钥。

    Args:
        master_key: Sm9SignMasterKey（含私钥）
        user_id:    用户身份标识，如 "sender@example.com"

    Returns:
        Sm9SignKey（含私钥）
    """
    gm = get_gmssl()
    return master_key.extract_key(user_id)


def sign(sign_key: object, message: bytes) -> bytes:
    """用用户签名私钥对消息签名。

    Args:
        sign_key: Sm9SignKey（含私钥）
        message:  待签名消息字节

    Returns:
        签名字节（约 104 字节）
    """
    gm = get_gmssl()
    ctx = gm.Sm9Signature(gm.DO_SIGN)
    ctx.update(message)
    return ctx.sign(sign_key)


def verify(
    signature: bytes,
    message: bytes,
    master_pub: object,
    signer_id: str,
) -> bool:
    """验证 SM9 签名。

    Args:
        signature:  签名字节
        message:    原始消息字节
        master_pub: Sm9SignMasterKey（含公钥即可）
        signer_id:  签名者身份 ID

    Returns:
        True 表示验签通过
    """
    gm = get_gmssl()
    ctx = gm.Sm9Signature(gm.DO_VERIFY)
    ctx.update(message)
    try:
        return ctx.verify(signature, master_pub, signer_id)
    except Exception:
        return False


def save_master_key(master_key: object, path: Path | str, passwd: str = _DEFAULT_PASSWD) -> None:
    """将主密钥（含私钥）加密保存为 PEM 文件。"""
    master_key.export_encrypted_master_key_info_pem(str(Path(path)), passwd)


def load_master_key(path: Path | str, passwd: str = _DEFAULT_PASSWD) -> object:
    """从 PEM 文件加载主密钥（含私钥）。"""
    gm = get_gmssl()
    master = gm.Sm9SignMasterKey()
    master.import_encrypted_master_key_info_pem(str(Path(path)), passwd.encode())
    return master


def save_master_pub(master_key: object, path: Path | str) -> None:
    """保存主公钥 PEM 文件（不含私钥，供验签方使用）。"""
    master_key.export_public_master_key_pem(str(Path(path)))


def load_master_pub(path: Path | str) -> object:
    """加载主公钥 PEM 文件。"""
    gm = get_gmssl()
    master = gm.Sm9SignMasterKey()
    master.import_public_master_key_pem(str(Path(path)))
    return master


def save_sign_key(sign_key: object, path: Path | str, passwd: str = _DEFAULT_PASSWD) -> None:
    """将用户签名私钥加密保存为 PEM 文件。"""
    sign_key.export_encrypted_private_key_info_pem(str(Path(path)), passwd.encode())


def load_sign_key(path: Path | str, user_id: str, passwd: str = _DEFAULT_PASSWD) -> object:
    """从 PEM 文件加载用户签名私钥。"""
    gm = get_gmssl()
    key = gm.Sm9SignKey(user_id)
    key.import_encrypted_private_key_info_pem(str(Path(path)), passwd.encode())
    return key
