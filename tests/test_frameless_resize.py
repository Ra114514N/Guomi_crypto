from PySide6.QtCore import QPoint, Qt

from gui.frameless_resize import cursor_shape_for_edges, edge_flags_at


def test_edge_flags_detect_window_borders():
    size = (100, 80)

    assert edge_flags_at(QPoint(0, 0), size, 12) == (True, False, True, False)
    assert edge_flags_at(QPoint(99, 79), size, 12) == (False, True, False, True)
    assert edge_flags_at(QPoint(50, 40), size, 12) == (False, False, False, False)


def test_cursor_shape_for_resize_edges():
    assert cursor_shape_for_edges((True, False, True, False)) == Qt.SizeFDiagCursor
    assert cursor_shape_for_edges((False, True, True, False)) == Qt.SizeBDiagCursor
    assert cursor_shape_for_edges((True, False, False, False)) == Qt.SizeHorCursor
    assert cursor_shape_for_edges((False, False, True, False)) == Qt.SizeVerCursor
    assert cursor_shape_for_edges((False, False, False, False)) == Qt.ArrowCursor
