"""Sender: build one envelope message."""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
from uuid import uuid4

from crypto.file_utils import ensure_output_dir
from crypto.kdf_utils import derive_all
from crypto.metadata_utils import build_envelope, build_header, header_to_bytes, save_envelope
from crypto.sm2_kex_or_wrap import KEX_MODE, wrap_session_key
from crypto.sm3_integrity import build_integrity_object, build_transcript, hmac_sm3, sm3_digest
from crypto.sm4_adapter import SM4Mode, sm4_encrypt
from crypto.sm9_signature import sign as sm9_sign
from crypto.zuc_adapter import zuc_encrypt
from core.protocol import (
    CIPHER_SM4,
    CIPHER_ZUC,
    DEFAULT_RECEIVER_ID,
    DEFAULT_SENDER_ID,
    MODE_CBC,
    MODE_CTR,
    MODE_GCM,
    PROTOCOL_VERSION,
    SUITE_SM4_CBC,
    SUITE_SM4_CTR,
    SUITE_SM4_GCM,
    SUITE_ZUC,
)

log = logging.getLogger(__name__)

CipherType = Literal["sm4", "zuc"]


def _suite_id(cipher: str, mode: str | None) -> str:
    if cipher == CIPHER_SM4 and mode == MODE_GCM:
        return SUITE_SM4_GCM
    if cipher == CIPHER_SM4 and mode == MODE_CTR:
        return SUITE_SM4_CTR
    if cipher == CIPHER_SM4 and mode == MODE_CBC:
        return SUITE_SM4_CBC
    if cipher == CIPHER_ZUC:
        return SUITE_ZUC
    raise ValueError(f"Unsupported suite for cipher={cipher}, mode={mode}")


def _context_bytes(session_id: str, sender_id: str, receiver_id: str, suite_id: str) -> bytes:
    return f"{session_id}|{sender_id}|{receiver_id}|{suite_id}".encode("utf-8")


def send(
    plaintext_path: str | Path,
    receiver_pub: str,
    sm9_master_key: object,
    sender_id: str = DEFAULT_SENDER_ID,
    receiver_id: str = DEFAULT_RECEIVER_ID,
    cipher: CipherType = "sm4",
    mode: SM4Mode = "cbc",
    output_dir: str | Path | None = None,
) -> dict:
    out = ensure_output_dir(output_dir)
    plaintext = Path(plaintext_path).read_bytes()
    log.info("[sender] loaded plaintext: %d bytes", len(plaintext))

    session_secret = os.urandom(16)
    session_id = uuid4().hex
    timestamp = datetime.now(timezone.utc).isoformat()
    seq = 1
    suite_id = _suite_id(cipher, mode if cipher == CIPHER_SM4 else None)
    context = _context_bytes(session_id, sender_id, receiver_id, suite_id)

    derived = derive_all(session_secret, context=context)
    sm4_key = derived["sm4_key"]
    sm4_iv = derived["sm4_iv"]
    zuc_key = derived["zuc_key"]
    zuc_iv = derived["zuc_iv"]
    integ_key = derived["integrity_key"]

    if cipher == CIPHER_SM4:
        iv_or_nonce = sm4_iv if mode != MODE_GCM else sm4_iv[:12]
        ct, gcm_tag = sm4_encrypt(sm4_key, plaintext, mode=mode, iv=iv_or_nonce)
        algo_label = f"SM4-{mode.upper()}"
    elif cipher == CIPHER_ZUC:
        iv_or_nonce = zuc_iv
        ct = zuc_encrypt(zuc_key, iv_or_nonce, plaintext)
        gcm_tag = None
        algo_label = "ZUC-128"
    else:
        raise ValueError(f"Unknown cipher: {cipher}")

    wrapped_secret = wrap_session_key(session_secret, receiver_pub)
    header = build_header(
        version=PROTOCOL_VERSION,
        suite_id=suite_id,
        cipher=cipher,
        mode=mode if cipher == CIPHER_SM4 else None,
        kex_mode=KEX_MODE,
        sender_id=sender_id,
        receiver_id=receiver_id,
        session_id=session_id,
        timestamp=timestamp,
        seq=seq,
    )
    header_bytes = header_to_bytes(header)

    if cipher == CIPHER_SM4 and mode == MODE_GCM:
        auth_tag = gcm_tag or b""
    else:
        auth_tag = hmac_sm3(
            integ_key,
            build_integrity_object(header_bytes, wrapped_secret, iv_or_nonce, ct),
        )

    transcript = build_transcript(header_bytes, wrapped_secret, iv_or_nonce, ct, auth_tag)
    signature = sm9_sign(sm9_master_key.extract_key(sender_id), transcript)
    plain_digest = sm3_digest(plaintext)

    envelope = build_envelope(
        header=header,
        wrapped_secret=wrapped_secret,
        nonce_or_iv=iv_or_nonce,
        ciphertext=ct,
        auth_tag=auth_tag,
        signature=bytes.fromhex(signature) if isinstance(signature, str) else signature,
        algo_meta={
            "algo": algo_label,
            "ciphertext_len": len(ct),
            "plain_digest_hex": plain_digest.hex(),
            "has_gcm_tag": gcm_tag is not None,
        },
    )
    save_envelope(out / "message.json", envelope)
    log.info("[sender] wrote envelope: %s", out / "message.json")

    return {
        "algo_label": algo_label,
        "plain_digest": plain_digest.hex(),
        "auth_tag": auth_tag.hex(),
        "signature_hex": envelope["signature_b64"],
        "output_dir": str(out),
        "meta": envelope,
    }
