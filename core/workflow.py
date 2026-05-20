"""Full workflow orchestration."""

from __future__ import annotations

import logging
from pathlib import Path

from crypto.file_utils import ensure_output_dir
from crypto.key_utils import save_key_hex
from crypto.sm2_kex_or_wrap import generate_sm2_keypair
from crypto.sm9_signature import generate_master_key
from core.protocol import DEFAULT_SENDER_ID
from core.receiver import receive
from core.sender import send

log = logging.getLogger(__name__)


def run_full_workflow(
    plaintext_path: str | Path,
    cipher: str = "sm4",
    mode: str = "cbc",
    sender_id: str = DEFAULT_SENDER_ID,
    output_dir: str | Path | None = None,
) -> dict:
    out = ensure_output_dir(output_dir)

    log.info("=== initialize SM9 master key ===")
    sm9_master, _ = generate_master_key()
    log.info("=== generate SM2 receiver key pair ===")
    receiver_pri, receiver_pub = generate_sm2_keypair()
    save_key_hex(out / "receiver_pri.txt", receiver_pri)
    save_key_hex(out / "receiver_pub.txt", receiver_pub)

    log.info("=== sender ===")
    send_result = send(
        plaintext_path=plaintext_path,
        receiver_pub=receiver_pub,
        sm9_master_key=sm9_master,
        sender_id=sender_id,
        cipher=cipher,
        mode=mode,
        output_dir=out,
    )

    log.info("=== receiver ===")
    recv_result = receive(
        receiver_pri=receiver_pri,
        receiver_pub=receiver_pub,
        sm9_master_pub=sm9_master,
        output_dir=out,
    )

    return {"send": send_result, "receive": recv_result, "_sm9_master": sm9_master}
