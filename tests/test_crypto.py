from __future__ import annotations

import os
import pickle
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

gmssl = pytest.importorskip("gmssl", reason="gmssl package is required for crypto adapter tests")

from core.receiver import receive
from core.workflow import run_full_workflow
from crypto.gmssl_loader import is_available
from crypto.kdf_utils import derive_all
from crypto.key_utils import gen_iv, gen_sm4_key, load_key_hex
from crypto.metadata_utils import load_meta, save_meta
from crypto.sm2_kex_or_wrap import generate_sm2_keypair, unwrap_session_key, wrap_session_key
from crypto.sm3_adapter import sm3_hash
from crypto.sm3_integrity import build_integrity_object, hmac_sm3, verify_hmac_sm3
from crypto.sm4_adapter import sm4_decrypt, sm4_encrypt
from crypto.zuc_adapter import zuc_decrypt, zuc_encrypt

SM9_AVAILABLE = is_available()


class TestSM2Wrap:
    def test_wrap_unwrap(self):
        pri, pub = generate_sm2_keypair()
        key = os.urandom(16)
        wrapped = wrap_session_key(key, pub)
        assert unwrap_session_key(wrapped, pri, pub) == key

    def test_invalid_key_length(self):
        _, pub = generate_sm2_keypair()
        with pytest.raises(ValueError):
            wrap_session_key(b"short", pub)


class TestKDF:
    def test_lengths_and_context_binding(self):
        master = os.urandom(16)
        d1 = derive_all(master, context=b"ctx-a")
        d2 = derive_all(master, context=b"ctx-b")
        assert len(d1["sm4_key"]) == 16
        assert len(d1["sm4_iv"]) == 16
        assert len(d1["zuc_key"]) == 16
        assert len(d1["zuc_iv"]) == 16
        assert len(d1["integrity_key"]) == 32
        assert d1["sm4_key"] != d2["sm4_key"]

    def test_deterministic(self):
        master = os.urandom(16)
        assert derive_all(master, context=b"ctx") == derive_all(master, context=b"ctx")


class TestSM3Integrity:
    def test_hmac_sm3_verify(self):
        key = b"k" * 32
        tag = hmac_sm3(key, b"data")
        assert len(tag) == 32
        assert verify_hmac_sm3(key, b"data", tag)
        assert not verify_hmac_sm3(key, b"tampered", tag)

    def test_sm3_known_vector(self):
        assert sm3_hash(b"abc") == "66c7f0f462eeedd9d1f2d46bdc10e4e24167c4875cf2f7a2297da02b8f4ba8e0"

    def test_integrity_object_length_prefixes(self):
        obj = build_integrity_object(b"hdr", b"iv", b"ct")
        assert obj.startswith(b"\x00\x00\x00\x03hdr")


class TestSM4:
    def test_cbc_ctr_gcm_roundtrip(self):
        key = gen_sm4_key()
        data = b"SM4 plaintext"
        for mode, iv_len in [("cbc", 16), ("ctr", 16), ("gcm", 12)]:
            iv = gen_iv(iv_len)
            ct, tag = sm4_encrypt(key, data, mode=mode, iv=iv)
            assert sm4_decrypt(key, ct, mode=mode, iv=iv, tag=tag) == data

    def test_gcm_tamper_fails(self):
        key = gen_sm4_key()
        iv = gen_iv(12)
        ct, tag = sm4_encrypt(key, b"hello", mode="gcm", iv=iv)
        bad = bytes([ct[0] ^ 1]) + ct[1:]
        with pytest.raises(ValueError):
            sm4_decrypt(key, bad, mode="gcm", iv=iv, tag=tag)


class TestZUC:
    def test_roundtrip(self):
        key = gen_sm4_key()
        iv = gen_iv(16)
        data = os.urandom(4096)
        assert zuc_decrypt(key, iv, zuc_encrypt(key, iv, data)) == data


@pytest.mark.skipif(not SM9_AVAILABLE, reason="GmSSL native library not available")
class TestEnvelopeWorkflow:
    @pytest.fixture
    def plain_file(self, tmp_path):
        p = tmp_path / "plain.txt"
        p.write_text("full workflow plaintext\nHello SM9 world!", encoding="utf-8")
        return p

    @pytest.mark.parametrize("cipher,mode", [
        ("sm4", "cbc"),
        ("sm4", "ctr"),
        ("sm4", "gcm"),
        ("zuc", "cbc"),
    ])
    def test_workflow(self, plain_file, tmp_path, cipher, mode):
        out = tmp_path / f"out_{cipher}_{mode}"
        result = run_full_workflow(plain_file, cipher=cipher, mode=mode, output_dir=out)
        recv = result["receive"]
        assert (out / "message.json").exists()
        assert not (out / "ciphertext.bin").exists()
        assert not (out / "plain_digest.bin").exists()
        assert recv["integrity_ok"]
        assert recv["signature_ok"]
        assert recv["digest_ok"]
        assert recv["success"]
        assert (out / "recovered.txt").exists()

    @pytest.mark.parametrize("cipher,mode", [
        ("sm4", "cbc"),
        ("sm4", "gcm"),
        ("zuc", "cbc"),
    ])
    def test_binary_roundtrip(self, tmp_path, cipher, mode):
        # 含 0xFF/0x00 等非 UTF-8 字节的二进制明文必须逐字节无损恢复
        payload = b"\x89PNG\r\n\x1a\n" + os.urandom(256) + b"\xff\x00\xfe\x01"
        src = tmp_path / "image.png"
        src.write_bytes(payload)
        out = tmp_path / f"out_bin_{cipher}_{mode}"
        result = run_full_workflow(src, cipher=cipher, mode=mode, output_dir=out)
        recv = result["receive"]
        assert recv["success"]
        recovered = out / "recovered.png"
        assert recovered.exists()
        assert recovered.read_bytes() == payload
        assert recv["decrypt_ok"]
        assert recv["type_match"]
        assert "PNG" in recv["detected_type"]
        assert recv["recovered_path"] == str(recovered)

    def test_tampered_filename_fails(self, plain_file, tmp_path):
        out = tmp_path / "tamper_filename"
        result = run_full_workflow(plain_file, cipher="sm4", mode="cbc", output_dir=out)
        envelope = load_meta(out / "message.json")
        envelope["header"]["filename"] = "evil.exe"
        save_meta(out / "message.json", envelope)
        recv = _receive_with_master(out, result)
        assert not recv["success"]

    def test_tampered_ciphertext_fails(self, plain_file, tmp_path):
        out = tmp_path / "tamper_ciphertext"
        result = run_full_workflow(plain_file, cipher="sm4", mode="cbc", output_dir=out)
        _tamper_b64_field(out / "message.json", "ciphertext_b64")
        recv = _receive_with_master(out, result)
        assert not recv["success"]

    def test_tampered_nonce_fails(self, plain_file, tmp_path):
        out = tmp_path / "tamper_nonce"
        result = run_full_workflow(plain_file, cipher="sm4", mode="cbc", output_dir=out)
        _tamper_b64_field(out / "message.json", "nonce_or_iv_b64")
        recv = _receive_with_master(out, result)
        assert not recv["success"]

    def test_tampered_receiver_id_fails(self, plain_file, tmp_path):
        out = tmp_path / "tamper_receiver"
        result = run_full_workflow(plain_file, cipher="sm4", mode="cbc", output_dir=out)
        envelope = load_meta(out / "message.json")
        envelope["header"]["receiver_id"] = "mallory@example.test"
        save_meta(out / "message.json", envelope)
        recv = _receive_with_master(out, result)
        assert not recv["success"]


def _tamper_b64_field(path: Path, field: str) -> None:
    envelope = load_meta(path)
    raw = bytearray(envelope[field].encode("ascii"))
    raw[-2] = ord("A") if raw[-2] != ord("A") else ord("B")
    envelope[field] = raw.decode("ascii")
    save_meta(path, envelope)


def _receive_with_master(out: Path, result: dict) -> dict:
    receiver_pri = load_key_hex(out / "receiver_pri.txt")
    receiver_pub = load_key_hex(out / "receiver_pub.txt")
    return receive(receiver_pri, receiver_pub, result["_sm9_master"], output_dir=out)
