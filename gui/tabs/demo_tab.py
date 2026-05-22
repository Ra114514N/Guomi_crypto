"""Envelope protocol demo tab — runs full workflow via QThread."""

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTextEdit, QComboBox, QLabel, QLineEdit, QFileDialog,
)

from gui.workers import WorkflowWorker

DEFAULT_PLAIN = Path(__file__).resolve().parent.parent.parent / "plain.txt"


class DemoTab(QWidget):
    def __init__(self, log_signal: Signal, parent=None):
        super().__init__(parent)
        self._log = log_signal
        self._worker = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        params = QHBoxLayout()
        params.addWidget(QLabel("算法:"))
        self.algo_combo = QComboBox()
        self.algo_combo.addItems(["sm4-gcm", "sm4-cbc", "sm4-ctr", "zuc"])
        params.addWidget(self.algo_combo)

        params.addWidget(QLabel("文件:"))
        self.file_edit = QLineEdit(str(DEFAULT_PLAIN))
        params.addWidget(self.file_edit, 1)

        browse_btn = QPushButton("浏览")
        browse_btn.clicked.connect(self._browse)
        params.addWidget(browse_btn)
        layout.addLayout(params)

        self.run_btn = QPushButton("运行演示")
        self.run_btn.clicked.connect(self._on_run)
        layout.addWidget(self.run_btn)

        self.result_display = QTextEdit()
        self.result_display.setReadOnly(True)
        self.result_display.setPlaceholderText("演示结果将显示在此处...")
        layout.addWidget(self.result_display)

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
        self.result_display.clear()
        self._log.emit(f"开始演示: {cipher}-{mode}, 文件: {Path(path).name}")

        self._worker = WorkflowWorker(path, cipher, mode)
        self._worker.progress.connect(self._log.emit)
        self._worker.finished.connect(self._on_done)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_done(self, result: dict):
        self.run_btn.setEnabled(True)
        send = result["send"]
        recv = result["receive"]
        lines = [
            "=== 演示结果 ===",
            f"算法: {send['algo_label']}",
            f"认证标签: {send['auth_tag'][:32]}...",
            f"签名: {send['signature_hex'][:32]}...",
            f"完整性校验: {'通过' if recv['integrity_ok'] else '失败'}",
            f"签名验证: {'通过' if recv['signature_ok'] else '失败'}",
            f"摘要校验: {'通过' if recv['digest_ok'] else '失败'}",
            f"输出目录: {send['output_dir']}",
        ]
        self.result_display.setPlainText("\n".join(lines))
        self._log.emit("演示完成")

    def _on_error(self, msg: str):
        self.run_btn.setEnabled(True)
        self.result_display.setPlainText(f"错误: {msg}")
        self._log.emit(f"演示失败: {msg}")
