"""Benchmark tab — runs core.benchmark via QThread."""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QTextEdit

from gui.workers import BenchmarkWorker


class BenchmarkTab(QWidget):
    def __init__(self, log_signal: Signal, parent=None):
        super().__init__(parent)
        self._log = log_signal
        self._worker = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        self.run_btn = QPushButton("运行基准测试")
        self.run_btn.clicked.connect(self._on_run)
        layout.addWidget(self.run_btn)

        self.result_display = QTextEdit()
        self.result_display.setReadOnly(True)
        self.result_display.setPlaceholderText("基准测试结果...")
        layout.addWidget(self.result_display)

    def _on_run(self):
        self.run_btn.setEnabled(False)
        self.result_display.clear()
        self._log.emit("开始基准测试...")

        self._worker = BenchmarkWorker()
        self._worker.progress.connect(self._log.emit)
        self._worker.finished.connect(self._on_done)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_done(self, md_text: str):
        self.run_btn.setEnabled(True)
        self.result_display.setPlainText(md_text)
        self._log.emit("基准测试完成")

    def _on_error(self, msg: str):
        self.run_btn.setEnabled(True)
        self.result_display.setPlainText(f"错误: {msg}")
        self._log.emit(f"基准测试失败: {msg}")
