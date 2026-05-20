"""SM3 完整性与 transcript 工具。"""

from __future__ import annotations

import hashlib
import hmac
import struct

from crypto.sm3_adapter import sm3_hash


def hmac_sm3(key: bytes, data: bytes) -> bytes:
    mac = hmac.new(key, data, digestmod=_sm3_digestmod())
    return mac.digest()


def verify_hmac_sm3(key: bytes, data: bytes, expected: bytes) -> bool:
    actual = hmac_sm3(key, data)
    return hmac.compare_digest(actual, expected)


def sm3_digest(data: bytes) -> bytes:
    return bytes.fromhex(sm3_hash(data))


def verify_sm3_digest(data: bytes, expected: bytes) -> bool:
    return hmac.compare_digest(sm3_digest(data), expected)


def build_integrity_object(*parts: bytes) -> bytes:
    result = b""
    for p in parts:
        result += struct.pack(">I", len(p)) + p
    return result


def build_transcript(header: bytes, wrapped_secret: bytes, nonce_or_iv: bytes, ciphertext: bytes, auth_tag: bytes) -> bytes:
    return build_integrity_object(header, wrapped_secret, nonce_or_iv, ciphertext, auth_tag)


def _sm3_digestmod():
    class _Factory:
        digest_size = 32
        block_size = 64

        def __init__(self, data: bytes = b""):
            self._buf = data

        def update(self, data: bytes) -> None:
            self._buf += data

        def digest(self) -> bytes:
            return bytes.fromhex(sm3_hash(self._buf))

        def hexdigest(self) -> str:
            return sm3_hash(self._buf)

        def copy(self) -> "_Factory":
            return _Factory(self._buf)

    return _Factory
