from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QFontMetrics
from PySide6.QtWidgets import QLabel


class ElidedLabel(QLabel):
    """Label that keeps a full tooltip while drawing shortened visible text."""

    def __init__(self, text: str = "", parent=None):
        super().__init__(parent)
        self._full_text = ""
        self.setText(text)

    def setText(self, text: str):
        self._full_text = text
        super().setText(text)
        self._refresh_elision()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._refresh_elision()

    def setFont(self, font: QFont):
        super().setFont(font)
        self._refresh_elision()

    def _refresh_elision(self):
        if not self._full_text:
            return
        metrics = QFontMetrics(self.font())
        elided = metrics.elidedText(self._full_text, Qt.ElideRight, max(0, self.width()))
        super().setText(elided)
