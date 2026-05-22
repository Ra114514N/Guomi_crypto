"""Send / Receive tab — uses WorkflowWorker, caches result for split display."""

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTextEdit, QLabel, QLineEdit, QComboBox, QFileDialog,
)

from gui.workers import WorkflowWorker

DEFAULT_PLAIN = Path(__file__).resolve().parent.parent.parent / "plain.txt"


class SendRecvTab(QWidget):
    def __init__(self, log_signal: Signal, parent=None):
        super().__init__(parent)
        self._log = log_signal
        self._worker = None
        self._last_result = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        algo_row = QHBoxLayout()
        algo_row.addWidget(QLabel("算法:"))
        self.algo_combo = QComboBox()
        self.algo_combo.addItems(["sm4-gcm", "sm4-cbc", "sm4-ctr", "zuc"])
        algo_row.addWidget(self.algo_combo)
        algo_row.addWidget(QLabel("文件:"))
        self.file_edit = QLineEdit(str(DEFAULT_PLAIN))
        algo_row.addWidget(self.file_edit, 1)
        browse_btn = QPushButton("浏览")
        browse_btn.clicked.connect(self._browse)
        algo_row.addWidget(browse_btn)
        layout.addLayout(algo_row)

        id_row = QHBoxLayout()
        id_row.addWidget(QLabel("发送方 ID:"))
        self.sender_edit = QLineEdit("sender@sm9.local")
        id_row.addWidget(self.sender_edit, 1)
        layout.addLayout(id_row)

        btn_row = QHBoxLayout()
        self.send_btn = QPushButton("发送")
        self.send_btn.clicked.connect(self._on_send)
        btn_row.addWidget(self.send_btn)

        self.recv_btn = QPushButton("接收")
        self.recv_btn.clicked.connect(self._on_recv)
        btn_row.addWidget(self.recv_btn)
        layout.addLayout(btn_row)

        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setPlaceholderText("收发结果...")
        layout.addWidget(self.output)

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择明文文件")
        if path:
            self.file_edit.setText(path)

    def _parse_algo(self) -> tuple[str, str]:
        value = self.algo_combo.currentText()
        if value == "zuc":
            return "zuc", "cbc"
        return "sm4", value.split("-")[1]

    def _on_send(self):
        path = self.file_edit.text().strip()
        if not path or not Path(path).exists():
            self._log.emit("错误: 明文文件不存在")
            return

        cipher, mode = self._parse_algo()
        sender_id = self.sender_edit.text().strip() or "sender@sm9.local"

        self.send_btn.setEnabled(False)
        self.recv_btn.setEnabled(False)
        self.output.clear()
        self._log.emit(f"开始发送: {cipher}-{mode}, 发送方: {sender_id}")

        self._worker = WorkflowWorker(path, cipher, mode, sender_id)
        self._worker.progress.connect(self._log.emit)
        self._worker.finished.connect(self._on_send_done)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_send_done(self, result: dict):
        self._last_result = result
        self.send_btn.setEnabled(True)
        self.recv_btn.setEnabled(True)
        send = result["send"]
        lines = [
            "=== 发送完成 ===",
            f"算法: {send['algo_label']}",
            f"明文摘要: {send['plain_digest'][:32]}...",
            f"认证标签: {send['auth_tag'][:32]}...",
            f"SM9 签名: {send['signature_hex'][:32]}...",
            f"信封文件: {send['output_dir']}/message.json",
            "",
            "点击「接收」查看解密验证结果",
        ]
        self.output.setPlainText("\n".join(lines))
        self._log.emit("发送完成，信封已生成")

    def _on_recv(self):
        if self._last_result is None:
            self._log.emit("请先执行「发送」生成信封")
            self.output.setPlainText("请先点击「发送」执行完整流程")
            return

        recv = self._last_result["receive"]
        lines = [
            "=== 接收验证结果 ===",
            f"算法: {recv['algo_label']}",
            f"发送方: {recv['sender_id']}",
            f"接收方: {recv['receiver_id']}",
            f"明文长度: {recv['plaintext_len']} bytes",
            f"完整性校验: {'通过' if recv['integrity_ok'] else '失败'}",
            f"签名验证: {'通过' if recv['signature_ok'] else '失败'}",
            f"摘要校验: {'通过' if recv['digest_ok'] else '失败'}",
            f"总体结果: {'成功' if recv['success'] else '失败'}",
        ]
        self.output.setPlainText("\n".join(lines))
        self._log.emit("接收验证完成")

    def _on_error(self, msg: str):
        self.send_btn.setEnabled(True)
        self.recv_btn.setEnabled(True)
        self.output.setPlainText(f"错误: {msg}")
        self._log.emit(f"收发失败: {msg}")
