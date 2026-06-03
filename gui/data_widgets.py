"""Data display widgets for StepCard — implements the SecOps dashboard aesthetic.

Components:
- MetaCell: Stacked key/value for short metadata (algo, length, etc.)
- LongDataRow: Full-width row for long crypto strings with ellipsis + hover-copy
- VerifyCapsule: A single security verification capsule badge
- VerifyCapsuleRow: Three capsules side-by-side for step 5
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QWidget, QLabel, QHBoxLayout, QVBoxLayout, QPushButton,
    QFrame, QSizePolicy,
)

from gui import styles


def _is_mono_value(value: str) -> bool:
    """Heuristic: treat as mono/crypto data if long, base64-ish, hex-ish, or contains ellipsis."""
    if "..." in value:
        return True
    if len(value) >= 20:
        return True
    stripped = value.replace(" ", "").replace("-", "").replace("_", "")
    if stripped and all(c in "0123456789abcdefABCDEF" for c in stripped):
        return True
    return False


class MetaCell(QWidget):
    """A short metadata cell: muted key on top, primary value below.

    Used for compact horizontal layout of short data points like
    "算法: SM4-GCM", "密文长度: 943 字节" etc.
    """

    def __init__(self, key: str, value: str, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)

        self._key_label = QLabel(key)
        self._key_label.setStyleSheet(
            f"color: #767C8D; font-size: 11px; font-weight: 400; "
            f"background: transparent; font-family: {styles.current_font_family};"
        )
        layout.addWidget(self._key_label)

        is_mono = _is_mono_value(value)
        self._value_label = QLabel(value)
        self._value_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        if is_mono:
            self._value_label.setStyleSheet(
                f"color: {styles.mono_color};"
                f"background-color: {styles.mono_bg};"
                f"border-radius: 4px;"
                f"padding: 2px 8px;"
                f"font-family: {styles.mono_font_family};"
                f"font-size: 13px;"
                f"font-weight: 500;"
            )
            self._value_label.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
        else:
            self._value_label.setStyleSheet(
                f"color: #FFFFFF;"
                f"font-family: {styles.current_font_family};"
                f"font-size: 14px;"
                f"font-weight: 600;"
                f"background: transparent;"
            )
        layout.addWidget(self._value_label, alignment=Qt.AlignLeft)


class LongDataRow(QWidget):
    """A full-width row for long crypto strings.

    Layout: muted key label (left, fixed width) + truncated mono chip (expanding)
    + hover-fade-in copy button.
    """

    def __init__(self, key: str, full_value: str, max_chars: int = 56, parent=None):
        super().__init__(parent)
        self._full_value = full_value
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # Key on left
        self._key_label = QLabel(key)
        self._key_label.setFixedWidth(86)
        self._key_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self._key_label.setStyleSheet(
            f"color: #767C8D; font-size: 11px; font-weight: 400; "
            f"background: transparent; font-family: {styles.current_font_family};"
        )
        layout.addWidget(self._key_label)

        # Truncated value chip
        display = full_value
        if len(full_value) > max_chars:
            display = full_value[:max_chars] + "…"
        self._value_label = QLabel(display)
        self._value_label.setToolTip(full_value)
        self._value_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self._value_label.setStyleSheet(
            f"color: {styles.mono_color};"
            f"background-color: {styles.mono_bg};"
            f"border-radius: 4px;"
            f"padding: 4px 10px;"
            f"font-family: {styles.mono_font_family};"
            f"font-size: 13px;"
            f"font-weight: 500;"
        )
        self._value_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout.addWidget(self._value_label, 1)

        # Hover-only copy button — use stylesheet color transitions instead
        # of QGraphicsOpacityEffect to keep the row stable inside QScrollArea.
        self._copy_btn = QPushButton("📋 复制")
        self._copy_btn.setCursor(Qt.PointingHandCursor)
        self._copy_btn.setFixedHeight(24)
        self._copy_btn.clicked.connect(self._on_copy)
        layout.addWidget(self._copy_btn)

        self._dim_style = (
            f"QPushButton {{"
            f"  color: rgba(118, 124, 141, 0);"
            f"  background-color: transparent;"
            f"  border: 1px solid transparent;"
            f"  border-radius: 4px;"
            f"  padding: 2px 8px;"
            f"  font-size: 11px;"
            f"  font-family: {styles.current_font_family};"
            f"}}"
        )
        self._hot_style = (
            f"QPushButton {{"
            f"  color: {styles.mono_color};"
            f"  background-color: transparent;"
            f"  border: 1px solid {styles.mono_color};"
            f"  border-radius: 4px;"
            f"  padding: 2px 8px;"
            f"  font-size: 11px;"
            f"  font-family: {styles.current_font_family};"
            f"}}"
            f"QPushButton:hover {{"
            f"  background-color: rgba(78, 201, 176, 0.10);"
            f"}}"
        )
        self._copy_btn.setStyleSheet(self._dim_style)

    def enterEvent(self, event):
        self._copy_btn.setStyleSheet(self._hot_style)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._copy_btn.setStyleSheet(self._dim_style)
        super().leaveEvent(event)

    def _on_copy(self):
        QGuiApplication.clipboard().setText(self._full_value)
        original = self._copy_btn.text()
        self._copy_btn.setText("✓ 已复制")
        QTimer.singleShot(1200, lambda: self._copy_btn.setText(original))


class VerifyCapsule(QFrame):
    """A single verification capsule — toggles between dim and bright-green states.

    No QGraphicsOpacityEffect is used: persistent graphics effects glitch when
    a QScrollArea scrolls. The domino entrance is achieved purely by delaying
    the dim→lit state transition.
    """

    STATE_PENDING = "pending"
    STATE_PASS = "pass"
    STATE_FAIL = "fail"

    def __init__(self, label: str, parent=None):
        super().__init__(parent)
        self.setObjectName("VerifyCapsule")
        self._label_text = label
        self._state = self.STATE_PENDING
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setFixedHeight(56)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(10)

        self._icon = QLabel("◯")
        self._icon.setFixedWidth(18)
        self._icon.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._icon)

        self._text = QLabel(label)
        self._text.setStyleSheet(
            f"background: transparent; font-family: {styles.current_font_family};"
        )
        layout.addWidget(self._text, 1)

        self._apply_style()

    def _apply_style(self):
        if self._state == self.STATE_PASS:
            bg = "rgba(16, 185, 129, 0.15)"
            border = styles.success_color
            text_color = styles.success_color
            icon_text = "✓"
        elif self._state == self.STATE_FAIL:
            bg = "rgba(239, 68, 68, 0.15)"
            border = styles.error_color
            text_color = styles.error_color
            icon_text = "✗"
        else:
            bg = styles.mono_bg
            border = styles.card_border
            text_color = "#767C8D"
            icon_text = "◯"

        self.setStyleSheet(
            f"QFrame#VerifyCapsule {{"
            f"  background-color: {bg};"
            f"  border: 1px solid {border};"
            f"  border-radius: 8px;"
            f"}}"
        )
        self._icon.setText(icon_text)
        self._icon.setStyleSheet(
            f"color: {text_color}; font-size: 14px; font-weight: 700; background: transparent;"
        )
        self._text.setStyleSheet(
            f"color: {text_color}; font-size: 13px; font-weight: 600; "
            f"background: transparent; font-family: {styles.current_font_family};"
        )

    def set_state(self, state: str) -> None:
        self._state = state
        self._apply_style()


class VerifyCapsuleRow(QWidget):
    """Three verification capsules, lit up domino-style.

    When animate=True, capsules start in the pending (dim) state and flip to
    their pass/fail state one after another. When False, they render in their
    final state immediately (used for static test boards / re-renders).
    """

    def __init__(self, items: list[tuple[str, bool]], animate: bool = True, parent=None):
        """items: list of (label, ok) tuples."""
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        # Fix the height so QScrollArea doesn't recompute geometry mid-scroll.
        self.setFixedHeight(60)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self._capsules: list[VerifyCapsule] = []
        for label, ok in items:
            cap = VerifyCapsule(label)
            self._capsules.append(cap)
            layout.addWidget(cap, 1)

        if animate:
            # Domino: each capsule flips from dim → lit in sequence.
            for i, (_, ok) in enumerate(items):
                cap = self._capsules[i]
                target = VerifyCapsule.STATE_PASS if ok else VerifyCapsule.STATE_FAIL
                QTimer.singleShot(180 + i * 200,
                                  lambda c=cap, s=target: c.set_state(s))
        else:
            # Render final states immediately.
            for i, (_, ok) in enumerate(items):
                target = VerifyCapsule.STATE_PASS if ok else VerifyCapsule.STATE_FAIL
                self._capsules[i].set_state(target)


class ConclusionBanner(QFrame):
    """A large pass/fail conclusion banner for the final step."""

    def __init__(self, text: str, ok: bool, parent=None):
        super().__init__(parent)
        self.setObjectName("ConclusionBanner")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(12)

        color = styles.success_color if ok else styles.error_color
        bg = "rgba(16, 185, 129, 0.15)" if ok else "rgba(239, 68, 68, 0.15)"
        icon = "🛡️" if ok else "⚠️"

        icon_lbl = QLabel(icon)
        icon_lbl.setStyleSheet("font-size: 20px; background: transparent;")
        layout.addWidget(icon_lbl)

        text_lbl = QLabel(text)
        text_lbl.setWordWrap(True)
        text_lbl.setStyleSheet(
            f"color: {color}; font-size: 15px; font-weight: 700; "
            f"background: transparent; font-family: {styles.current_font_family};"
        )
        layout.addWidget(text_lbl, 1)

        self.setStyleSheet(
            f"QFrame#ConclusionBanner {{"
            f"  background-color: {bg};"
            f"  border: 1px solid {color};"
            f"  border-radius: 8px;"
            f"}}"
        )
