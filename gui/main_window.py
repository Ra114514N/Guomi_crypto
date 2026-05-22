"""Main window with frameless chrome, custom title bar, and splitter layout."""

from PySide6.QtCore import Qt, Signal, QPoint
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QFrame, QLabel, QPushButton, QSplitter, QGroupBox,
    QTabWidget, QTextEdit, QComboBox, QLineEdit, QFileDialog,
)

from gui import styles
from gui.tabs.env_tab import EnvTab
from gui.tabs.demo_tab import DemoTab
from gui.tabs.send_recv_tab import SendRecvTab
from gui.tabs.benchmark_tab import BenchmarkTab


class MainWindow(QMainWindow):
    log_message = Signal(str)

    def __init__(self):
        super().__init__()
        self._drag_pos = QPoint()
        self._is_dark = styles.is_dark_mode()
        self._current_theme = "默认"
        self._exec_worker = None

        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMinimumSize(1000, 650)
        self.resize(1100, 720)

        self._build_ui()
        self._apply_theme()
        self.log_message.connect(self._append_log)

    def _build_ui(self):
        central = QWidget(objectName="central")
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self._build_title_bar(main_layout)
        self._build_content(main_layout)

    # ── Title Bar ──────────────────────────────────────────────

    def _build_title_bar(self, parent_layout: QVBoxLayout):
        self.title_bar = QFrame()
        self.title_bar.setFixedHeight(32)
        self.title_bar.setObjectName("titleBar")
        layout = QHBoxLayout(self.title_bar)
        layout.setContentsMargins(10, 0, 6, 0)
        layout.setSpacing(6)

        title_label = QLabel("国密安全传输系统")
        title_label.setFont(QFont(styles.current_font_family, 10, QFont.Bold))
        layout.addWidget(title_label)
        layout.addStretch()

        self.theme_btn = self._circle_button(styles.theme_button_color)
        self.theme_btn.setToolTip("切换主题")
        self.theme_btn.clicked.connect(self._open_theme_selector)
        layout.addWidget(self.theme_btn)

        self.min_btn = self._circle_button(styles.minimize_button_color)
        self.min_btn.setToolTip("最小化")
        self.min_btn.clicked.connect(self.showMinimized)
        layout.addWidget(self.min_btn)

        self.max_btn = self._circle_button(styles.maximize_button_color)
        self.max_btn.setToolTip("最大化")
        self.max_btn.clicked.connect(self._toggle_maximize)
        layout.addWidget(self.max_btn)

        self.close_btn = self._circle_button(styles.close_button_color)
        self.close_btn.setToolTip("关闭")
        self.close_btn.clicked.connect(self.close)
        layout.addWidget(self.close_btn)

        parent_layout.addWidget(self.title_bar)

    def _circle_button(self, color: str) -> QPushButton:
        btn = QPushButton()
        btn.setFixedSize(14, 14)
        btn.setStyleSheet(
            f"QPushButton {{ background-color: {color}; border-radius: 7px; border: none; }}"
            f"QPushButton:hover {{ border: 1px solid rgba(0,0,0,0.3); }}"
        )
        return btn

    # ── Content Area ───────────────────────────────────────────

    def _build_content(self, parent_layout: QVBoxLayout):
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(6, 4, 6, 6)
        content_layout.setSpacing(4)

        splitter = QSplitter(Qt.Vertical)

        upper = QWidget()
        upper_layout = QHBoxLayout(upper)
        upper_layout.setContentsMargins(0, 0, 0, 0)
        upper_layout.setSpacing(4)

        self._build_left_panel(upper_layout)
        self._build_right_panel(upper_layout)

        splitter.addWidget(upper)
        self._build_log_panel(splitter)

        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)

        content_layout.addWidget(splitter)
        parent_layout.addWidget(content)

    # ── Left Panel: Tabs ───────────────────────────────────────

    def _build_left_panel(self, parent_layout: QHBoxLayout):
        group = QGroupBox("功能区")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(4, 14, 4, 4)

        self.tab_widget = QTabWidget()
        self.env_tab = EnvTab(self.log_message)
        self.demo_tab = DemoTab(self.log_message)
        self.send_recv_tab = SendRecvTab(self.log_message)
        self.benchmark_tab = BenchmarkTab(self.log_message)

        self.tab_widget.addTab(self.env_tab, "环境")
        self.tab_widget.addTab(self.demo_tab, "演示")
        self.tab_widget.addTab(self.send_recv_tab, "收发")
        self.tab_widget.addTab(self.benchmark_tab, "性能")

        layout.addWidget(self.tab_widget)
        parent_layout.addWidget(group, 3)

    # ── Right Panel: Result Workbench ─────────────────────────

    def _build_right_panel(self, parent_layout: QHBoxLayout):
        group = QGroupBox("结果工作台")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(8, 18, 8, 8)
        layout.setSpacing(8)

        algo_label = QLabel("加密算法:")
        layout.addWidget(algo_label)
        self.algo_combo = QComboBox()
        self.algo_combo.addItems(["sm4-gcm", "sm4-cbc", "sm4-ctr", "zuc"])
        layout.addWidget(self.algo_combo)

        file_label = QLabel("明文文件:")
        layout.addWidget(file_label)
        file_row = QHBoxLayout()
        self.file_edit = QLineEdit(str(self._default_plain()))
        file_row.addWidget(self.file_edit)
        browse_btn = QPushButton("浏览")
        browse_btn.clicked.connect(self._browse_file)
        file_row.addWidget(browse_btn)
        layout.addLayout(file_row)

        self.run_btn = QPushButton("执行")
        self.run_btn.setFixedHeight(32)
        self.run_btn.clicked.connect(self._on_execute)
        layout.addWidget(self.run_btn)

        result_label = QLabel("最近结果:")
        layout.addWidget(result_label)
        self.result_summary = QTextEdit()
        self.result_summary.setReadOnly(True)
        self.result_summary.setPlaceholderText("执行后结果摘要将显示在此...")
        layout.addWidget(self.result_summary)

        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("color: gray; font-size: 11px;")
        layout.addWidget(self.status_label)

        parent_layout.addWidget(group, 2)

    # ── Log Panel ──────────────────────────────────────────────

    def _build_log_panel(self, splitter: QSplitter):
        group = QGroupBox("日志输出")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(4, 14, 4, 4)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        layout.addWidget(self.log_output)

        splitter.addWidget(group)

    # ── Theme ──────────────────────────────────────────────────

    def _apply_theme(self):
        styles.apply_color_scheme(self._current_theme, self._is_dark)
        self._refresh_styles()

    def _refresh_styles(self):
        self.centralWidget().setStyleSheet(styles.main_window_style)
        self.tab_widget.setStyleSheet(styles.tab_style)
        self.log_output.setStyleSheet(styles.log_style)
        self.result_summary.setStyleSheet(styles.textedit_style)
        self.algo_combo.setStyleSheet(styles.combobox_style)
        self.file_edit.setStyleSheet(styles.lineedit_style)

        for btn in self.findChildren(QPushButton):
            if btn in (self.theme_btn, self.min_btn, self.max_btn, self.close_btn):
                continue
            btn.setStyleSheet(styles.button_style)

        for group in self.findChildren(QGroupBox):
            group.setStyleSheet(styles.group_style)

    def _open_theme_selector(self):
        from gui.theme_selector import ThemeSelectorDialog
        dlg = ThemeSelectorDialog(self._current_theme, self._is_dark, self)
        dlg.theme_selected.connect(self._on_theme_selected)
        dlg.exec()

    def _on_theme_selected(self, theme_name: str, is_dark: bool):
        self._current_theme = theme_name
        self._is_dark = is_dark
        self._apply_theme()
        self.log_message.emit(f"切换主题: {theme_name} ({'深色' if is_dark else '浅色'})")

    # ── Helpers ────────────────────────────────────────────────

    @staticmethod
    def _default_plain():
        from pathlib import Path
        return Path(__file__).resolve().parent.parent / "plain.txt"

    def _browse_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择明文文件")
        if path:
            self.file_edit.setText(path)
            self.log_message.emit(f"选择文件: {path}")

    def _on_execute(self):
        """Quick-execute: triggers the demo workflow using right-panel params."""
        from gui.workers import WorkflowWorker
        from pathlib import Path

        path = self.file_edit.text().strip()
        if not path or not Path(path).exists():
            self.log_message.emit("错误: 明文文件不存在")
            return

        value = self.algo_combo.currentText()
        if value == "zuc":
            cipher, mode = "zuc", "cbc"
        else:
            cipher, mode = "sm4", value.split("-")[1]

        self.run_btn.setEnabled(False)
        self.status_label.setText("运行中...")
        self.result_summary.clear()
        self.log_message.emit(f"快速执行: {cipher}-{mode}")

        self._exec_worker = WorkflowWorker(path, cipher, mode)
        self._exec_worker.progress.connect(self.log_message.emit)
        self._exec_worker.finished.connect(self._on_exec_done)
        self._exec_worker.error.connect(self._on_exec_error)
        self._exec_worker.start()

    def _on_exec_done(self, result: dict):
        self.run_btn.setEnabled(True)
        self.status_label.setText("完成")
        send = result["send"]
        recv = result["receive"]
        lines = [
            f"算法: {send['algo_label']}",
            f"完整性: {'OK' if recv['integrity_ok'] else 'FAIL'}",
            f"签名: {'OK' if recv['signature_ok'] else 'FAIL'}",
            f"摘要: {'OK' if recv['digest_ok'] else 'FAIL'}",
            f"信封: {send['output_dir']}/message.json",
        ]
        self.result_summary.setPlainText("\n".join(lines))
        self.log_message.emit("快速执行完成")

    def _on_exec_error(self, msg: str):
        self.run_btn.setEnabled(True)
        self.status_label.setText("错误")
        self.result_summary.setPlainText(f"错误: {msg}")
        self.log_message.emit(f"快速执行失败: {msg}")

    def _toggle_maximize(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def _append_log(self, text: str):
        self.log_output.append(text)

    # ── Frameless Drag ─────────────────────────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and event.position().y() < 32:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton and not self._drag_pos.isNull():
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = QPoint()
