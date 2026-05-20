"""密钥派生。"""

from __future__ import annotations

import struct

from crypto.sm3_integrity import hmac_sm3

_LABEL_SM4_KEY = b"sm4-key-v2"
_LABEL_SM4_IV = b"sm4-iv-v2"
_LABEL_ZUC_KEY = b"zuc-key-v2"
_LABEL_ZUC_IV = b"zuc-iv-v2"
_LABEL_INTEG = b"integrity-key-v2"


def _hkdf_extract(salt: bytes, ikm: bytes) -> bytes:
    if not salt:
        salt = bytes(32)
    return hmac_sm3(salt, ikm)


def _hkdf_expand(prk: bytes, info: bytes, length: int) -> bytes:
    n = (length + 31) // 32
    okm = b""
    t = b""
    for i in range(1, n + 1):
        t = hmac_sm3(prk, t + info + struct.pack("B", i))
        okm += t
    return okm[:length]


def derive_all(master_key: bytes, context: bytes = b"", salt: bytes = b"") -> dict:
    prk = _hkdf_extract(salt + context, master_key)
    return {
        "sm4_key": _hkdf_expand(prk, _LABEL_SM4_KEY + context, 16),
        "sm4_iv": _hkdf_expand(prk, _LABEL_SM4_IV + context, 16),
        "zuc_key": _hkdf_expand(prk, _LABEL_ZUC_KEY + context, 16),
        "zuc_iv": _hkdf_expand(prk, _LABEL_ZUC_IV + context, 16),
        "integrity_key": _hkdf_expand(prk, _LABEL_INTEG + context, 32),
    }


def derive_sm4(master_key: bytes, context: bytes = b"", salt: bytes = b"") -> tuple[bytes, bytes]:
    d = derive_all(master_key, context=context, salt=salt)
    return d["sm4_key"], d["sm4_iv"]


def derive_zuc(master_key: bytes, context: bytes = b"", salt: bytes = b"") -> tuple[bytes, bytes]:
    d = derive_all(master_key, context=context, salt=salt)
    return d["zuc_key"], d["zuc_iv"]


def derive_integrity(master_key: bytes, context: bytes = b"", salt: bytes = b"") -> bytes:
    return derive_all(master_key, context=context, salt=salt)["integrity_key"]
