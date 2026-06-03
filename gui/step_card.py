"""StepCardWidget — a single protocol step rendered as an animated card.

States: pending, running, success, error.
Entrance animation: fade-in (geometry animation conflicts with layouts).

Data layout is now smart-routed:
- Step 5 (verification): three parallel capsule badges
- Step 6 (conclusion): a banner
- Other steps: short data → horizontal MetaCells, long data → LongDataRow
"""

from __future__ import annotations

from PySide6.QtCore import (
    Qt, QPropertyAnimation, QEasingCurve, QTimer,
)
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel,
    QGraphicsOpacityEffect, QWidget, QSizePolicy,
)

from gui import styles
from gui.data_widgets import (
    MetaCell, LongDataRow, VerifyCapsuleRow, ConclusionBanner,
)


# Threshold above which a value is rendered as a full-width LongDataRow
LONG_VALUE_THRESHOLD = 28


class StepCardWidget(QFrame):
    """A card representing one protocol step in the timeline."""

    STATE_PENDING = "pending"
    STATE_RUNNING = "running"
    STATE_SUCCESS = "success"
    STATE_ERROR = "error"

    def __init__(self, step_number: int, title: str, parent=None):
        super().__init__(parent)
        self.setObjectName("StepCard")
        self._step_number = step_number
        self._title = title
        self._state = self.STATE_PENDING

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self._build_ui()
        self._apply_card_border()

        self._opacity_effect = QGraphicsOpacityEffect(self)
        self._opacity_effect.setOpacity(0.0)
        self.setGraphicsEffect(self._opacity_effect)

    def _build_ui(self):
        self.setContentsMargins(0, 0, 0, 0)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(12)

        # Header row: status icon + step title
        header = QHBoxLayout()
        header.setSpacing(12)

        self._status_label = QLabel()
        self._status_label.setFixedWidth(22)
        self._status_label.setAlignment(Qt.AlignCenter)
        self._update_status_icon()
        header.addWidget(self._status_label)

        self._title_label = QLabel(f"{self._step_number}. {self._title}")
        self._title_label.setFont(QFont(styles.current_font_family, 12, QFont.Bold))
        self._title_label.setStyleSheet(
            "color: #FFFFFF; background: transparent;"
        )
        header.addWidget(self._title_label, 1)

        layout.addLayout(header)

        # Data area
        self._data_widget = QWidget()
        self._data_widget.setStyleSheet("background: transparent;")
        self._data_layout = QVBoxLayout(self._data_widget)
        self._data_layout.setContentsMargins(34, 4, 0, 0)
        self._data_layout.setSpacing(10)
        layout.addWidget(self._data_widget)

    def _apply_card_border(self):
        border_color = styles.card_border
        if self._state == self.STATE_RUNNING:
            border_color = styles.warning_color
        elif self._state == self.STATE_ERROR:
            border_color = styles.error_color

        self.setStyleSheet(
            f"QFrame#StepCard {{"
            f"  background-color: {styles.card_bg};"
            f"  border: 1px solid {border_color};"
            f"  border-radius: 10px;"
            f"}}"
        )

    # ── Public API ─────────────────────────────────────────────

    def set_state(self, state: str) -> None:
        self._state = state
        self._update_status_icon()
        self._apply_card_border()

    def set_data_rows(self, data: dict[str, str], animate: bool = True) -> None:
        """Smart-route data into appropriate widgets based on step + content."""
        # Clear existing
        self._clear_data_layout()

        if not data:
            return

        # Step 5: parallel verification capsules
        if self._step_number == 5:
            self._render_verification(data, animate=animate)
            return

        # Step 6: conclusion banner
        if self._step_number == 6:
            self._render_conclusion(data)
            return

        # Default: bucket short vs. long data
        short_items: list[tuple[str, str]] = []
        long_items: list[tuple[str, str]] = []
        for key, value in data.items():
            value = str(value)
            if len(value) > LONG_VALUE_THRESHOLD:
                long_items.append((key, value))
            else:
                short_items.append((key, value))

        # Short items: horizontal row of MetaCells
        if short_items:
            row = QHBoxLayout()
            row.setSpacing(28)
            row.setContentsMargins(0, 0, 0, 0)
            for key, value in short_items:
                row.addWidget(MetaCell(key, value))
            row.addStretch()
            self._data_layout.addLayout(row)

        # Long items: each on its own LongDataRow
        for key, value in long_items:
            self._data_layout.addWidget(LongDataRow(key, value))

    def add_data_row(self, key: str, value: str) -> None:
        """Legacy single-row entry; routes through set_data_rows."""
        # Maintain incremental adds by accumulating into a dict
        if not hasattr(self, "_acc_data"):
            self._acc_data = {}
        self._acc_data[key] = value
        self.set_data_rows(self._acc_data)

    def animate_entrance(self, delay: int = 0) -> None:
        QTimer.singleShot(delay, self._run_entrance)

    def refresh_styles(self) -> None:
        self._apply_card_border()
        self._title_label.setStyleSheet(
            "color: #FFFFFF; background: transparent;"
        )
        self._update_status_icon()

    # ── Renderers ──────────────────────────────────────────────

    def _render_verification(self, data: dict[str, str], animate: bool = True) -> None:
        """Step 5 — three parallel capsules."""
        items: list[tuple[str, bool]] = []
        for key, value in data.items():
            ok = ("✓" in str(value)) or ("通过" in str(value))
            items.append((key, ok))
        self._data_layout.addWidget(VerifyCapsuleRow(items, animate=animate))

    def _render_conclusion(self, data: dict[str, str]) -> None:
        """Step 6 — banner with conclusion + supplementary info."""
        conclusion_text = data.get("结论", "")
        ok = "通过" in conclusion_text and "失败" not in conclusion_text

        if conclusion_text:
            self._data_layout.addWidget(ConclusionBanner(conclusion_text, ok))

        # Supplementary fields (e.g., output path) as MetaCell row
        extras = {k: v for k, v in data.items() if k != "结论"}
        if extras:
            row = QHBoxLayout()
            row.setSpacing(28)
            for key, value in extras.items():
                row.addWidget(MetaCell(key, str(value)))
            row.addStretch()
            self._data_layout.addLayout(row)

    # ── Internal ───────────────────────────────────────────────

    def _clear_data_layout(self):
        while self._data_layout.count():
            item = self._data_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
                continue
            sub = item.layout()
            if sub is not None:
                self._clear_layout_recursive(sub)

    def _clear_layout_recursive(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
                continue
            sub = item.layout()
            if sub is not None:
                self._clear_layout_recursive(sub)

    def _update_status_icon(self):
        icons = {
            self.STATE_PENDING: ("⏳", "#767C8D"),
            self.STATE_RUNNING: ("◉", styles.warning_color),
            self.STATE_SUCCESS: ("✓", styles.success_color),
            self.STATE_ERROR: ("✗", styles.error_color),
        }
        icon, color = icons.get(self._state, icons[self.STATE_PENDING])
        self._status_label.setText(icon)
        self._status_label.setStyleSheet(
            f"color: {color}; font-size: 16px; font-weight: bold; background: transparent;"
        )

    def _run_entrance(self):
        fade = QPropertyAnimation(self._opacity_effect, b"opacity", self)
        fade.setDuration(420)
        fade.setStartValue(0.0)
        fade.setEndValue(1.0)
        fade.setEasingCurve(QEasingCurve.OutCubic)
        fade.finished.connect(self._remove_opacity_effect)
        fade.start(QPropertyAnimation.DeleteWhenStopped)

    def _remove_opacity_effect(self):
        if self._opacity_effect is not None:
            self.setGraphicsEffect(None)
            self._opacity_effect = None
