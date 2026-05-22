"""Theme selector dialog with color scheme grid."""

from PySide6.QtCore import Qt, Signal, QPoint
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QGridLayout, QCheckBox, QWidget,
)

from gui import styles


class ThemeSelectorDialog(QDialog):
    theme_selected = Signal(str, bool)

    def __init__(self, current_theme: str, is_dark: bool, parent=None):
        super().__init__(parent)
        self._drag_pos = QPoint()
        self._current_theme = current_theme
        self._is_dark = is_dark

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(320, 220)

        self._build_ui()

    def _build_ui(self):
        container = QWidget(self)
        container.setGeometry(0, 0, 320, 220)
        container.setStyleSheet(
            f"background-color: {styles.background_color};"
            f"border: 1px solid {styles.border_color};"
            "border-radius: 8px;"
        )

        layout = QVBoxLayout(container)
        layout.setContentsMargins(12, 10, 12, 12)
        layout.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel("选择主题")
        title.setStyleSheet(f"color: {styles.text_color}; font-size: 13px; font-weight: bold; border: none;")
        header.addWidget(title)
        header.addStretch()

        close_btn = QPushButton("×")
        close_btn.setFixedSize(20, 20)
        close_btn.setStyleSheet(
            "QPushButton { border: none; font-size: 14px; color: gray; }"
            "QPushButton:hover { color: red; }"
        )
        close_btn.clicked.connect(self.close)
        header.addWidget(close_btn)
        layout.addLayout(header)

        grid = QGridLayout()
        grid.setSpacing(8)
        themes = styles.get_available_themes()
        for i, name in enumerate(themes):
            btn = self._theme_button(name)
            grid.addWidget(btn, i // 3, i % 3)
        layout.addLayout(grid)

        self.dark_check = QCheckBox("深色模式")
        self.dark_check.setChecked(self._is_dark)
        self.dark_check.setStyleSheet(f"color: {styles.text_color}; border: none;")
        self.dark_check.toggled.connect(self._on_dark_toggled)
        layout.addWidget(self.dark_check)

        layout.addStretch()

    def _theme_button(self, name: str) -> QPushButton:
        scheme = styles.color_schemes[name]["light"]
        bg = scheme["button_bg_color"]
        btn = QPushButton(name)
        btn.setFixedHeight(30)
        selected = "2px solid #4a90d9" if name == self._current_theme else f"1px solid {styles.border_color}"
        btn.setStyleSheet(
            f"QPushButton {{ background-color: {bg}; border: {selected}; border-radius: 4px;"
            f"  color: {scheme['button_text_color']}; font-size: 11px; padding: 2px 8px; }}"
            f"QPushButton:hover {{ border: 2px solid #4a90d9; }}"
        )
        btn.clicked.connect(lambda checked, n=name: self._select_theme(n))
        return btn

    def _select_theme(self, name: str):
        self._current_theme = name
        self.theme_selected.emit(name, self._is_dark)
        self.close()

    def _on_dark_toggled(self, checked: bool):
        self._is_dark = checked
        self.theme_selected.emit(self._current_theme, self._is_dark)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton and not self._drag_pos.isNull():
            self.move(event.globalPosition().toPoint() - self._drag_pos)
