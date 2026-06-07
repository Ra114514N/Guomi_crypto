"""Independent receiver-side window for verification display.

Layout:
┌─────────────────────────────────────────────────────────────┐
│ 📥 基于国密算法的安全数据传输与身份认证系统 — 接收端 [—][□][×] │  <- title bar 44px
├─────────────────────────────────────────────────┬───────────┤
│  TimelineView (center, flex)                    │ >_ 日志   │
│                                                 │  250px    │
└─────────────────────────────────────────────────┴───────────┘
"""

from PySide6.QtCore import Qt, QPoint, QRect, QPropertyAnimation, QEasingCurve, QParallelAnimationGroup
from PySide6.QtGui import QFont, QPixmap, QPainter
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QFrame, QLabel, QPushButton,
    QGraphicsOpacityEffect,
)

from gui import styles
from gui.elided_label import ElidedLabel
from gui.effects import add_drop_shadow
from gui.frameless_resize import ResizeCursorFilter, cursor_shape_for_edges, edge_flags_at
from gui.log_widget import LogWidget
from gui.timeline_view import TimelineView


class _ThemeOverlay(QWidget):
    """Full-window overlay that cross-fades from old theme screenshot to new."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self._pixmap = QPixmap()

        self._opacity_effect = QGraphicsOpacityEffect(self)
        self._opacity_effect.setOpacity(1.0)
        self.setGraphicsEffect(self._opacity_effect)

    @property
    def opacity_effect(self):
        return self._opacity_effect

    def set_old_skin(self, pixmap: QPixmap):
        self._pixmap = pixmap
        self.resize(self.parent().size())
        self.raise_()
        self.show()

    def paintEvent(self, event):
        if not self._pixmap.isNull():
            painter = QPainter(self)
            painter.drawPixmap(0, 0, self._pixmap)
            painter.end()

    def resizeEvent(self, event):
        if self.parent():
            self.resize(self.parent().size())


class ReceiverWindow(QMainWindow):
    """Independent window showing the receiver-side verification timeline."""

    def __init__(self, is_dark: bool = False, parent=None):
        super().__init__(parent)
        self._drag_pos = QPoint()
        self._is_dark = is_dark

        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMouseTracking(True)
        self.setMinimumSize(840, 680)
        self.resize(1080, 960)
        self.setWindowTitle("基于国密算法的安全数据传输与身份认证系统 — 接收端")

        self._build_ui()
        self._resize_cursor_filter = ResizeCursorFilter(self, self._EDGE)
        self._resize_cursor_filter.install_recursively(self)
        self._apply_theme()

    # ── Build UI ───────────────────────────────────────────────

    def _build_ui(self):
        central = QWidget(objectName="central")
        central.setMouseTracking(True)
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

        self.title_label = ElidedLabel("\U0001F4E5 基于国密算法的安全数据传输与身份认证系统 — 接收端")
        self.title_label.setObjectName("titleLabel")
        self.title_label.setFont(QFont(styles.current_font_family, 11, QFont.Bold))
        self.title_label.setMaximumWidth(520)
        self.title_label.setToolTip("基于国密算法的安全数据传输与身份认证系统 — 接收端")
        layout.addWidget(self.title_label)
        layout.addStretch()

        # Window controls
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

    # ── Body (timeline + log) ─────────────────────────────────

    def _build_body(self, parent_layout: QVBoxLayout):
        body = QWidget()
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        # Center: timeline
        self.timeline = TimelineView(auto_scroll=False)
        body_layout.addWidget(self.timeline, 1)

        # Right: log panel
        self._build_log_panel(body_layout)

        parent_layout.addWidget(body, 1)

    # ── Right Log Panel ────────────────────────────────────────

    def _build_log_panel(self, parent_layout: QHBoxLayout):
        self._log_frame = QFrame(objectName="logPanel")
        self._log_frame.setFixedWidth(300)
        log_layout = QVBoxLayout(self._log_frame)
        log_layout.setContentsMargins(0, 8, 8, 8)
        log_layout.setSpacing(4)

        header = QHBoxLayout()
        header.setContentsMargins(10, 0, 4, 0)
        lbl = QLabel(">_ 日志")
        lbl.setStyleSheet(
            f"color: {styles.text_muted}; font-size: 11px; "
            f"font-weight: 600; background: transparent;"
        )
        header.addWidget(lbl)
        header.addStretch()
        log_layout.addLayout(header)

        self.log_output = LogWidget()
        log_layout.addWidget(self.log_output, 1)

        parent_layout.addWidget(self._log_frame)

    # ── Theme ──────────────────────────────────────────────────

    def _apply_theme(self):
        styles.apply_color_scheme("默认", self._is_dark)
        self._refresh_styles()

    def _refresh_styles(self):
        self.centralWidget().setStyleSheet(styles.main_window_style)
        self.title_bar.setStyleSheet(styles.title_bar_style)
        self.log_output.setStyleSheet(styles.log_style)

        # Log panel background
        self._log_frame.setStyleSheet(
            f"QFrame#logPanel {{ background-color: {styles.surface_color}; "
            f"border-left: 1px solid {styles.border_subtle}; }}"
        )

        # Window control buttons
        for btn in (self.min_btn, self.max_btn, self.close_btn):
            btn.setStyleSheet(styles.win_control_style)

        self.timeline.refresh_styles()

    def sync_theme(self, is_dark: bool):
        """Sync theme with the sender window, with overlay animation."""
        if is_dark == self._is_dark:
            return

        old_skin = self.grab()

        overlay = _ThemeOverlay(self)
        overlay.set_old_skin(old_skin)
        overlay.repaint()

        self._is_dark = is_dark
        self._apply_theme()

        anim = QPropertyAnimation(overlay.opacity_effect, b"opacity", self)
        anim.setDuration(450)
        anim.setEasingCurve(QEasingCurve.InOutQuad)
        anim.setStartValue(1.0)
        anim.setEndValue(0.0)
        anim.finished.connect(overlay.deleteLater)
        anim.start()
        self._theme_anim = anim

    # ── Public API ─────────────────────────────────────────────

    def on_step_data(self, data: dict):
        """Receive step data and render in timeline."""
        step = data["step"]
        title = data["title"]
        state = data["state"]
        kv = data.get("data", {})

        current_count = len(self.timeline._cards)

        if state == "running":
            self.timeline.add_step(step, title, state="running", animate=True)
        elif step > current_count:
            self.timeline.add_step(step, title, data=kv, state=state, animate=True)
        else:
            self.timeline.update_last_card_state(state)
            if kv:
                cards = self.timeline._cards
                if cards:
                    cards[-1].set_data_rows(kv)

    def on_progress(self, text: str):
        """Append log message."""
        self.log_output.append_message(text)

    def present_from_sender(self, sender_geometry: QRect):
        """Show near the sender window with a short slide/fade transition."""
        target = self._target_geometry_near(sender_geometry)
        start_pos = QPoint(target.x() + 36, target.y())

        self.resize(target.size())
        self.setWindowOpacity(0.0)
        self.move(start_pos)
        self.show()
        self.raise_()
        self.activateWindow()

        fade = QPropertyAnimation(self, b"windowOpacity", self)
        fade.setDuration(220)
        fade.setStartValue(0.0)
        fade.setEndValue(1.0)
        fade.setEasingCurve(QEasingCurve.OutCubic)

        slide = QPropertyAnimation(self, b"pos", self)
        slide.setDuration(260)
        slide.setStartValue(start_pos)
        slide.setEndValue(target.topLeft())
        slide.setEasingCurve(QEasingCurve.OutCubic)

        group = QParallelAnimationGroup(self)
        group.addAnimation(fade)
        group.addAnimation(slide)
        group.finished.connect(lambda: self.setWindowOpacity(1.0))
        group.start(QPropertyAnimation.DeleteWhenStopped)
        self._present_anim = group

    def _target_geometry_near(self, sender_geometry: QRect) -> QRect:
        screen = self.screen()
        available = screen.availableGeometry() if screen else sender_geometry
        margin = 18
        width = min(max(self.width(), self.minimumWidth()), available.width() - margin * 2)
        height = min(max(self.height(), self.minimumHeight()), available.height() - margin * 2)

        x = sender_geometry.right() + margin
        if x + width > available.right():
            x = sender_geometry.left() + 180
        if x < available.left() + margin:
            x = available.left() + margin
        if x + width > available.right() - margin:
            x = available.right() - width - margin

        y = sender_geometry.top() + 64
        if y + height > available.bottom():
            y = available.bottom() - height - margin
        y = max(available.top() + margin, y)
        return QRect(x, y, width, height)

    # ── Helpers ────────────────────────────────────────────────

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

    # ── Frameless Drag & Resize ─────────────────────────────────

    _EDGE = 12

    def _edge_at(self, pos):
        return edge_flags_at(pos, self.size(), self._EDGE)

    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton:
            return
        pos = event.position().toPoint()
        left, right, top, bottom = self._edge_at(pos)
        if left or right or top or bottom:
            self._resize_edge = (left, right, top, bottom)
            self._resize_start_geo = self.geometry()
            self._resize_start_pos = event.globalPosition().toPoint()
        elif pos.y() < 44:
            self._resize_edge = None
            self._drag_pos = (event.globalPosition().toPoint()
                              - self.frameGeometry().topLeft())
        else:
            self._resize_edge = None
        event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            if getattr(self, '_resize_edge', None):
                self._do_resize(event.globalPosition().toPoint())
                event.accept()
                return
            if self._drag_pos and not self._drag_pos.isNull():
                self.move(event.globalPosition().toPoint() - self._drag_pos)
                event.accept()
                return
        else:
            pos = event.position().toPoint()
            self.setCursor(cursor_shape_for_edges(self._edge_at(pos)))

    def _do_resize(self, global_pos):
        left, right, top, bottom = self._resize_edge
        geo = QRect(self._resize_start_geo)
        delta = global_pos - self._resize_start_pos
        min_w, min_h = self.minimumWidth(), self.minimumHeight()

        if right:
            geo.setRight(geo.right() + delta.x())
        if bottom:
            geo.setBottom(geo.bottom() + delta.y())
        if left:
            geo.setLeft(geo.left() + delta.x())
        if top:
            geo.setTop(geo.top() + delta.y())

        if geo.width() < min_w:
            if left:
                geo.setLeft(geo.right() - min_w)
            else:
                geo.setRight(geo.left() + min_w)
        if geo.height() < min_h:
            if top:
                geo.setTop(geo.bottom() - min_h)
            else:
                geo.setBottom(geo.top() + min_h)

        self.setGeometry(geo)

    def mouseReleaseEvent(self, event):
        self._drag_pos = QPoint()
        self._resize_edge = None

    def mouseDoubleClickEvent(self, event):
        if event.position().y() < 44:
            self._toggle_maximize()
