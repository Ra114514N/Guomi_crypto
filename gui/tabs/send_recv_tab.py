"""Send / Receive tab — uses WorkflowWorker, caches result for split display."""

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QLineEdit, QComboBox, QFileDialog,
)

from gui import styles
from gui.effects import BusyDot
from gui.result_view import ResultView
from gui.workers import WorkflowWorker

DEFAULT_PLAIN = Path(__file__).resolve().parent.parent.parent / "plain.txt"


class SendRecvTab(QWidget):
    def __init__(self, log_signal: Signal, parent=None):
        super().__init__(parent)
        self._log = log_signal
        self._worker = None
        self._last_result = None
        self._stage = "idle"  # "idle" | "sent" | "received"

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # Algorithm + file row
        algo_row = QHBoxLayout()
        algo_row.setSpacing(6)
        algo_row.addWidget(self._tag("算法"))
        self.algo_combo = QComboBox()
        self.algo_combo.addItems(["sm4-gcm", "sm4-cbc", "sm4-ctr", "zuc"])
        algo_row.addWidget(self.algo_combo)
        algo_row.addWidget(self._tag("文件"))
        self.file_edit = QLineEdit(str(DEFAULT_PLAIN))
        algo_row.addWidget(self.file_edit, 1)
        browse_btn = QPushButton("浏览")
        browse_btn.setCursor(Qt.PointingHandCursor)
        browse_btn.clicked.connect(self._browse)
        algo_row.addWidget(browse_btn)
        layout.addLayout(algo_row)

        # ID row
        id_row = QHBoxLayout()
        id_row.setSpacing(6)
        id_row.addWidget(self._tag("发送方 ID"))
        self.sender_edit = QLineEdit("sender@sm9.local")
        id_row.addWidget(self.sender_edit, 1)
        layout.addLayout(id_row)

        # Action row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        btn_row.addStretch()
        self.busy_dot = BusyDot(color=styles.accent_color)
        btn_row.addWidget(self.busy_dot)
        self.send_btn = QPushButton("📤  发送")
        self.send_btn.setObjectName("primaryButton")
        self.send_btn.setCursor(Qt.PointingHandCursor)
        self.send_btn.setMinimumHeight(32)
        self.send_btn.clicked.connect(self._on_send)
        btn_row.addWidget(self.send_btn)
        self.recv_btn = QPushButton("📥  接收")
        self.recv_btn.setCursor(Qt.PointingHandCursor)
        self.recv_btn.setMinimumHeight(32)
        self.recv_btn.clicked.connect(self._on_recv)
        btn_row.addWidget(self.recv_btn)
        layout.addLayout(btn_row)

        # Output area
        self.output = ResultView(placeholder="收发结果...")
        layout.addWidget(self.output, 1)

    def refresh_styles(self) -> None:
        self.algo_combo.setStyleSheet(styles.combobox_style)
        self.file_edit.setStyleSheet(styles.lineedit_style)
        self.sender_edit.setStyleSheet(styles.lineedit_style)
        self.output.setStyleSheet(styles.textedit_style)
        if self.send_btn.objectName() == "primaryButton":
            self.send_btn.setStyleSheet(styles.primary_button_style)
        self.busy_dot.set_color(styles.accent_color)
        if self._last_result is not None:
            if self._stage == "sent":
                self._render_send(self._last_result)
            elif self._stage == "received":
                self._render_recv(self._last_result)

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

    # ── Send ──────────────────────────────────────────────────

    def _on_send(self):
        path = self.file_edit.text().strip()
        if not path or not Path(path).exists():
            self._log.emit("错误: 明文文件不存在")
            return

        cipher, mode = self._parse_algo()
        sender_id = self.sender_edit.text().strip() or "sender@sm9.local"

        self.send_btn.setEnabled(False)
        self.recv_btn.setEnabled(False)
        self.busy_dot.start()
        self.output.clear_content()
        self._log.emit(
            f"▶ 开始发送流程 | 算法: {cipher.upper()}-{mode.upper()} | 发送方: {sender_id}"
        )

        self._worker = WorkflowWorker(path, cipher, mode, sender_id)
        self._worker.progress.connect(self._log.emit)
        self._worker.finished.connect(self._on_send_done)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_send_done(self, result: dict):
        self._last_result = result
        self._stage = "sent"
        self.send_btn.setEnabled(True)
        self.recv_btn.setEnabled(True)
        self.busy_dot.stop()
        self._render_send(result)
        self._log.emit("✓ 发送流程完成 — 信封已生成")

    def _render_send(self, result: dict) -> None:
        send = result["send"]
        meta = send["meta"]
        header = meta["header"]
        v = self.output
        v.clear_content()

        v.section("发送端执行过程")

        v.subsection("步骤 1 · 生成会话秘密")
        v.paragraph("随机生成 16 字节会话秘密 (os.urandom)")
        v.kv_mono("会话 ID", header["session_id"])

        v.subsection("步骤 2 · SM2 密钥封装")
        v.paragraph("使用接收方 SM2 公钥封装会话秘密")
        v.hint("封装结果 (Base64 前 48 字符):")
        v.code_block(meta["wrapped_secret_b64"][:48] + "...")

        v.subsection("步骤 3 · HKDF-SM3 密钥派生")
        v.kv_mono(
            "上下文绑定",
            f"{header['session_id'][:16]}...|{header['sender_id']}|"
            f"{header['receiver_id']}|{header['suite_id']}",
        )
        v.paragraph("派生出: SM4密钥(16B) + SM4-IV(16B) + ZUC密钥(16B) + ZUC-IV(16B) + 完整性密钥(32B)")

        v.subsection("步骤 4 · 对称加密")
        v.kv("算法", send["algo_label"])
        v.kv_mono("明文 SM3 摘要", send["plain_digest"])
        v.kv_mono("IV/Nonce", meta["nonce_or_iv_b64"])
        v.kv("密文长度", f"{meta['algo_meta']['ciphertext_len']} 字节")
        v.hint("密文 (Base64 前 48 字符):")
        v.code_block(meta["ciphertext_b64"][:48] + "...")

        v.subsection("步骤 5 · 完整性保护")
        v.kv("算法", header.get("integrity_algo", "GCM 内置认证"))
        v.hint("认证标签:")
        v.code_block(meta["auth_tag_b64"])

        v.subsection("步骤 6 · SM9 签名")
        v.kv("签名者身份", header["sender_id"])
        v.paragraph("签名范围: header || wrapped_secret || nonce || ciphertext || auth_tag")
        v.hint("签名值 (Base64 前 48 字符):")
        v.code_block(meta["signature_b64"][:48] + "...")

        v.subsection("输出")
        v.kv_mono("信封文件", f"{send['output_dir']}/message.json")

        v.divider()
        v.hint("发送流程完成，点击「接收」查看解封装与验证过程")
        v.commit()

    # ── Receive ───────────────────────────────────────────────

    def _on_recv(self):
        if self._last_result is None:
            self._log.emit("提示: 请先执行「发送」生成信封")
            v = self.output
            v.clear_content()
            v.section("提示")
            v.paragraph("请先点击「发送」执行完整发送流程，生成 message.json 信封文件")
            v.commit()
            return

        self._stage = "received"
        self._render_recv(self._last_result)
        self._log.emit("✓ 接收端验证完成 — 全部中间过程已展示")

    def _render_recv(self, result: dict) -> None:
        recv = result["receive"]
        send = result["send"]
        meta = send["meta"]
        header = meta["header"]
        v = self.output
        v.clear_content()

        v.section("接收端验证过程")

        v.subsection("步骤 1 · 加载信封")
        v.paragraph("读取 message.json")
        v.kv("识别算法", recv["algo_label"])
        v.kv("发送方", recv["sender_id"])
        v.kv("接收方", recv["receiver_id"])

        v.subsection("步骤 2 · SM2 密钥解封装")
        v.paragraph("使用接收方 SM2 私钥解封会话秘密")
        v.paragraph("恢复 16 字节原始会话秘密")

        v.subsection("步骤 3 · HKDF-SM3 密钥派生")
        v.paragraph("使用相同上下文重新派生全部业务密钥")
        v.kv_mono(
            "上下文",
            f"{header['session_id'][:16]}...|{header['sender_id']}|"
            f"{header['receiver_id']}|{header['suite_id']}",
        )

        v.subsection("步骤 4 · SM9 签名验证")
        v.paragraph(f"验证者使用发送方身份 '{recv['sender_id']}' 和 SM9 主公钥")
        v.paragraph("重建 transcript = header || wrapped_secret || nonce || ciphertext || auth_tag")
        v.badge("签名验证", ok=recv["signature_ok"],
                 detail="确认数据来源为声称的发送方" if recv["signature_ok"]
                 else "数据来源不可信")

        v.subsection("步骤 5 · 完整性验证")
        v.kv("算法", header.get("integrity_algo", "GCM 内置认证"))
        v.paragraph("重新计算 HMAC / 验证 GCM Tag")
        v.badge("完整性验证", ok=recv["integrity_ok"],
                 detail="数据在传输中未被篡改" if recv["integrity_ok"]
                 else "数据可能已被篡改")

        v.subsection("步骤 6 · 解密与摘要比对")
        v.paragraph("使用派生的对称密钥解密密文")
        v.kv("恢复明文长度", f"{recv['plaintext_len']} 字节")
        v.paragraph("重新计算明文 SM3 摘要并与信封中记录的摘要比对")
        v.badge("摘要比对", ok=recv["digest_ok"],
                 detail="解密内容与原始明文完全相同" if recv["digest_ok"]
                 else "解密结果与原文不符")

        v.section("最终安全结论")
        if recv["success"]:
            v.conclusion("全部验证通过 — 数据完整、来源可信、传输安全", ok=True)
            v.paragraph("1. 数据来源可信 (SM9 签名验证通过)")
            v.paragraph("2. 数据未被篡改 (完整性验证通过)")
            v.paragraph("3. 解密正确 (明文摘要比对通过)")
            v.kv_mono("恢复明文", f"{recv['output_dir']}/recovered.txt")
        else:
            v.conclusion("验证失败 — 安全性无法保证", ok=False)
            v.badge("签名验证", ok=recv["signature_ok"])
            v.badge("完整性验证", ok=recv["integrity_ok"])
            v.badge("摘要比对", ok=recv["digest_ok"])

        v.commit()

    def _on_error(self, msg: str):
        self.send_btn.setEnabled(True)
        self.recv_btn.setEnabled(True)
        self.busy_dot.stop()
        v = self.output
        v.clear_content()
        v.section("执行错误")
        v.paragraph(msg)
        v.commit()
        self._log.emit(f"✗ 收发流程失败: {msg}")
