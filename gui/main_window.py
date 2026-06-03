"""Main window — deep-space immersive layout.

Layout:
┌─────────────────────────────────────────────────────────────┐
│ ⬡ Title                        [algo ▼] [⚡ 启动演示]  [◑]  │  <- top bar
├────────┬──────────────────────────────────────┬─────────────┤
│  Nav   │  TimelineView (center)               │  Log panel  │
│  btns  │                                      │  (toggle)   │
└────────┴──────────────────────────────────────┴─────────────┘
"""

from pathlib import Path

from PySide6.QtCore import Qt, Signal, QPoint, QTimer, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QFrame, QLabel, QPushButton, QComboBox, QLineEdit,
    QFileDialog, QStackedWidget, QSplitter,
)

from gui import styles
from gui.effects import add_drop_shadow, BusyDot, StatusIndicator, BrandMark
from gui.log_widget import LogWidget
from gui.timeline_view import TimelineView
from gui.tabs.env_tab import EnvTab
from gui.tabs.benchmark_tab import BenchmarkTab


# PLACEHOLDER_APPEND_MARKER


class MainWindow(QMainWindow):
    log_message = Signal(str)

    def __init__(self):
        super().__init__()
        self._drag_pos = QPoint()
        self._current_theme = "深空"
        self._is_dark = True
        self._exec_worker = None
        self._current_nav = "demo"

        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMinimumSize(1060, 680)
        self.resize(1220, 780)

        self._build_ui()
        self._apply_theme()
        self.log_message.connect(self._append_log)

        QTimer.singleShot(80, self._emit_welcome)

    def _emit_welcome(self):
        self.log_message.emit("═══ 国密安全传输系统 ═══")
        self.log_message.emit("▶ 系统就绪 — 选择算法后点击「启动演示」")

    # ── Build UI ───────────────────────────────────────────────

    def _build_ui(self):
        central = QWidget(objectName="central")
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self._build_top_bar(main_layout)
        self._build_body(main_layout)

        add_drop_shadow(central, blur=32, dx=0, dy=6, alpha=85)

    # ── Top Bar ────────────────────────────────────────────────

    def _build_top_bar(self, parent_layout: QVBoxLayout):
        self.title_bar = QFrame(objectName="titleBar")
        self.title_bar.setFixedHeight(44)
        layout = QHBoxLayout(self.title_bar)
        layout.setContentsMargins(16, 0, 10, 0)
        layout.setSpacing(12)

        self.brand_mark = BrandMark(color=styles.accent_color)
        layout.addWidget(self.brand_mark)

        self.title_label = QLabel("国密安全数据传输演示系统")
        self.title_label.setObjectName("titleLabel")
        self.title_label.setFont(QFont(styles.current_font_family, 11, QFont.Bold))
        layout.addWidget(self.title_label)
        layout.addStretch()

        # Algorithm selector
        self.algo_combo = QComboBox()
        self.algo_combo.addItems(["sm4-gcm", "sm4-cbc", "sm4-ctr", "zuc"])
        self.algo_combo.setFixedWidth(110)
        layout.addWidget(self.algo_combo)

        # Attack simulation selector — tampers the envelope before receiving
        self.attack_combo = QComboBox()
        self.attack_combo.addItem("正常传输", "none")
        self.attack_combo.addItem("篡改密文", "ciphertext")
        self.attack_combo.addItem("篡改 IV/Nonce", "nonce")
        self.attack_combo.addItem("伪造接收方 ID", "receiver_id")
        self.attack_combo.addItem("伪造 SM9 签名", "signature")
        self.attack_combo.setFixedWidth(130)
        self.attack_combo.setToolTip("攻击模拟：发送后、接收前篡改信封，触发真实校验失败")
        layout.addWidget(self.attack_combo)

        # File picker (compact)
        self.file_edit = QLineEdit(str(self._default_plain()))
        self.file_edit.setFixedWidth(180)
        self.file_edit.setPlaceholderText("明文文件路径")
        layout.addWidget(self.file_edit)
        browse_btn = QPushButton("…")
        browse_btn.setFixedSize(28, 28)
        browse_btn.setCursor(Qt.PointingHandCursor)
        browse_btn.clicked.connect(self._browse_file)
        layout.addWidget(browse_btn)

        # Launch button
        self.run_btn = QPushButton("⚡  启动演示")
        self.run_btn.setObjectName("primaryButton")
        self.run_btn.setFixedHeight(30)
        self.run_btn.setCursor(Qt.PointingHandCursor)
        self.run_btn.clicked.connect(self._on_execute)
        layout.addWidget(self.run_btn)

        # Status
        self.busy_dot = BusyDot(color=styles.accent_color)
        layout.addWidget(self.busy_dot)

        # Theme button — minimal glyph
        self.theme_btn = self._win_control_button("◑", "WinThemeButton")
        self.theme_btn.setToolTip("切换主题")
        self.theme_btn.clicked.connect(self._open_theme_selector)
        layout.addWidget(self.theme_btn)

        # Window controls — geometric micro-glyphs
        self.min_btn = self._win_control_button("—", "WinMinButton")
        self.min_btn.setToolTip("最小化")
        self.min_btn.clicked.connect(self.showMinimized)
        layout.addWidget(self.min_btn)

        self.max_btn = self._win_control_button("□", "WinMaxButton")
        self.max_btn.setToolTip("最大化 / 还原")
        self.max_btn.clicked.connect(self._toggle_maximize)
        layout.addWidget(self.max_btn)

        self.close_btn = self._win_control_button("×", "WinCloseButton")
        self.close_btn.setToolTip("关闭")
        self.close_btn.clicked.connect(self.close)
        layout.addWidget(self.close_btn)

        parent_layout.addWidget(self.title_bar)

    # ── Body (nav + center + log) ─────────────────────────────

    def _build_body(self, parent_layout: QVBoxLayout):
        body = QWidget()
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        self._build_nav(body_layout)
        self._build_center(body_layout)
        self._build_log_panel(body_layout)

        parent_layout.addWidget(body, 1)

    # ── Left Nav ───────────────────────────────────────────────

    def _build_nav(self, parent_layout: QHBoxLayout):
        nav = QFrame(objectName="navPanel")
        nav.setFixedWidth(72)
        nav_layout = QVBoxLayout(nav)
        nav_layout.setContentsMargins(8, 12, 8, 12)
        nav_layout.setSpacing(4)

        self._nav_buttons = {}
        nav_items = [
            ("demo", "◈\n演示"),
            ("send_recv", "◈\n收发"),
            ("env", "◈\n环境"),
            ("bench", "◈\n性能"),
        ]
        for key, label in nav_items:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedHeight(52)
            btn.clicked.connect(lambda checked, k=key: self._on_nav(k))
            nav_layout.addWidget(btn)
            self._nav_buttons[key] = btn

        nav_layout.addStretch()

        # Log toggle at bottom
        self._log_toggle_btn = QPushButton(">_")
        self._log_toggle_btn.setCheckable(True)
        self._log_toggle_btn.setChecked(True)
        self._log_toggle_btn.setCursor(Qt.PointingHandCursor)
        self._log_toggle_btn.setFixedHeight(36)
        self._log_toggle_btn.setToolTip("显示/隐藏日志")
        self._log_toggle_btn.clicked.connect(self._toggle_log)
        nav_layout.addWidget(self._log_toggle_btn)

        self._nav_buttons["demo"].setChecked(True)
        parent_layout.addWidget(nav)

    # ── Center (stacked: timeline / env / benchmark) ──────────

    def _build_center(self, parent_layout: QHBoxLayout):
        self._stack = QStackedWidget()

        # Page 0: Timeline (demo + send/recv share this)
        self.timeline = TimelineView()
        self._stack.addWidget(self.timeline)

        # Page 1: Env tab
        self.env_tab = EnvTab(self.log_message)
        self._stack.addWidget(self.env_tab)

        # Page 2: Benchmark tab
        self.benchmark_tab = BenchmarkTab(self.log_message)
        self._stack.addWidget(self.benchmark_tab)

        self._stack.setCurrentIndex(0)
        parent_layout.addWidget(self._stack, 1)

    # ── Right Log Panel ────────────────────────────────────────

    def _build_log_panel(self, parent_layout: QHBoxLayout):
        self._log_frame = QFrame(objectName="logPanel")
        self._log_frame.setFixedWidth(280)
        log_layout = QVBoxLayout(self._log_frame)
        log_layout.setContentsMargins(0, 8, 8, 8)
        log_layout.setSpacing(4)

        header = QHBoxLayout()
        header.setContentsMargins(10, 0, 4, 0)
        lbl = QLabel(">_ 日志")
        lbl.setStyleSheet(
            f"color: {styles.text_muted}; font-size: 11px; font-weight: 600; background: transparent;"
        )
        header.addWidget(lbl)
        header.addStretch()
        clear_btn = QPushButton("清空")
        clear_btn.setFixedHeight(22)
        clear_btn.setCursor(Qt.PointingHandCursor)
        clear_btn.clicked.connect(self._on_clear_log)
        header.addWidget(clear_btn)
        log_layout.addLayout(header)

        self.log_output = LogWidget()
        log_layout.addWidget(self.log_output, 1)

        parent_layout.addWidget(self._log_frame)

    # ── Theme ──────────────────────────────────────────────────

    def _apply_theme(self):
        styles.apply_color_scheme(self._current_theme, self._is_dark)
        self._refresh_styles()

    def _refresh_styles(self):
        self.centralWidget().setStyleSheet(styles.main_window_style)
        self.title_bar.setStyleSheet(styles.title_bar_style)
        self.algo_combo.setStyleSheet(styles.combobox_style)
        self.attack_combo.setStyleSheet(styles.combobox_style)
        self.file_edit.setStyleSheet(styles.lineedit_style)
        self.log_output.setStyleSheet(styles.log_style)

        # Nav buttons
        for btn in self._nav_buttons.values():
            btn.setStyleSheet(styles.nav_button_style)
        self._log_toggle_btn.setStyleSheet(styles.nav_button_style)

        # Nav panel background
        nav_panel = self.findChild(QFrame, "navPanel")
        if nav_panel:
            nav_panel.setStyleSheet(
                f"QFrame#navPanel {{ background-color: {styles.surface_color}; "
                f"border-right: 1px solid {styles.border_subtle}; }}"
            )

        # Log panel background
        self._log_frame.setStyleSheet(
            f"QFrame#logPanel {{ background-color: {styles.surface_color}; "
            f"border-left: 1px solid {styles.border_subtle}; }}"
        )

        # Buttons
        for btn in self.findChildren(QPushButton):
            if btn in (self.theme_btn, self.min_btn, self.max_btn, self.close_btn):
                continue
            if btn in self._nav_buttons.values() or btn is self._log_toggle_btn:
                continue
            if btn.objectName() == "primaryButton":
                btn.setStyleSheet(styles.primary_button_style)
            else:
                btn.setStyleSheet(styles.button_style)

        # Window control buttons
        for btn in (self.theme_btn, self.min_btn, self.max_btn, self.close_btn):
            btn.setStyleSheet(styles.win_control_style)

        self.brand_mark.set_color(styles.accent_color)
        self.busy_dot.set_color(styles.accent_color)
        self.timeline.refresh_styles()

        if hasattr(self, 'env_tab') and hasattr(self.env_tab, 'refresh_styles'):
            self.env_tab.refresh_styles()
        if hasattr(self, 'benchmark_tab') and hasattr(self.benchmark_tab, 'refresh_styles'):
            self.benchmark_tab.refresh_styles()

    def _open_theme_selector(self):
        from gui.theme_selector import ThemeSelectorDialog
        dlg = ThemeSelectorDialog(self._current_theme, self._is_dark, self)
        dlg.theme_selected.connect(self._on_theme_selected)
        dlg.exec()

    def _on_theme_selected(self, theme_name: str, is_dark: bool):
        self._current_theme = theme_name
        self._is_dark = is_dark
        self._apply_theme()
        self.log_message.emit(f"▶ 切换主题: {theme_name} ({'深色' if is_dark else '浅色'})")

    # ── Navigation ─────────────────────────────────────────────

    def _on_nav(self, key: str):
        for k, btn in self._nav_buttons.items():
            btn.setChecked(k == key)
        self._current_nav = key

        if key == "demo" or key == "send_recv":
            self._stack.setCurrentIndex(0)
        elif key == "env":
            self._stack.setCurrentIndex(1)
        elif key == "bench":
            self._stack.setCurrentIndex(2)

    # ── Execute ────────────────────────────────────────────────

    def _on_execute(self):
        from gui.workers import WorkflowWorker

        path = self.file_edit.text().strip()
        if not path or not Path(path).exists():
            self.log_message.emit("✗ 错误: 明文文件不存在")
            return

        value = self.algo_combo.currentText()
        if value == "zuc":
            cipher, mode = "zuc", "cbc"
        else:
            cipher, mode = "sm4", value.split("-")[1]

        self.run_btn.setEnabled(False)
        self.busy_dot.set_color(styles.warning_color)
        self.busy_dot.start()
        self.timeline.clear_steps()
        attack = self.attack_combo.currentData()
        if attack and attack != "none":
            self.log_message.emit(
                f"▶ 启动演示: {cipher.upper()}-{mode.upper()} | ⚠ 攻击模拟: {self.attack_combo.currentText()}"
            )
        else:
            self.log_message.emit(f"▶ 启动演示: {cipher.upper()}-{mode.upper()}")

        # Switch to timeline view
        self._on_nav("demo")

        self._exec_worker = WorkflowWorker(path, cipher, mode, attack=attack)
        self._exec_worker.progress.connect(self.log_message.emit)
        self._exec_worker.step_data.connect(self._on_step_data)
        self._exec_worker.finished.connect(self._on_exec_done)
        self._exec_worker.error.connect(self._on_exec_error)
        self._exec_worker.start()

    def _on_step_data(self, data: dict):
        step = data["step"]
        title = data["title"]
        state = data["state"]
        kv = data.get("data", {})

        current_count = len(self.timeline._cards)

        if state == "running":
            self.timeline.add_step(step, title, state="running", animate=True)
        elif step > current_count:
            # New step that skipped "running" state (e.g. conclusion)
            card = self.timeline.add_step(step, title, data=kv, state=state, animate=True)
        else:
            self.timeline.update_last_card_state(state)
            if kv:
                cards = self.timeline._cards
                if cards:
                    cards[-1].set_data_rows(kv)

    def _on_exec_done(self, result: dict):
        self.run_btn.setEnabled(True)
        self.busy_dot.set_color(styles.success_color)
        self.busy_dot.stop()
        self.log_message.emit("✓ 演示流程完成")

    def _on_exec_error(self, msg: str):
        self.run_btn.setEnabled(True)
        self.busy_dot.set_color(styles.error_color)
        self.busy_dot.stop()
        self.timeline.add_step(0, "执行错误", {"错误信息": msg}, state="error")
        self.log_message.emit(f"✗ 执行失败: {msg}")

    # ── Log toggle ─────────────────────────────────────────────

    def _toggle_log(self):
        visible = self._log_frame.isVisible()
        self._log_frame.setVisible(not visible)

    def _on_clear_log(self):
        self.log_output.clear_log()

    # ── Helpers ────────────────────────────────────────────────

    @staticmethod
    def _default_plain():
        import sys
        if getattr(sys, 'frozen', False):
            return Path(getattr(sys, '_MEIPASS', Path(sys.executable).parent)) / "plain.txt"
        return Path(__file__).resolve().parent.parent / "plain.txt"

    def _browse_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择明文文件")
        if path:
            self.file_edit.setText(path)
            self.log_message.emit(f"▶ 选择文件: {path}")

    def _win_control_button(self, glyph: str, object_name: str) -> QPushButton:
        btn = QPushButton(glyph)
        btn.setObjectName(object_name)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(styles.win_control_style)
        return btn

    def _toggle_maximize(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def _append_log(self, text: str):
        self.log_output.append_message(text)

    # ── Frameless Drag ─────────────────────────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and event.position().y() < 44:
            self._drag_pos = (event.globalPosition().toPoint()
                              - self.frameGeometry().topLeft())
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton and not self._drag_pos.isNull():
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = QPoint()

    def mouseDoubleClickEvent(self, event):
        if event.position().y() < 44:
            self._toggle_maximize()
