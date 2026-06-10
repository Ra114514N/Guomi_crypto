"""QThread workers that bridge business logic to the GUI via Signals."""

import logging
import sys
from pathlib import Path

from PySide6.QtCore import QThread, Signal


class SignalHandler(logging.Handler):
    """Routes logging output to a Qt Signal for real-time log display."""

    def __init__(self, signal: Signal):
        super().__init__()
        self._signal = signal

    def emit(self, record):
        self._signal.emit(self.format(record))


if getattr(sys, 'frozen', False):
    _APP_DIR = Path(sys.executable).parent  # writable dir next to exe
else:
    _APP_DIR = Path(__file__).resolve().parent.parent

ARTIFACTS = _APP_DIR / "artifacts"


class WorkflowWorker(QThread):
    """Runs the full send+receive workflow in a background thread.

    Signals:
        progress(str)   — log text lines (for the log panel)
        step_data(dict) — structured per-step data for the timeline cards:
            {"step": int, "title": str, "state": str, "target": str, "data": {k: v, ...}}
        sender_done()   — emitted after sender steps complete (+ attack tamper)
        finished(dict)  — final result {"send": ..., "receive": ...}
        error(str)      — exception message
    """

    progress = Signal(str)
    step_data = Signal(dict)
    sender_done = Signal()
    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, plaintext_path: str, cipher: str, mode: str,
                 sender_id: str = "sender@sm9.local", attack: str = "none", parent=None):
        super().__init__(parent)
        self._path = plaintext_path
        self._cipher = cipher
        self._mode = mode
        self._sender_id = sender_id
        self._attack = attack or "none"

    def run(self):
        handler = SignalHandler(self.progress)
        handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
        root_logger = logging.getLogger()
        root_logger.addHandler(handler)
        try:
            from crypto.sm9_signature import generate_master_key
            from crypto.sm2_kex_or_wrap import generate_sm2_keypair
            from crypto.key_utils import save_key_hex
            from crypto.file_utils import ensure_output_dir
            from core.sender import send
            from core.receiver import receive

            out = ensure_output_dir(ARTIFACTS)

            # ─── Sender Step 1: SM9 master key ───
            self.step_data.emit({"step": 1, "title": "生成 SM9 主密钥对",
                                 "state": "running", "target": "sender", "data": {}})
            self.progress.emit("▶ 发送端 1/3: 初始化 SM9 主密钥对")
            sm9_master, _ = generate_master_key()
            self.step_data.emit({"step": 1, "title": "生成 SM9 主密钥对",
                                 "state": "success", "target": "sender",
                                 "data": {"算法": "SM9 (GB/T 38635)",
                                          "用途": "身份签名 / 验签"}})
            self.progress.emit("  ✓ SM9 主密钥生成完成")

            # ─── Sender Step 2: SM2 keypair ───
            self.step_data.emit({"step": 2, "title": "生成 SM2 接收方密钥对",
                                 "state": "running", "target": "sender", "data": {}})
            self.progress.emit("▶ 发送端 2/3: 生成 SM2 接收方密钥对")
            receiver_pri, receiver_pub = generate_sm2_keypair()
            save_key_hex(out / "receiver_pri.txt", receiver_pri)
            save_key_hex(out / "receiver_pub.txt", receiver_pub)
            self.step_data.emit({"step": 2, "title": "生成 SM2 接收方密钥对",
                                 "state": "success", "target": "sender",
                                 "data": {"公钥": receiver_pub[:48] + "...",
                                          "存储": str(out)}})
            self.progress.emit(f"  ✓ SM2 公钥: {receiver_pub[:32]}...")

            # ─── Sender Step 3: encrypt + sign + envelope ───
            self.step_data.emit({"step": 3, "title": "加密·签名·封装",
                                 "state": "running", "target": "sender", "data": {}})
            self.progress.emit("▶ 发送端 3/3: 加密、签名、封装")
            send_result = send(
                plaintext_path=self._path,
                receiver_pub=receiver_pub,
                sm9_master_key=sm9_master,
                sender_id=self._sender_id,
                cipher=self._cipher,
                mode=self._mode,
                output_dir=out,
            )
            meta = send_result["meta"]
            self.step_data.emit({"step": 3, "title": "加密·签名·封装",
                                 "state": "success", "target": "sender",
                                 "data": {
                                     "加密算法": send_result["algo_label"],
                                     "文件名": send_result["filename"],
                                     "明文摘要": send_result["plain_digest"][:32] + "...",
                                     "密文长度": f"{meta['algo_meta']['ciphertext_len']} 字节",
                                     "认证标签": meta["auth_tag_b64"][:32] + "...",
                                     "SM9 签名": meta["signature_b64"][:32] + "...",
                                 }})
            self.progress.emit(f"  ✓ 信封已写入: {out}/message.json")

            # Optional attack simulation
            if self._attack != "none":
                self._tamper_envelope(out / "message.json")

            # Signal that sender phase is complete
            self.sender_done.emit()

            # ─── Receiver Step 1: load envelope + SM2 unwrap ───
            self.step_data.emit({"step": 1, "title": "加载信封 · SM2 解封",
                                 "state": "running", "target": "receiver", "data": {}})
            self.progress.emit("▶ 接收端 1/6: 加载信封、SM2 解封会话秘密")
            recv_result = receive(
                receiver_pri=receiver_pri,
                receiver_pub=receiver_pub,
                sm9_master_pub=sm9_master,
                output_dir=out,
            )
            self.step_data.emit({"step": 1, "title": "加载信封 · SM2 解封",
                                 "state": "success", "target": "receiver",
                                 "data": {
                                     "算法": recv_result["algo_label"],
                                     "会话秘密": "已恢复 (16 字节)",
                                 }})
            self.progress.emit("  ✓ SM2 解封完成，会话秘密已恢复")

            sig_ok = recv_result["signature_ok"]
            int_ok = recv_result["integrity_ok"]
            dig_ok = recv_result["digest_ok"]

            # ─── Receiver Step 2: SM9 signature verification ───
            self.step_data.emit({"step": 2, "title": "SM9 签名验证",
                                 "state": "running", "target": "receiver", "data": {}})
            self.progress.emit("▶ 接收端 2/6: SM9 签名验证")
            self.step_data.emit({"step": 2, "title": "SM9 签名验证",
                                 "state": "success" if sig_ok else "error",
                                 "target": "receiver",
                                 "data": {
                                     "SM9 签名验证": "✓ 通过 — 来源可信" if sig_ok
                                                    else "✗ 失败 — 数据可能被篡改",
                                 }})
            self.progress.emit(f"  {'✓' if sig_ok else '✗'} SM9 签名: {'通过' if sig_ok else '失败'}")

            # ─── Receiver Step 3: Integrity verification ───
            is_gcm = (self._cipher == "sm4" and self._mode == "gcm")
            integrity_title = "GCM 认证标签验证" if is_gcm else "HMAC 完整性验证"
            self.step_data.emit({"step": 3, "title": integrity_title,
                                 "state": "running", "target": "receiver", "data": {}})
            self.progress.emit(f"▶ 接收端 3/6: {integrity_title}")

            if is_gcm:
                step3_data = {
                    "GCM 认证": "✓ 通过" if int_ok else "✗ 失败",
                }
            else:
                step3_data = {
                    "_compare": True,
                    "_compare_title": "HMAC-SM3 对比",
                    "_claimed_label": "信封声称值",
                    "_claimed_value": recv_result["claimed_hmac"],
                    "_computed_label": "独立计算值",
                    "_computed_value": recv_result["computed_hmac"],
                    "_is_match": int_ok,
                }

            self.step_data.emit({"step": 3, "title": integrity_title,
                                 "state": "success" if int_ok else "error",
                                 "target": "receiver",
                                 "data": step3_data})
            self.progress.emit(f"  {'✓' if int_ok else '✗'} 完整性: {'通过' if int_ok else '失败'}")

            # ─── Receiver Step 4: SM3 digest comparison ───
            self.step_data.emit({"step": 4, "title": "SM3 摘要比对",
                                 "state": "running", "target": "receiver", "data": {}})
            self.progress.emit("▶ 接收端 4/6: SM3 明文摘要比对")
            self.step_data.emit({"step": 4, "title": "SM3 摘要比对",
                                 "state": "success" if dig_ok else "error",
                                 "target": "receiver",
                                 "data": {
                                     "_compare": True,
                                     "_compare_title": "SM3 明文摘要对比",
                                     "_claimed_label": "信封声称值",
                                     "_claimed_value": recv_result["claimed_digest"],
                                     "_computed_label": "解密后计算",
                                     "_computed_value": recv_result["computed_digest"] or "（解密失败，无法计算）",
                                     "_is_match": dig_ok,
                                 }})
            self.progress.emit(f"  {'✓' if dig_ok else '✗'} 摘要比对: {'通过' if dig_ok else '失败'}")

            # ─── Receiver Step 5: File type identification ───
            type_ok = recv_result["type_match"]
            self.step_data.emit({"step": 5, "title": "文件类型识别",
                                 "state": "running", "target": "receiver", "data": {}})
            self.progress.emit("▶ 接收端 5/6: 文件类型识别")
            if recv_result["decrypt_ok"]:
                step5_data = {
                    "_compare": True,
                    "_compare_title": "文件类型对比",
                    "_claimed_label": "信封声称类型",
                    "_claimed_value": recv_result["claimed_type"],
                    "_computed_label": "内容检测类型",
                    "_computed_value": recv_result["detected_type"],
                    "_is_match": type_ok,
                }
                step5_state = "success" if type_ok else "error"
                self.progress.emit(
                    f"  {'✓' if type_ok else '✗'} 文件类型: "
                    f"声称 {recv_result['claimed_type']} / 检测 {recv_result['detected_type']}"
                    f" — {'一致' if type_ok else '不一致'}")
            else:
                step5_data = {"文件类型识别": "✗ 解密失败，无法识别"}
                step5_state = "error"
                self.progress.emit("  ✗ 文件类型: 解密失败，无法识别")
            self.step_data.emit({"step": 5, "title": "文件类型识别",
                                 "state": step5_state,
                                 "target": "receiver",
                                 "data": step5_data})

            # ─── Receiver Step 6: Final conclusion ───
            all_ok = recv_result["success"]
            self.step_data.emit({"step": 6, "title": "最终结论",
                                 "state": "running", "target": "receiver", "data": {}})
            self.progress.emit("▶ 接收端 6/6: 最终结论")
            self.step_data.emit({"step": 6, "title": "最终结论",
                                 "state": "success" if all_ok else "error",
                                 "target": "receiver",
                                 "data": {
                                     "结论": "全部验证通过 — 数据完整、来源可信" if all_ok
                                             else "验证失败 — 安全性无法保证",
                                     "输出": recv_result["recovered_path"] if all_ok else "—",
                                 }})
            self.progress.emit("✓ 流程完成" if all_ok else "✗ 验证失败")

            result = {"send": send_result, "receive": recv_result, "_sm9_master": sm9_master}
            self.finished.emit(result)
        except Exception as exc:
            self.error.emit(str(exc))
        finally:
            root_logger.removeHandler(handler)

    def _tamper_envelope(self, message_path) -> None:
        """Tamper one field of the on-disk envelope to trigger a real failure.

        Each attack flips a byte / replaces a field so the receiver's genuine
        SM2/HMAC-SM3/SM9 checks reject the message — no faked results.
        """
        import base64
        from crypto.metadata_utils import load_envelope, save_envelope

        envelope = load_envelope(message_path)

        labels = {
            "ciphertext": "篡改密文",
            "nonce": "篡改 IV/Nonce",
            "receiver_id": "伪造接收方 ID",
            "filename": "篡改文件名",
            "signature": "伪造 SM9 签名",
        }
        self.progress.emit(f"⚠ 攻击模拟: {labels.get(self._attack, self._attack)} — 正在篡改信封")

        if self._attack == "ciphertext":
            envelope["ciphertext_b64"] = self._flip_b64(envelope["ciphertext_b64"])
        elif self._attack == "nonce":
            envelope["nonce_or_iv_b64"] = self._flip_b64(envelope["nonce_or_iv_b64"])
        elif self._attack == "receiver_id":
            envelope["header"]["receiver_id"] = "attacker@evil.local"
        elif self._attack == "filename":
            envelope["header"]["filename"] = "evil.exe"
        elif self._attack == "signature":
            envelope["signature_b64"] = self._flip_b64(envelope["signature_b64"])

        save_envelope(message_path, envelope)
        self.progress.emit("⚠ 信封已被篡改，移交接收端进行真实校验")

    @staticmethod
    def _flip_b64(value: str) -> str:
        """Flip one byte in a base64-encoded blob, returning re-encoded base64."""
        import base64
        raw = bytearray(base64.b64decode(value.encode("ascii")))
        if not raw:
            return value
        idx = len(raw) // 2
        raw[idx] ^= 0xFF
        return base64.b64encode(bytes(raw)).decode("ascii")


class BenchmarkWorker(QThread):
    """Runs core.benchmark.run_benchmark() in a background thread."""

    progress = Signal(str)
    finished = Signal(str)
    error = Signal(str)

    def run(self):
        handler = SignalHandler(self.progress)
        handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
        root_logger = logging.getLogger()
        root_logger.addHandler(handler)
        try:
            self.progress.emit("▶ 初始化基准测试环境")
            self.progress.emit("  测试数据量: 1KB, 64KB, 1MB")
            self.progress.emit("  测试算法: SM4-CBC, SM4-CTR, SM4-GCM, ZUC-128")
            from core.benchmark import run_benchmark
            md = run_benchmark(output_dir=ARTIFACTS)
            self.progress.emit("✓ 测试完成，结果已写入 artifacts/")
            self.finished.emit(md)
        except Exception as exc:
            self.error.emit(str(exc))
        finally:
            root_logger.removeHandler(handler)
