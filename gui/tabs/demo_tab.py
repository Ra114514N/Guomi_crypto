"""Envelope protocol demo tab — runs full workflow via QThread."""

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QComboBox, QLabel, QLineEdit, QFileDialog,
)

from gui import styles
from gui.effects import BusyDot
from gui.result_view import ResultView
from gui.workers import WorkflowWorker

DEFAULT_PLAIN = Path(__file__).resolve().parent.parent.parent / "plain.txt"


class DemoTab(QWidget):
    def __init__(self, log_signal: Signal, parent=None):
        super().__init__(parent)
        self._log = log_signal
        self._worker = None
        self._last_result = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Parameter row
        params = QHBoxLayout()
        params.setSpacing(6)
        params.addWidget(self._tag("算法"))
        self.algo_combo = QComboBox()
        self.algo_combo.addItems(["sm4-gcm", "sm4-cbc", "sm4-ctr", "zuc"])
        params.addWidget(self.algo_combo)

        params.addWidget(self._tag("文件"))
        self.file_edit = QLineEdit(str(DEFAULT_PLAIN))
        params.addWidget(self.file_edit, 1)

        browse_btn = QPushButton("浏览")
        browse_btn.setCursor(Qt.PointingHandCursor)
        browse_btn.clicked.connect(self._browse)
        params.addWidget(browse_btn)
        layout.addLayout(params)

        # Action row
        action_row = QHBoxLayout()
        action_row.addStretch()
        self.busy_dot = BusyDot(color=styles.accent_color)
        action_row.addWidget(self.busy_dot)
        self.run_btn = QPushButton("▶  运行演示")
        self.run_btn.setObjectName("primaryButton")
        self.run_btn.setCursor(Qt.PointingHandCursor)
        self.run_btn.setMinimumHeight(34)
        self.run_btn.clicked.connect(self._on_run)
        action_row.addWidget(self.run_btn)
        layout.addLayout(action_row)

        # Result display
        self.result_display = ResultView(placeholder="演示结果将显示在此处...")
        layout.addWidget(self.result_display, 1)

    def refresh_styles(self) -> None:
        self.algo_combo.setStyleSheet(styles.combobox_style)
        self.file_edit.setStyleSheet(styles.lineedit_style)
        self.result_display.setStyleSheet(styles.textedit_style)
        if self.run_btn.objectName() == "primaryButton":
            self.run_btn.setStyleSheet(styles.primary_button_style)
        self.busy_dot.set_color(styles.accent_color)
        if self._last_result is not None:
            self._render_result(self._last_result)

    def _tag(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(
            f"color: {styles.text_muted}; font-size: 11px; "
            f"font-weight: 600; padding: 0 4px;"
        )
        return lbl

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择明文文件")
        if path:
            self.file_edit.setText(path)

    def _parse_algo(self) -> tuple[str, str]:
        value = self.algo_combo.currentText()
        if value == "zuc":
            return "zuc", "cbc"
        return "sm4", value.split("-")[1]

    def _on_run(self):
        path = self.file_edit.text().strip()
        if not path or not Path(path).exists():
            self._log.emit("错误: 明文文件不存在")
            return

        cipher, mode = self._parse_algo()
        self.run_btn.setEnabled(False)
        self.busy_dot.start()
        self.result_display.clear_content()
        self._log.emit(
            f"▶ 开始信封协议演示 | 算法: {cipher.upper()}-{mode.upper()} | 文件: {path}"
        )

        self._worker = WorkflowWorker(path, cipher, mode)
        self._worker.progress.connect(self._log.emit)
        self._worker.finished.connect(self._on_done)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_done(self, result: dict):
        self._last_result = result
        self.run_btn.setEnabled(True)
        self.busy_dot.stop()
        self._render_result(result)
        self._log.emit("✓ 信封协议演示完成 — 全部中间过程已展示")

    def _render_result(self, result: dict) -> None:
        send = result["send"]
        recv = result["receive"]
        meta = send["meta"]
        header = meta["header"]
        v = self.result_display
        v.clear_content()

        # ─── Sender side ───────────────────────────────────────
        v.section("发送端处理过程")
        v.subsection("协议头信息")
        v.kv("协议版本", header["version"])
        v.kv("算法套件 ID", header["suite_id"])
        v.kv("对称加密算法", send["algo_label"])
        v.kv("密钥交换方式", header["kex_mode"])
        v.kv("发送方 ID", header["sender_id"])
        v.kv("接收方 ID", header["receiver_id"])
        v.kv_mono("会话 ID", header["session_id"])
        v.kv("时间戳", header["timestamp"])
        v.kv("序列号", header["seq"])

        v.subsection("SM2 密钥封装")
        v.hint("封装后的会话秘密 (Base64 前 64 字符):")
        v.code_block(meta["wrapped_secret_b64"][:64] + "...")
        v.kv("封装密文总长度", f"{len(meta['wrapped_secret_b64'])} 字符 (Base64)")

        v.subsection("对称加密")
        v.kv_mono("明文 SM3 摘要", send["plain_digest"])
        v.kv("密文长度", f"{meta['algo_meta']['ciphertext_len']} 字节")
        v.kv_mono("IV/Nonce", meta["nonce_or_iv_b64"])
        v.hint("密文 (Base64 前 64 字符):")
        v.code_block(meta["ciphertext_b64"][:64] + "...")

        v.subsection("完整性保护")
        integrity_algo = (
            "AES-GCM 内置认证" if header.get("mode") == "gcm"
            else header.get("integrity_algo", "HMAC-SM3")
        )
        v.kv("完整性算法", integrity_algo)
        v.hint("认证标签 (Base64):")
        v.code_block(meta["auth_tag_b64"])

        v.subsection("SM9 数字签名")
        v.hint("签名范围: header || wrapped_secret || nonce || ciphertext || auth_tag")
        v.hint("签名值 (Base64 前 64 字符):")
        v.code_block(meta["signature_b64"][:64] + "...")

        v.kv_mono("信封输出路径", f"{send['output_dir']}/message.json")

        # ─── Receiver side ─────────────────────────────────────
        v.section("接收端验证过程")
        v.subsection("解封装")
        v.paragraph("使用接收方 SM2 私钥解封会话秘密")
        v.paragraph("通过 HKDF-SM3 派生业务密钥 (上下文绑定: session_id|sender|receiver|suite)")

        v.subsection("验证结果")
        v.badge("SM9 签名验证", ok=recv["signature_ok"],
                 detail="数据来源可信" if recv["signature_ok"] else "签名不匹配")
        v.badge("HMAC/GCM 完整性", ok=recv["integrity_ok"],
                 detail="传输过程未被篡改" if recv["integrity_ok"] else "数据可能被篡改")
        v.badge("SM3 明文摘要比对", ok=recv["digest_ok"],
                 detail="解密结果与原文一致" if recv["digest_ok"] else "解密内容与原文不符")

        v.subsection("解密结果")
        v.kv("恢复明文长度", f"{recv['plaintext_len']} 字节")
        v.kv_mono("恢复文件路径", f"{recv['output_dir']}/recovered.txt")

        # ─── Conclusion ────────────────────────────────────────
        ok = recv["success"]
        v.conclusion(
            "全部验证通过 — 数据完整、来源可信、传输安全" if ok
            else "验证失败 — 安全性无法保证",
            ok=ok,
        )
        v.commit()

    def _on_error(self, msg: str):
        self.run_btn.setEnabled(True)
        self.busy_dot.stop()
        v = self.result_display
        v.clear_content()
        v.section("执行错误")
        v.paragraph(msg)
        v.commit()
        self._log.emit(f"✗ 演示执行失败: {msg}")
