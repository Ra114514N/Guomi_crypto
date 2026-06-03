"""Benchmark tab — runs core.benchmark via QThread."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton

from gui import styles
from gui.effects import BusyDot
from gui.result_view import ResultView
from gui.workers import BenchmarkWorker


class BenchmarkTab(QWidget):
    def __init__(self, log_signal: Signal, parent=None):
        super().__init__(parent)
        self._log = log_signal
        self._worker = None
        self._last_md = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # Action row
        action_row = QHBoxLayout()
        action_row.addStretch()
        self.busy_dot = BusyDot(color=styles.accent_color)
        action_row.addWidget(self.busy_dot)
        self.run_btn = QPushButton("📊  运行基准测试")
        self.run_btn.setObjectName("primaryButton")
        self.run_btn.setCursor(Qt.PointingHandCursor)
        self.run_btn.setMinimumHeight(34)
        self.run_btn.clicked.connect(self._on_run)
        action_row.addWidget(self.run_btn)
        layout.addLayout(action_row)

        self.result_display = ResultView(placeholder="基准测试结果...")
        layout.addWidget(self.result_display, 1)

        # Pre-render the "before run" explanation
        self._render_intro()

    def refresh_styles(self) -> None:
        self.result_display.setStyleSheet(styles.textedit_style)
        if self.run_btn.objectName() == "primaryButton":
            self.run_btn.setStyleSheet(styles.primary_button_style)
        self.busy_dot.set_color(styles.accent_color)
        if self._last_md is not None:
            self._render_results(self._last_md)
        else:
            self._render_intro()

    def _render_intro(self) -> None:
        v = self.result_display
        v.clear_content()
        v.section("性能基准测试")
        v.subsection("测试设置")
        v.kv("测试主机", "当前主机 · 单线程执行")
        v.kv("测试数据量", "1 KB / 64 KB / 1 MB")
        v.kv("测试算法", "SM4-CBC, SM4-CTR, SM4-GCM, ZUC-128")
        v.subsection("各列含义")
        for k, d in [
            ("size", "测试数据大小"),
            ("suite", "对称加密算法套件"),
            ("encrypt_ms / decrypt_ms", "加解密耗时 (毫秒)"),
            ("sm3_ms", "SM3 哈希耗时 (毫秒)"),
            ("hmac_sm3_ms", "HMAC-SM3 计算耗时 (毫秒)"),
            ("sm9_sign_ms / sm9_verify_ms", "SM9 签名 / 验签耗时 (毫秒)"),
            ("sm2_wrap_ms / sm2_unwrap_ms", "SM2 密钥封装 / 解封装耗时 (毫秒)"),
            ("ciphertext_len", "密文长度 (字节)"),
            ("envelope_overhead", "信封额外开销 (字节)"),
        ]:
            v.kv(k, d)
        v.hint("点击「运行基准测试」开始")
        v.commit()

    def _on_run(self):
        self.run_btn.setEnabled(False)
        self.busy_dot.start()
        v = self.result_display
        v.clear_content()
        v.section("基准测试运行中…")
        v.paragraph("请稍候 — 各项指标计算完成后将在此处显示")
        v.commit()
        self._log.emit(
            "▶ 开始基准测试 | 测试数据量: 1KB, 64KB, 1MB | 算法: SM4-CBC/CTR/GCM, ZUC-128"
        )

        self._worker = BenchmarkWorker()
        self._worker.progress.connect(self._log.emit)
        self._worker.finished.connect(self._on_done)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_done(self, md_text: str):
        self._last_md = md_text
        self.run_btn.setEnabled(True)
        self.busy_dot.stop()
        self._render_results(md_text)
        self._log.emit("✓ 基准测试完成 — 结果已输出至 artifacts/benchmark.md 和 benchmark.csv")

    def _render_results(self, md_text: str) -> None:
        v = self.result_display
        v.clear_content()
        v.section("性能基准测试结果")
        v.subsection("测试环境")
        v.kv("测试主机", "当前主机 · 单线程执行")
        v.kv("测试数据量", "1 KB / 64 KB / 1 MB")
        v.kv("测试算法", "SM4-CBC, SM4-CTR, SM4-GCM, ZUC-128")
        v.subsection("详细数据")
        v.set_preformatted(md_text)
        v.hint("已输出: artifacts/benchmark.md 和 artifacts/benchmark.csv")
        v.commit()

    def _on_error(self, msg: str):
        self.run_btn.setEnabled(True)
        self.busy_dot.stop()
        v = self.result_display
        v.clear_content()
        v.section("执行错误")
        v.paragraph(msg)
        v.commit()
        self._log.emit(f"✗ 基准测试失败: {msg}")
