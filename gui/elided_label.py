from __future__ import annotations

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont, QFontMetrics
from PySide6.QtWidgets import QLabel


class ElidedLabel(QLabel):
    """Label that keeps a full tooltip while drawing shortened visible text.

    h_padding: horizontal stylesheet padding to subtract from the available
    width when eliding (QLabel.width() includes padding drawn by QSS).

    compact=True clamps size hints to a tiny width so a long value can never
    inflate the parent layout — the label fills whatever space the layout
    grants and elides to fit it. Leave False for title-style labels that
    should claim their natural width from the layout.
    """

    _MIN_HINT_WIDTH = 48

    def __init__(self, text: str = "", parent=None, h_padding: int = 0,
                 compact: bool = False):
        super().__init__(parent)
        self._full_text = ""
        self._h_padding = h_padding
        self._compact = compact
        self.setText(text)

    def sizeHint(self) -> QSize:
        hint = super().sizeHint()
        if self._compact:
            return QSize(self._MIN_HINT_WIDTH, hint.height())
        return hint

    def minimumSizeHint(self) -> QSize:
        hint = super().minimumSizeHint()
        if self._compact:
            return QSize(self._MIN_HINT_WIDTH, hint.height())
        return hint

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
        available = max(0, self.width() - self._h_padding)
        elided = metrics.elidedText(self._full_text, Qt.ElideRight, available)
        super().setText(elided)
