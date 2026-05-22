"""QSS theme system with runtime color scheme switching."""

import json
import sys
from pathlib import Path

from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QApplication

_CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"

# Global color variables
background_color = "rgba(255, 255, 255, 0.95)"
text_color = "#333333"
button_bg_color = "rgba(240, 240, 240, 0.9)"
button_text_color = "#333333"
button_hover_color = "rgba(220, 220, 220, 0.9)"
border_color = "#cccccc"
group_title_bg_color = "rgba(240, 240, 240, 0.9)"
log_bg_color = "rgba(250, 250, 250, 0.95)"
log_text_color = "#333333"
tab_selected_bg = "rgba(255, 255, 255, 1.0)"
tab_unselected_bg = "rgba(230, 230, 230, 0.8)"
current_font_family = "Microsoft YaHei"

# Title bar button colors
theme_button_color = "rgba(255, 223, 186, 0.9)"
minimize_button_color = "rgba(198, 255, 198, 0.9)"
maximize_button_color = "rgba(186, 225, 255, 0.9)"
close_button_color = "rgba(255, 204, 204, 0.9)"

# Pre-composed style strings (populated by update_styles)
main_window_style = ""
button_style = ""
tab_style = ""
group_style = ""
log_style = ""
combobox_style = ""
lineedit_style = ""
textedit_style = ""

# Load color schemes
_style_path = _CONFIG_DIR / "style.json"
color_schemes: dict = {}
if _style_path.exists():
    with open(_style_path, "r", encoding="utf-8") as f:
        color_schemes = json.load(f)


def is_dark_mode() -> bool:
    app = QApplication.instance()
    if app is None:
        return False
    return app.palette().color(QPalette.Window).lightness() < 128


def get_available_themes() -> list[str]:
    return list(color_schemes.keys())


def apply_color_scheme(scheme_name: str, is_dark: bool) -> None:
    global background_color, text_color, button_bg_color, button_text_color
    global button_hover_color, border_color, group_title_bg_color
    global log_bg_color, log_text_color, tab_selected_bg, tab_unselected_bg

    mode = "dark" if is_dark else "light"
    scheme = color_schemes.get(scheme_name, color_schemes["默认"])[mode]

    background_color = scheme["background_color"]
    text_color = scheme["text_color"]
    button_bg_color = scheme["button_bg_color"]
    button_text_color = scheme["button_text_color"]
    button_hover_color = scheme["button_hover_color"]
    border_color = scheme["border_color"]
    group_title_bg_color = scheme["group_title_bg_color"]
    log_bg_color = scheme["log_bg_color"]
    log_text_color = scheme["log_text_color"]
    tab_selected_bg = scheme["tab_selected_bg"]
    tab_unselected_bg = scheme["tab_unselected_bg"]

    update_styles()


def update_styles() -> None:
    global main_window_style, button_style, tab_style
    global group_style, log_style, combobox_style, lineedit_style, textedit_style

    main_window_style = f"""
        QMainWindow {{
            background-color: {background_color};
            border-radius: 10px;
        }}
        QWidget#central {{
            background-color: {background_color};
            border-radius: 10px;
        }}
    """

    button_style = f"""
        QPushButton {{
            background-color: {button_bg_color};
            color: {button_text_color};
            border: 1px solid {border_color};
            border-radius: 4px;
            padding: 6px 14px;
            font-family: {current_font_family};
            font-size: 12px;
        }}
        QPushButton:hover {{
            background-color: {button_hover_color};
        }}
        QPushButton:pressed {{
            background-color: {border_color};
        }}
    """

    tab_style = f"""
        QTabWidget::pane {{
            border: 1px solid {border_color};
            border-radius: 4px;
            background-color: {background_color};
        }}
        QTabBar::tab {{
            background-color: {tab_unselected_bg};
            color: {text_color};
            border: 1px solid {border_color};
            border-bottom: none;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
            padding: 5px 12px;
            font-family: {current_font_family};
            font-size: 12px;
        }}
        QTabBar::tab:selected {{
            background-color: {tab_selected_bg};
            font-weight: bold;
        }}
        QTabBar::tab:hover {{
            background-color: {button_hover_color};
        }}
    """

    group_style = f"""
        QGroupBox {{
            background-color: {group_title_bg_color};
            border: 1px solid {border_color};
            border-radius: 5px;
            margin-top: 8px;
            padding-top: 14px;
            font-family: {current_font_family};
            font-size: 12px;
            color: {text_color};
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 2px 8px;
            background-color: {group_title_bg_color};
            border-radius: 3px;
        }}
    """

    log_style = f"""
        QTextEdit {{
            background-color: {log_bg_color};
            color: {log_text_color};
            border: 1px solid {border_color};
            border-radius: 4px;
            font-family: Consolas, {current_font_family};
            font-size: 11px;
            padding: 4px;
        }}
    """

    combobox_style = f"""
        QComboBox {{
            background-color: {button_bg_color};
            color: {button_text_color};
            border: 1px solid {border_color};
            border-radius: 4px;
            padding: 4px 8px;
            font-family: {current_font_family};
            font-size: 12px;
        }}
        QComboBox:hover {{
            background-color: {button_hover_color};
        }}
        QComboBox QAbstractItemView {{
            background-color: {background_color};
            color: {text_color};
            selection-background-color: {button_hover_color};
        }}
    """

    lineedit_style = f"""
        QLineEdit {{
            background-color: {log_bg_color};
            color: {text_color};
            border: 1px solid {border_color};
            border-radius: 4px;
            padding: 4px 8px;
            font-family: {current_font_family};
            font-size: 12px;
        }}
    """

    textedit_style = f"""
        QTextEdit {{
            background-color: {log_bg_color};
            color: {text_color};
            border: 1px solid {border_color};
            border-radius: 4px;
            font-family: {current_font_family};
            font-size: 12px;
            padding: 4px;
        }}
    """


# Initialize styles on import
update_styles()
