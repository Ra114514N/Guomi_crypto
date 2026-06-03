"""Animation helpers and small custom widgets for dynamic UI feedback."""

import math

from PySide6.QtCore import (
    Qt, QPropertyAnimation, QEasingCurve, Property, QObject,
)
from PySide6.QtGui import QColor, QPainter, QBrush
from PySide6.QtWidgets import (
    QWidget, QGraphicsDropShadowEffect, QGraphicsOpacityEffect,
)


def add_drop_shadow(widget: QWidget, *, blur: int = 28, dx: int = 0,
                    dy: int = 6, alpha: int = 70) -> QGraphicsDropShadowEffect:
    """Apply a soft drop shadow to a widget. Returns the effect for tuning."""
    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(blur)
    effect.setOffset(dx, dy)
    effect.setColor(QColor(0, 0, 0, alpha))
    widget.setGraphicsEffect(effect)
    return effect


def fade_in(widget: QWidget, duration: int = 220) -> QPropertyAnimation:
    """Fade a widget in from transparent to opaque."""
    effect = QGraphicsOpacityEffect(widget)
    widget.setGraphicsEffect(effect)
    anim = QPropertyAnimation(effect, b"opacity", widget)
    anim.setDuration(duration)
    anim.setStartValue(0.0)
    anim.setEndValue(1.0)
    anim.setEasingCurve(QEasingCurve.OutCubic)
    anim.start(QPropertyAnimation.DeleteWhenStopped)
    return anim


class BusyDot(QWidget):
    """Pulsing dot used to signal ongoing background work.

    Renders a soft circular glow plus an inner dot whose radius/opacity
    oscillate via a sine-driven property animation.
    """

    def __init__(self, color: str = "#2563eb", diameter: int = 10, parent=None):
        super().__init__(parent)
        self._base_color = QColor(color)
        self._diameter = diameter
        self._phase = 0.0          # 0..1 driven by the animation
        self._scale = 1.0          # derived
        self._opacity = 1.0        # derived
        self.setFixedSize(diameter + 10, diameter + 10)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.hide()

        self._anim = QPropertyAnimation(self, b"pulse_value", self)
        self._anim.setDuration(1200)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setLoopCount(-1)
        self._anim.setEasingCurve(QEasingCurve.Linear)

    # ── Public API ─────────────────────────────────────────────

    def set_color(self, color: str) -> None:
        self._base_color = QColor(color)
        self.update()

    def start(self) -> None:
        self.show()
        if self._anim.state() != QPropertyAnimation.Running:
            self._anim.start()

    def stop(self) -> None:
        self._anim.stop()
        self.hide()

    # ── Property animation hook ───────────────────────────────

    def _get_pulse(self) -> float:
        return self._phase

    def _set_pulse(self, v: float) -> None:
        self._phase = v
        s = math.sin(v * math.pi)            # 0 → 1 → 0 over a single loop
        self._scale = 0.78 + 0.34 * s        # 0.78 ↔ 1.12
        self._opacity = 0.50 + 0.50 * s      # 0.50 ↔ 1.00
        self.update()

    pulse_value = Property(float, _get_pulse, _set_pulse)

    # ── Painting ──────────────────────────────────────────────

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        cx = self.width() / 2
        cy = self.height() / 2

        # Outer halo
        halo = QColor(self._base_color)
        halo.setAlphaF(0.20 * self._opacity)
        painter.setBrush(QBrush(halo))
        painter.setPen(Qt.NoPen)
        rg = self._diameter * 0.95 * self._scale
        painter.drawEllipse(int(cx - rg), int(cy - rg), int(rg * 2), int(rg * 2))

        # Solid core
        core = QColor(self._base_color)
        core.setAlphaF(min(1.0, 0.85 + 0.15 * self._opacity))
        painter.setBrush(QBrush(core))
        r = self._diameter / 2 * (0.85 + 0.15 * self._scale)
        painter.drawEllipse(int(cx - r), int(cy - r), int(r * 2), int(r * 2))


class StatusIndicator(QWidget):
    """A static, three-state status dot (idle / running / ok / error)."""

    IDLE = "idle"
    RUNNING = "running"
    OK = "ok"
    ERROR = "error"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(14, 14)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self._state = self.IDLE
        self._colors = {
            self.IDLE: QColor("#9ca3af"),
            self.RUNNING: QColor("#2563eb"),
            self.OK: QColor("#16a34a"),
            self.ERROR: QColor("#dc2626"),
        }

    def set_colors(self, *, idle: str, running: str, ok: str, error: str) -> None:
        self._colors = {
            self.IDLE: QColor(idle),
            self.RUNNING: QColor(running),
            self.OK: QColor(ok),
            self.ERROR: QColor(error),
        }
        self.update()

    def set_state(self, state: str) -> None:
        if state not in (self.IDLE, self.RUNNING, self.OK, self.ERROR):
            state = self.IDLE
        self._state = state
        self.update()

    def state(self) -> str:
        return self._state

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        color = self._colors.get(self._state, self._colors[self.IDLE])

        # halo
        halo = QColor(color)
        halo.setAlphaF(0.25)
        painter.setBrush(QBrush(halo))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(1, 1, 12, 12)

        # core
        painter.setBrush(QBrush(color))
        painter.drawEllipse(4, 4, 6, 6)


class BrandMark(QWidget):
    """Small painted brand badge for the title bar — a layered diamond."""

    def __init__(self, color: str = "#2563eb", parent=None):
        super().__init__(parent)
        self._color = QColor(color)
        self.setFixedSize(18, 18)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)

    def set_color(self, color: str) -> None:
        self._color = QColor(color)
        self.update()

    def paintEvent(self, event):
        from PySide6.QtGui import QPolygonF
        from PySide6.QtCore import QPointF
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        cx, cy = 9.0, 9.0
        outer = QPolygonF([
            QPointF(cx, cy - 7), QPointF(cx + 7, cy),
            QPointF(cx, cy + 7), QPointF(cx - 7, cy),
        ])
        inner = QPolygonF([
            QPointF(cx, cy - 3.2), QPointF(cx + 3.2, cy),
            QPointF(cx, cy + 3.2), QPointF(cx - 3.2, cy),
        ])
        soft = QColor(self._color)
        soft.setAlphaF(0.30)
        painter.setBrush(QBrush(soft))
        painter.setPen(Qt.NoPen)
        painter.drawPolygon(outer)
        painter.setBrush(QBrush(self._color))
        painter.drawPolygon(inner)
