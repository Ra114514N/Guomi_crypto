"""Environment detection tab — calls crypto.gmssl_loader synchronously."""

import sys

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QTextEdit


class EnvTab(QWidget):
    def __init__(self, log_signal: Signal, parent=None):
        super().__init__(parent)
        self._log = log_signal
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        self.info_display = QTextEdit()
        self.info_display.setReadOnly(True)
        self.info_display.setPlaceholderText("点击「检测环境」查看系统信息...")
        layout.addWidget(self.info_display)

        btn = QPushButton("检测环境")
        btn.clicked.connect(self._on_detect)
        layout.addWidget(btn)

        self._on_detect()

    def _on_detect(self):
        from crypto.gmssl_loader import is_available, error_message

        sm9_status = "可用" if is_available() else f"不可用 - {error_message()}"
        lines = [
            f"Python: {sys.version.split()[0]}",
            "Protocol: envelope v3.0",
            "SM2: sm2_wrap (gmssl)",
            "SM3: hash (gmssl)",
            "SM4: CBC / CTR / GCM",
            "ZUC-128: enabled",
            f"SM9 native library: {sm9_status}",
        ]
        self.info_display.setPlainText("\n".join(lines))
        self._log.emit("环境检测完成")
