"""TimelineView — scrollable container that manages a vertical flow of StepCards.

Usage:
    timeline = TimelineView()
    timeline.add_step(1, "生成会话秘密", {"Session ID": "...", "Secret": "..."}, state="success")
    timeline.clear_steps()
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QScrollArea, QLabel,
)

from gui import styles
from gui.step_card import StepCardWidget


class TimelineView(QWidget):
    """A vertical scroll area that hosts StepCardWidgets with staggered entrance."""

    def __init__(self, parent=None, auto_scroll: bool = True):
        super().__init__(parent)
        self._cards: list[StepCardWidget] = []
        self._entrance_delay_base = 80
        self._auto_scroll = auto_scroll

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet(
            "QScrollArea { border: none; background: transparent; }"
        )
        layout.addWidget(self._scroll)

        self._container = QWidget()
        self._container.setStyleSheet("background: transparent;")
        self._card_layout = QVBoxLayout(self._container)
        self._card_layout.setContentsMargins(12, 12, 12, 12)
        self._card_layout.setSpacing(10)

        # Placeholder shown when empty
        self._placeholder = QLabel("等待指令…")
        self._placeholder.setAlignment(Qt.AlignCenter)
        self._placeholder.setStyleSheet(
            f"color: {styles.text_muted}; font-size: 14px; "
            f"border: 2px dashed {styles.card_border}; border-radius: 12px; "
            f"padding: 60px 20px; background: transparent;"
        )
        self._card_layout.addWidget(self._placeholder)

        # Bottom spacer keeps cards top-aligned without setAlignment
        self._card_layout.addStretch(1)

        self._scroll.setWidget(self._container)

    # ── Public API ─────────────────────────────────────────────

    def add_step(
        self,
        step_number: int,
        title: str,
        data: dict[str, str] | None = None,
        state: str = StepCardWidget.STATE_SUCCESS,
        animate: bool = True,
    ) -> StepCardWidget:
        """Add a new step card to the timeline."""
        if self._placeholder.isVisible():
            self._placeholder.hide()

        card = StepCardWidget(step_number, title, parent=self._container)
        card.set_state(state)
        if data:
            card.set_data_rows(data, animate=animate)

        # Insert before the bottom stretch
        insert_idx = self._card_layout.count() - 1
        self._card_layout.insertWidget(insert_idx, card)
        self._cards.append(card)

        if animate:
            card.animate_entrance(delay=self._entrance_delay_base)

        if self._auto_scroll:
            QTimer.singleShot(150, self._scroll_to_bottom)
        return card

    def update_last_card_state(self, state: str) -> None:
        """Update the state of the most recently added card."""
        if self._cards:
            self._cards[-1].set_state(state)

    def clear_steps(self) -> None:
        """Remove all cards and show placeholder."""
        for card in self._cards:
            card.setParent(None)
            card.deleteLater()
        self._cards.clear()
        self._placeholder.show()

    def refresh_styles(self) -> None:
        self._placeholder.setStyleSheet(
            f"color: {styles.text_muted}; font-size: 14px; "
            f"border: 2px dashed {styles.card_border}; border-radius: 12px; "
            f"padding: 60px 20px; background: transparent;"
        )
        for card in self._cards:
            card.refresh_styles()

    # ── Internal ───────────────────────────────────────────────

    def _scroll_to_bottom(self):
        bar = self._scroll.verticalScrollBar()
        bar.setValue(bar.maximum())
