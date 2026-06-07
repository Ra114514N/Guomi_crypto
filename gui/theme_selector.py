"""Theme selector dialog with color scheme grid and live swatches."""

from PySide6.QtCore import Qt, Signal, QPoint
from PySide6.QtGui import QFont, QPainter, QColor, QBrush
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QGridLayout, QCheckBox, QWidget,
)

from gui import styles
from gui.effects import add_drop_shadow, fade_in


class _SwatchRow(QWidget):
    """A horizontal strip of small color squares showing a theme's palette."""

    def __init__(self, colors: list[str], parent=None):
        super().__init__(parent)
        self._colors = [QColor(c) for c in colors]
        self.setFixedHeight(10)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        n = len(self._colors)
        if n == 0:
            return
        w = self.width()
        h = self.height()
        cell = max(8, min(14, w // n))
        x0 = (w - cell * n) // 2
        for i, col in enumerate(self._colors):
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(col))
            painter.drawRoundedRect(x0 + i * cell, 0, cell - 2, h, 2, 2)


class _ThemeCard(QPushButton):
    """A card-style button showing theme name + swatches."""

    def __init__(self, name: str, colors: list[str], selected: bool,
                 dark_preview: bool, parent=None):
        super().__init__(parent)
        self.theme_name = name
        self.setFixedHeight(62)
        self.setCursor(Qt.PointingHandCursor)

        # Use the theme's own light/dark accent for the border when selected
        self._accent = colors[0]
        bg = colors[1]      # surface-ish
        text_col = colors[2]
        border = colors[3]

        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 6, 8, 6)
        outer.setSpacing(3)

        top = QHBoxLayout()
        top.setSpacing(6)
        top.setContentsMargins(0, 0, 0, 0)
        dot = QLabel()
        dot.setFixedSize(8, 8)
        dot.setStyleSheet(
            f"background-color: {self._accent}; border-radius: 4px;"
        )
        top.addWidget(dot)
        name_label = QLabel(name)
        name_label.setFont(QFont(styles.current_font_family, 10, QFont.DemiBold))
        name_label.setStyleSheet(f"color: {text_col}; background: transparent;")
        top.addWidget(name_label)
        top.addStretch()
        if dark_preview:
            tag = QLabel("DK")
            tag.setStyleSheet(
                f"color: {text_col}; background: transparent; "
                f"font-size: 9px; opacity: 0.6;"
            )
            top.addWidget(tag)
        outer.addLayout(top)

        swatches = _SwatchRow(colors)
        outer.addWidget(swatches)

        border_style = (
            f"2px solid {self._accent}" if selected else f"1px solid {border}"
        )
        self.setStyleSheet(
            f"QPushButton {{"
            f"  background-color: {bg};"
            f"  border: {border_style};"
            f"  border-radius: 8px;"
            f"  text-align: left;"
            f"}}"
            f"QPushButton:hover {{"
            f"  border: 2px solid {self._accent};"
            f"}}"
        )


class ThemeSelectorDialog(QDialog):
    theme_selected = Signal(str, bool)

    def __init__(self, current_theme: str, is_dark: bool, parent=None):
        super().__init__(parent)
        self._drag_pos = QPoint()
        self._current_theme = current_theme
        self._is_dark = is_dark

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)

        themes = styles.get_available_themes()
        n_themes = len(themes)
        cols = 2
        rows = (n_themes + cols - 1) // cols
        # Size scales with theme count
        width = 400
        height = 130 + rows * 72
        self.setFixedSize(width, height)

        self._container = QWidget(self)
        self._container.setGeometry(8, 8, width - 16, height - 16)
        self._build_ui()
        add_drop_shadow(self._container, blur=30, dy=8, alpha=110)
        fade_in(self._container, duration=180)

    def _build_ui(self):
        # Apply current theme colors to the container
        self._container.setStyleSheet(
            f"background-color: {styles.surface_color};"
            f"border: 1px solid {styles.border_subtle};"
            f"border-radius: 10px;"
        )

        layout = QVBoxLayout(self._container)
        layout.setContentsMargins(16, 12, 16, 14)
        layout.setSpacing(10)

        # Header
        header = QHBoxLayout()
        title = QLabel("选择主题")
        title.setStyleSheet(
            f"color: {styles.text_color}; font-size: 13px; "
            f"font-weight: 700; border: none; background: transparent;"
        )
        header.addWidget(title)
        header.addStretch()

        close_btn = QPushButton("×")
        close_btn.setFixedSize(22, 22)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet(
            f"QPushButton {{ border: none; font-size: 15px; "
            f"  color: {styles.text_muted}; background: transparent; }}"
            f"QPushButton:hover {{ color: {styles.error_color}; }}"
        )
        close_btn.clicked.connect(self.close)
        header.addWidget(close_btn)
        layout.addLayout(header)

        # Grid of theme cards
        grid = QGridLayout()
        grid.setSpacing(10)
        themes = styles.get_available_themes()
        for i, name in enumerate(themes):
            card = self._theme_card(name)
            grid.addWidget(card, i // 2, i % 2)
        layout.addLayout(grid)

        # Dark mode toggle
        self.dark_check = QCheckBox("深色模式")
        self.dark_check.setChecked(self._is_dark)
        self.dark_check.setCursor(Qt.PointingHandCursor)
        self.dark_check.setStyleSheet(
            f"QCheckBox {{ color: {styles.text_color}; "
            f"  background: transparent; font-size: 12px; }}"
            f"QCheckBox::indicator {{"
            f"  width: 16px; height: 16px; border-radius: 4px;"
            f"  border: 1px solid {styles.border_color};"
            f"  background-color: {styles.button_bg_color};"
            f"}}"
            f"QCheckBox::indicator:checked {{"
            f"  background-color: {styles.accent_color};"
            f"  border: 1px solid {styles.accent_color};"
            f"}}"
            f"QCheckBox::indicator:hover {{"
            f"  border: 1px solid {styles.accent_color};"
            f"}}"
        )
        self.dark_check.toggled.connect(self._on_dark_toggled)
        layout.addWidget(self.dark_check)

        layout.addStretch()

    def _theme_card(self, name: str) -> QPushButton:
        scheme = styles.get_scheme(name, self._is_dark)
        palette = [
            scheme.get("accent_color", "#2563eb"),
            scheme.get("surface_color", scheme.get("background_color", "#ffffff")),
            scheme.get("text_color", "#1f2937"),
            scheme.get("border_color", "#d1d5db"),
            scheme.get("success_color", "#16a34a"),
            scheme.get("warning_color", "#d97706"),
            scheme.get("error_color", "#dc2626"),
            scheme.get("mono_color", "#7c3aed"),
        ]
        card = _ThemeCard(name, palette,
                          selected=(name == self._current_theme),
                          dark_preview=self._is_dark)
        card.clicked.connect(lambda checked=False, n=name: self._select_theme(n))
        return card

    def _select_theme(self, name: str):
        self._current_theme = name
        self.theme_selected.emit(name, self._is_dark)
        self.close()

    def _on_dark_toggled(self, checked: bool):
        self._is_dark = checked
        self.theme_selected.emit(self._current_theme, self._is_dark)
        self.close()

    @staticmethod
    def _clear_layout(layout):
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = (event.globalPosition().toPoint()
                              - self.frameGeometry().topLeft())

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton and not self._drag_pos.isNull():
            self.move(event.globalPosition().toPoint() - self._drag_pos)
