"""Receiver: verify one envelope and recover plaintext."""

from __future__ import annotations

import logging
from pathlib import Path

from crypto.file_utils import ensure_output_dir, write_text
from crypto.kdf_utils import derive_all
from crypto.metadata_utils import decode_envelope, header_to_bytes, load_envelope
from crypto.sm2_kex_or_wrap import unwrap_session_key
from crypto.sm3_integrity import build_integrity_object, build_transcript, sm3_digest, verify_hmac_sm3
from crypto.sm4_adapter import sm4_decrypt
from crypto.zuc_adapter import zuc_decrypt
from crypto.sm9_signature import verify as sm9_verify

log = logging.getLogger(__name__)


def _context_bytes(session_id: str, sender_id: str, receiver_id: str, suite_id: str) -> bytes:
    return f"{session_id}|{sender_id}|{receiver_id}|{suite_id}".encode("utf-8")


def receive(
    receiver_pri: str,
    receiver_pub: str,
    sm9_master_pub: object,
    output_dir: str | Path | None = None,
) -> dict:
    out = ensure_output_dir(output_dir)
    envelope = decode_envelope(load_envelope(out / "message.json"))
    header = envelope["header"]
    cipher = header["cipher"]
    mode = header.get("mode") or "cbc"
    sender_id = header["sender_id"]
    receiver_id = header["receiver_id"]
    suite_id = header["suite_id"]

    log.info("[receiver] loaded envelope, algorithm: %s", envelope["algo_meta"]["algo"])

    wrapped_secret = envelope["wrapped_secret"]
    nonce_or_iv = envelope["nonce_or_iv"]
    ct = envelope["ciphertext"]
    auth_tag = envelope["auth_tag"]
    signature = envelope["signature"]
    header_bytes = header_to_bytes(header)

    session_secret = unwrap_session_key(wrapped_secret, receiver_pri, receiver_pub)
    derived = derive_all(session_secret, context=_context_bytes(header["session_id"], sender_id, receiver_id, suite_id))
    sm4_key = derived["sm4_key"]
    zuc_key = derived["zuc_key"]
    integ_key = derived["integrity_key"]

    transcript = build_transcript(header_bytes, wrapped_secret, nonce_or_iv, ct, auth_tag)
    sig_ok = sm9_verify(signature, transcript, sm9_master_pub, sender_id)

    if cipher == "sm4" and mode == "gcm":
        integrity_ok = sig_ok
    elif cipher == "sm4":
        integrity_ok = verify_hmac_sm3(
            integ_key,
            build_integrity_object(header_bytes, wrapped_secret, nonce_or_iv, ct),
            auth_tag,
        )
    elif cipher == "zuc":
        integrity_ok = verify_hmac_sm3(
            integ_key,
            build_integrity_object(header_bytes, wrapped_secret, nonce_or_iv, ct),
            auth_tag,
        )
    else:
        raise ValueError(f"Unknown cipher: {cipher}")

    plaintext = b""
    digest_ok = False
    if integrity_ok and sig_ok:
        try:
            if cipher == "sm4":
                plaintext = sm4_decrypt(sm4_key, ct, mode=mode, iv=nonce_or_iv, tag=auth_tag if mode == "gcm" else None)
            else:
                plaintext = zuc_decrypt(zuc_key, nonce_or_iv, ct)
            digest_ok = sm3_digest(plaintext).hex() == envelope["algo_meta"]["plain_digest_hex"]
            write_text(out / "recovered.txt", plaintext.decode("utf-8", errors="replace"))
        except Exception:
            integrity_ok = False

    result = {
        "algo_label": envelope["algo_meta"]["algo"],
        "sender_id": sender_id,
        "receiver_id": receiver_id,
        "plaintext_len": len(plaintext),
        "integrity_ok": integrity_ok,
        "signature_ok": sig_ok,
        "digest_ok": digest_ok,
        "success": integrity_ok and sig_ok and digest_ok,
        "output_dir": str(out),
    }

    if result["success"]:
        log.info("[receiver] all checks passed")
    else:
        log.warning(
            "[receiver] verification failed: integrity=%s sig=%s digest=%s",
            integrity_ok, sig_ok, digest_ok,
        )
    return result
