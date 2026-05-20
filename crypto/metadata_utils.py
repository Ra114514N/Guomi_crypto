"""协议报文工具。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def build_header(
    version: str,
    suite_id: str,
    cipher: str,
    mode: str | None,
    kex_mode: str,
    sender_id: str,
    receiver_id: str,
    session_id: str,
    timestamp: str,
    seq: int,
    integrity_algo: str = "hmac-sm3",
) -> dict:
    return {
        "version": version,
        "suite_id": suite_id,
        "cipher": cipher,
        "mode": mode,
        "kex_mode": kex_mode,
        "sender_id": sender_id,
        "receiver_id": receiver_id,
        "session_id": session_id,
        "timestamp": timestamp,
        "seq": seq,
        "integrity_algo": integrity_algo,
    }


def header_to_bytes(header: dict) -> bytes:
    return json.dumps(header, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def build_envelope(
    header: dict,
    wrapped_secret: bytes,
    nonce_or_iv: bytes,
    ciphertext: bytes,
    auth_tag: bytes,
    signature: bytes,
    algo_meta: dict[str, Any],
) -> dict:
    return {
        "header": header,
        "algo_meta": algo_meta,
        "wrapped_secret_b64": _b64(wrapped_secret),
        "nonce_or_iv_b64": _b64(nonce_or_iv),
        "ciphertext_b64": _b64(ciphertext),
        "auth_tag_b64": _b64(auth_tag),
        "signature_b64": _b64(signature),
    }


def save_meta(path: Path | str, meta: dict) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def load_meta(path: Path | str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save_envelope(path: Path | str, envelope: dict) -> None:
    save_meta(path, envelope)


def load_envelope(path: Path | str) -> dict:
    return load_meta(path)


def _b64(data: bytes) -> str:
    import base64

    return base64.b64encode(data).decode("ascii")


def _unb64(text: str) -> bytes:
    import base64

    return base64.b64decode(text.encode("ascii"))


def decode_envelope(envelope: dict) -> dict:
    result = dict(envelope)
    result["wrapped_secret"] = _unb64(result.pop("wrapped_secret_b64"))
    result["nonce_or_iv"] = _unb64(result.pop("nonce_or_iv_b64"))
    result["ciphertext"] = _unb64(result.pop("ciphertext_b64"))
    result["auth_tag"] = _unb64(result.pop("auth_tag_b64"))
    result["signature"] = _unb64(result.pop("signature_b64"))
    return result
