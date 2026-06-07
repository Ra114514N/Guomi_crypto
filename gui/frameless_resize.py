from __future__ import annotations

from PySide6.QtCore import QPoint, QEvent, QObject, Qt
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QWidget


EdgeFlags = tuple[bool, bool, bool, bool]


def edge_flags_at(pos: QPoint, size, edge: int) -> EdgeFlags:
    """Return left/right/top/bottom flags for a point inside a window."""
    width = size.width() if hasattr(size, "width") else size[0]
    height = size.height() if hasattr(size, "height") else size[1]
    x, y = pos.x(), pos.y()
    return x < edge, x > width - edge, y < edge, y > height - edge


def cursor_shape_for_edges(edges: EdgeFlags) -> Qt.CursorShape:
    left, right, top, bottom = edges
    if (left and top) or (right and bottom):
        return Qt.SizeFDiagCursor
    if (right and top) or (left and bottom):
        return Qt.SizeBDiagCursor
    if left or right:
        return Qt.SizeHorCursor
    if top or bottom:
        return Qt.SizeVerCursor
    return Qt.ArrowCursor


class ResizeCursorFilter(QObject):
    """Keeps resize cursors correct even when child widgets cover the edges."""

    def __init__(self, window: QWidget, edge: int):
        super().__init__(window)
        self._window = window
        self._edge = edge
        self._overridden = {}

    def eventFilter(self, watched, event):
        event_type = event.type()
        if event_type == QEvent.ChildAdded:
            child = event.child()
            if isinstance(child, QWidget):
                self.install_recursively(child)
        elif event_type in (QEvent.MouseMove, QEvent.HoverMove, QEvent.Enter):
            self.update_cursor(watched)
        elif event_type in (QEvent.Leave, QEvent.WindowDeactivate):
            self.update_cursor(watched)
        return super().eventFilter(watched, event)

    def install_recursively(self, root: QWidget):
        for widget in [root, *root.findChildren(QWidget)]:
            widget.setMouseTracking(True)
            widget.installEventFilter(self)

    def update_cursor(self, watched=None):
        if self._window.isMaximized() or getattr(self._window, "_resize_edge", None):
            return

        global_pos = QCursor.pos()
        local_pos = self._window.mapFromGlobal(global_pos)

        if not self._window.rect().contains(local_pos):
            self._restore_overridden_cursors()
            return

        cursor_shape = cursor_shape_for_edges(
            edge_flags_at(local_pos, self._window.size(), self._edge)
        )
        self._window.setCursor(cursor_shape)
        if cursor_shape == Qt.ArrowCursor:
            self._restore_overridden_cursors()
        elif isinstance(watched, QWidget):
            self._restore_overridden_cursors(unset_window=False)
            self._override_widget_cursor(watched, cursor_shape)

    def _override_widget_cursor(self, widget: QWidget, cursor_shape: Qt.CursorShape):
        if widget not in self._overridden:
            self._overridden[widget] = (
                widget.testAttribute(Qt.WA_SetCursor),
                QCursor(widget.cursor()),
            )
        widget.setCursor(cursor_shape)

    def _restore_overridden_cursors(self, unset_window: bool = True):
        if unset_window:
            self._window.unsetCursor()
        for widget, (had_cursor, cursor) in list(self._overridden.items()):
            if had_cursor:
                widget.setCursor(cursor)
            else:
                widget.unsetCursor()
        self._overridden.clear()
