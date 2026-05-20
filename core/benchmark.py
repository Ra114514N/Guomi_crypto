"""Performance benchmark."""

from __future__ import annotations

import csv
import os
import time
from pathlib import Path
from typing import List

from crypto.file_utils import ensure_output_dir, write_text
from crypto.kdf_utils import derive_all
from crypto.sm2_kex_or_wrap import generate_sm2_keypair, unwrap_session_key, wrap_session_key
from crypto.sm3_integrity import build_integrity_object, hmac_sm3, sm3_digest
from crypto.sm4_adapter import sm4_decrypt, sm4_encrypt
from crypto.sm9_signature import generate_master_key, sign as sm9_sign, verify as sm9_verify
from crypto.zuc_adapter import zuc_decrypt, zuc_encrypt


def _ms(fn) -> tuple[float, object]:
    t0 = time.perf_counter()
    result = fn()
    return (time.perf_counter() - t0) * 1000, result


def run_benchmark(data_sizes: List[int] | None = None, output_dir: str | Path | None = None) -> str:
    if data_sizes is None:
        data_sizes = [1024, 64 * 1024, 1024 * 1024]

    out = ensure_output_dir(output_dir)
    sm9_master, _ = generate_master_key()
    sm9_key = sm9_master.extract_key("bench@test.local")
    receiver_pri, receiver_pub = generate_sm2_keypair()
    rows = []

    for size in data_sizes:
        data = os.urandom(size)
        session_secret = os.urandom(16)
        derived = derive_all(session_secret, context=b"benchmark")
        sm4_key = derived["sm4_key"]
        sm4_iv = derived["sm4_iv"]
        zuc_key = derived["zuc_key"]
        zuc_iv = derived["zuc_iv"]
        integ_key = derived["integrity_key"]
        digest_ms, digest = _ms(lambda: sm3_digest(data))
        sign_ms, sig = _ms(lambda: sm9_sign(sm9_key, digest))
        verify_ms, _ = _ms(lambda: sm9_verify(sig, digest, sm9_master, "bench@test.local"))
        wrap_ms, wrapped = _ms(lambda: wrap_session_key(session_secret, receiver_pub))
        unwrap_ms, _ = _ms(lambda: unwrap_session_key(wrapped, receiver_pri, receiver_pub))

        for label, enc_fn, dec_fn in _cases(sm4_key, sm4_iv, zuc_key, zuc_iv, data):
            enc_ms, enc_result = _ms(enc_fn)
            ct = enc_result[0] if isinstance(enc_result, tuple) else enc_result
            tag = enc_result[1] if isinstance(enc_result, tuple) else None
            hmac_ms, auth_tag = _ms(lambda: hmac_sm3(integ_key, build_integrity_object(b"hdr", wrapped, sm4_iv, ct)))
            dec_ms, _ = _ms(lambda: dec_fn(ct, tag))
            rows.append({
                "size": _fmt(size),
                "suite": label,
                "encrypt_ms": f"{enc_ms:.2f}",
                "decrypt_ms": f"{dec_ms:.2f}",
                "sm3_ms": f"{digest_ms:.2f}",
                "hmac_sm3_ms": f"{hmac_ms:.2f}",
                "sm9_sign_ms": f"{sign_ms:.2f}",
                "sm9_verify_ms": f"{verify_ms:.2f}",
                "sm2_wrap_ms": f"{wrap_ms:.2f}",
                "sm2_unwrap_ms": f"{unwrap_ms:.2f}",
                "ciphertext_len": len(ct),
                "envelope_overhead": len(wrapped) + len(sig) + len(auth_tag),
            })

    md = _to_md(rows)
    write_text(out / "benchmark.md", md)
    _save_csv(out / "benchmark.csv", rows)
    return md


def _cases(sm4_key, sm4_iv, zuc_key, zuc_iv, data):
    iv16 = sm4_iv
    iv12 = sm4_iv[:12]

    return [
        (
            "SM4-CBC",
            lambda: sm4_encrypt(sm4_key, data, mode="cbc", iv=iv16),
            lambda ct, tag: sm4_decrypt(sm4_key, ct, mode="cbc", iv=iv16),
        ),
        (
            "SM4-CTR",
            lambda: sm4_encrypt(sm4_key, data, mode="ctr", iv=iv16),
            lambda ct, tag: sm4_decrypt(sm4_key, ct, mode="ctr", iv=iv16),
        ),
        (
            "SM4-GCM",
            lambda: sm4_encrypt(sm4_key, data, mode="gcm", iv=iv12),
            lambda ct, tag: sm4_decrypt(sm4_key, ct, mode="gcm", iv=iv12, tag=tag),
        ),
        (
            "ZUC-128",
            lambda: (zuc_encrypt(zuc_key, zuc_iv, data), None),
            lambda ct, tag: zuc_decrypt(zuc_key, zuc_iv, ct),
        ),
    ]


def _fmt(n: int) -> str:
    if n >= 1024 * 1024:
        return f"{n // (1024 * 1024)}MB"
    if n >= 1024:
        return f"{n // 1024}KB"
    return f"{n}B"


def _to_md(rows):
    if not rows:
        return ""
    headers = list(rows[0].keys())
    lines = ["|" + "|".join(headers) + "|", "|" + "|".join(["---"] * len(headers)) + "|"]
    for row in rows:
        lines.append("|" + "|".join(str(row[h]) for h in headers) + "|")
    return "\n".join(lines) + "\n"


def _save_csv(path: Path, rows):
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
