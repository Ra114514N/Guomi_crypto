"""QSS theme system with runtime color scheme switching."""

import json
import sys
from pathlib import Path

from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QApplication

if getattr(sys, 'frozen', False):
    _CONFIG_DIR = Path(getattr(sys, '_MEIPASS', Path(sys.executable).parent)) / "config"
else:
    _CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"

# ── Global color variables (populated by apply_color_scheme) ──────
background_color = "rgba(255, 255, 255, 0.95)"
surface_color = "rgba(255, 255, 255, 0.98)"
text_color = "#333333"
text_muted = "#6b7280"
button_bg_color = "rgba(240, 240, 240, 0.9)"
button_text_color = "#333333"
button_hover_color = "rgba(220, 220, 220, 0.9)"
border_color = "#cccccc"
border_subtle = "#e5e7eb"
group_title_bg_color = "rgba(240, 240, 240, 0.9)"
log_bg_color = "rgba(250, 250, 250, 0.95)"
log_text_color = "#333333"
tab_selected_bg = "rgba(255, 255, 255, 1.0)"
tab_unselected_bg = "rgba(230, 230, 230, 0.8)"

# Accent / semantic
accent_color = "#2563eb"
accent_hover = "#1d4ed8"
accent_text = "#ffffff"
accent_soft = "rgba(37, 99, 235, 0.10)"
success_color = "#16a34a"
error_color = "#dc2626"
warning_color = "#d97706"
info_color = "#0891b2"
mono_color = "#4EC9B0"
highlight_bg = "rgba(37, 99, 235, 0.06)"

# Card system (deep-space theme defaults)
card_bg = "#16161E"
card_border = "#23242F"
mono_bg = "#1F202C"

# Log panel specific colors (terminal aesthetic)
log_timestamp_color = "#5A5E6C"
log_info_color = "#ABB2BF"
log_success_color = "#98C379"
log_highlight_color = "#E5C07B"
log_path_color = "#61AFEF"

# Typography tokens (unified large font)
font_size_title = 18
font_size_body = 16
font_size_mono = 15
font_size_label = 13
font_size_log = 16
font_weight_title = 650
font_weight_body = 500
font_weight_mono = 600
font_weight_label = 500
card_padding = 16
card_spacing = 10
card_border_radius = 8

# Capsule tokens (light-mode only, empty string means fallback to legacy)
capsule_pass_bg = ""
capsule_pass_border = ""
capsule_pass_text = ""
capsule_fail_bg = ""
capsule_fail_border = ""
capsule_fail_text = ""

current_font_family = "'Microsoft YaHei UI', Inter, 'PingFang SC', system-ui, sans-serif"
mono_font_family = "'JetBrains Mono', 'Fira Code', Consolas, monospace"

# Title bar button colors
theme_button_color = "rgba(255, 223, 186, 0.9)"
minimize_button_color = "rgba(198, 255, 198, 0.9)"
maximize_button_color = "rgba(186, 225, 255, 0.9)"
close_button_color = "rgba(255, 204, 204, 0.9)"

# Pre-composed style strings (populated by update_styles)
main_window_style = ""
title_bar_style = ""
button_style = ""
primary_button_style = ""
tab_style = ""
group_style = ""
log_style = ""
combobox_style = ""
lineedit_style = ""
textedit_style = ""
splitter_style = ""
scrollbar_style = ""
status_label_style = ""
step_card_style = ""
nav_button_style = ""
win_control_style = ""

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


def get_scheme(scheme_name: str, is_dark: bool) -> dict:
    """Return the resolved scheme dict (for previews etc.)."""
    mode = "dark" if is_dark else "light"
    default = color_schemes.get("默认", {})
    return color_schemes.get(scheme_name, default).get(mode, {})


def apply_color_scheme(scheme_name: str, is_dark: bool) -> None:
    global background_color, surface_color, text_color, text_muted
    global button_bg_color, button_text_color, button_hover_color
    global border_color, border_subtle, group_title_bg_color
    global log_bg_color, log_text_color, tab_selected_bg, tab_unselected_bg
    global accent_color, accent_hover, accent_text, accent_soft
    global success_color, error_color, warning_color, info_color
    global mono_color, highlight_bg
    global card_bg, card_border, mono_bg
    global log_timestamp_color, log_info_color, log_success_color
    global log_highlight_color, log_path_color
    global font_size_title, font_size_body, font_size_mono
    global font_size_label, font_size_log
    global font_weight_title, font_weight_body, font_weight_mono, font_weight_label
    global card_padding, card_spacing, card_border_radius
    global capsule_pass_bg, capsule_pass_border, capsule_pass_text
    global capsule_fail_bg, capsule_fail_border, capsule_fail_text

    mode = "dark" if is_dark else "light"
    scheme = color_schemes.get(scheme_name, color_schemes["默认"])[mode]

    def _get(key, default):
        return scheme.get(key, default)

    background_color = _get("background_color", background_color)
    surface_color = _get("surface_color", background_color)
    text_color = _get("text_color", text_color)
    text_muted = _get("text_muted", "#6b7280")
    button_bg_color = _get("button_bg_color", button_bg_color)
    button_text_color = _get("button_text_color", button_text_color)
    button_hover_color = _get("button_hover_color", button_hover_color)
    border_color = _get("border_color", border_color)
    border_subtle = _get("border_subtle", border_color)
    group_title_bg_color = _get("group_title_bg_color", group_title_bg_color)
    log_bg_color = _get("log_bg_color", log_bg_color)
    log_text_color = _get("log_text_color", log_text_color)
    tab_selected_bg = _get("tab_selected_bg", tab_selected_bg)
    tab_unselected_bg = _get("tab_unselected_bg", tab_unselected_bg)

    accent_color = _get("accent_color", "#2563eb")
    accent_hover = _get("accent_hover", accent_color)
    accent_text = _get("accent_text", "#ffffff")
    accent_soft = _get("accent_soft", "rgba(37, 99, 235, 0.10)")
    success_color = _get("success_color", "#16a34a")
    error_color = _get("error_color", "#dc2626")
    warning_color = _get("warning_color", "#d97706")
    info_color = _get("info_color", "#0891b2")
    mono_color = _get("mono_color", "#4EC9B0")
    highlight_bg = _get("highlight_bg", accent_soft)
    card_bg = _get("card_bg", "#16161E")
    card_border = _get("card_border", "#23242F")
    mono_bg = _get("mono_bg", "#1F202C")

    # Log panel colors — derived from theme, with terminal-friendly defaults
    log_timestamp_color = _get("log_timestamp_color", "#5A5E6C")
    log_info_color = _get("log_info_color", "#ABB2BF")
    log_success_color = _get("log_success_color", "#98C379")
    log_highlight_color = _get("log_highlight_color", "#E5C07B")
    log_path_color = _get("log_path_color", "#61AFEF")

    # Typography tokens
    font_size_title = _get("font_size_title", 18)
    font_size_body = _get("font_size_body", 16)
    font_size_mono = _get("font_size_mono", 15)
    font_size_label = _get("font_size_label", 13)
    font_size_log = _get("font_size_log", 16)
    font_weight_title = _get("font_weight_title", 650)
    font_weight_body = _get("font_weight_body", 500)
    font_weight_mono = _get("font_weight_mono", 600)
    font_weight_label = _get("font_weight_label", 500)
    card_padding = _get("card_padding", 16)
    card_spacing = _get("card_spacing", 10)
    card_border_radius = _get("card_border_radius", 8)

    # Capsule tokens (empty string = fallback to legacy behavior)
    capsule_pass_bg = _get("capsule_pass_bg", "")
    capsule_pass_border = _get("capsule_pass_border", "")
    capsule_pass_text = _get("capsule_pass_text", "")
    capsule_fail_bg = _get("capsule_fail_bg", "")
    capsule_fail_border = _get("capsule_fail_border", "")
    capsule_fail_text = _get("capsule_fail_text", "")

    update_styles()


def update_styles() -> None:
    global main_window_style, title_bar_style
    global button_style, primary_button_style, tab_style, group_style
    global log_style, combobox_style, lineedit_style, textedit_style
    global splitter_style, scrollbar_style, status_label_style
    global step_card_style, nav_button_style, win_control_style

    main_window_style = f"""
        QWidget#central {{
            background-color: {background_color};
            border-radius: 12px;
            border: 1px solid {border_subtle};
        }}
    """

    title_bar_style = f"""
        QFrame#titleBar {{
            background-color: {surface_color};
            border-top-left-radius: 12px;
            border-top-right-radius: 12px;
            border-bottom: 1px solid {border_subtle};
        }}
        QLabel#titleLabel {{
            color: {text_color};
            font-family: {current_font_family};
        }}
    """

    button_style = f"""
        QPushButton {{
            background-color: {button_bg_color};
            color: {button_text_color};
            border: 1px solid {border_color};
            border-radius: 6px;
            padding: 6px 14px;
            font-family: {current_font_family};
            font-size: 12px;
        }}
        QPushButton:hover {{
            background-color: {button_hover_color};
            border-color: {accent_color};
        }}
        QPushButton:pressed {{
            background-color: {accent_soft};
        }}
        QPushButton:disabled {{
            background-color: {button_bg_color};
            color: {text_muted};
            border-color: {border_subtle};
        }}
    """

    primary_button_style = f"""
        QPushButton {{
            background-color: {accent_color};
            color: {accent_text};
            border: 1px solid {accent_color};
            border-radius: 6px;
            padding: 7px 18px;
            font-family: {current_font_family};
            font-size: 12px;
            font-weight: 600;
        }}
        QPushButton:hover {{
            background-color: {accent_hover};
            border-color: {accent_hover};
        }}
        QPushButton:pressed {{
            background-color: {accent_hover};
            padding-top: 8px;
            padding-bottom: 6px;
        }}
        QPushButton:disabled {{
            background-color: {button_bg_color};
            color: {text_muted};
            border-color: {border_subtle};
        }}
    """

    tab_style = f"""
        QTabWidget::pane {{
            border: 1px solid {border_subtle};
            border-radius: 6px;
            background-color: {surface_color};
            top: -1px;
        }}
        QTabBar {{
            qproperty-drawBase: 0;
            background: transparent;
        }}
        QTabBar::tab {{
            background-color: {tab_unselected_bg};
            color: {text_muted};
            border: 1px solid {border_subtle};
            border-bottom: 2px solid transparent;
            border-top-left-radius: 6px;
            border-top-right-radius: 6px;
            padding: 7px 18px;
            margin-right: 2px;
            font-family: {current_font_family};
            font-size: 12px;
        }}
        QTabBar::tab:selected {{
            background-color: {tab_selected_bg};
            color: {accent_color};
            font-weight: 700;
            border-bottom: 2px solid {accent_color};
        }}
        QTabBar::tab:hover:!selected {{
            background-color: {button_hover_color};
            color: {text_color};
        }}
    """

    group_style = f"""
        QGroupBox {{
            background-color: {surface_color};
            border: 1px solid {border_subtle};
            border-radius: 8px;
            margin-top: 12px;
            padding-top: 14px;
            font-family: {current_font_family};
            font-size: 12px;
            color: {text_color};
            font-weight: 600;
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            left: 10px;
            padding: 2px 10px;
            background-color: {accent_soft};
            color: {accent_color};
            border-radius: 4px;
        }}
        QLabel {{
            color: {text_color};
            font-family: {current_font_family};
        }}
    """

    scrollbar_style = f"""
        QScrollBar:vertical {{
            background: transparent;
            width: 10px;
            margin: 2px 2px 2px 0;
        }}
        QScrollBar::handle:vertical {{
            background: {border_color};
            border-radius: 4px;
            min-height: 30px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: {accent_color};
        }}
        QScrollBar::add-line:vertical,
        QScrollBar::sub-line:vertical {{
            height: 0; background: transparent;
        }}
        QScrollBar::add-page:vertical,
        QScrollBar::sub-page:vertical {{
            background: transparent;
        }}
        QScrollBar:horizontal {{
            background: transparent;
            height: 10px;
            margin: 0 2px 2px 2px;
        }}
        QScrollBar::handle:horizontal {{
            background: {border_color};
            border-radius: 4px;
            min-width: 30px;
        }}
        QScrollBar::handle:horizontal:hover {{
            background: {accent_color};
        }}
        QScrollBar::add-line:horizontal,
        QScrollBar::sub-line:horizontal {{
            width: 0; background: transparent;
        }}
    """

    log_style = f"""
        QTextEdit {{
            background-color: {log_bg_color};
            color: {log_text_color};
            border: 1px solid {border_subtle};
            border-radius: 6px;
            font-family: Consolas, 'JetBrains Mono', {current_font_family};
            font-size: {font_size_log}px;
            padding: 8px 10px;
            selection-background-color: {accent_color};
            selection-color: {accent_text};
        }}
    """ + scrollbar_style

    combobox_style = f"""
        QComboBox {{
            background-color: {button_bg_color};
            color: {button_text_color};
            border: 1px solid {border_color};
            border-radius: 6px;
            padding: 5px 12px;
            font-family: {current_font_family};
            font-size: 12px;
            min-height: 18px;
        }}
        QComboBox:hover {{
            background-color: {button_hover_color};
            border-color: {accent_color};
        }}
        QComboBox:focus {{
            border-color: {accent_color};
        }}
        QComboBox::drop-down {{
            border: none;
            width: 22px;
        }}
        QComboBox::down-arrow {{
            image: none;
            border-left: 4px solid transparent;
            border-right: 4px solid transparent;
            border-top: 5px solid {text_muted};
            margin-right: 8px;
        }}
        QComboBox QAbstractItemView {{
            background-color: {surface_color};
            color: {text_color};
            border: 1px solid {border_color};
            border-radius: 6px;
            selection-background-color: {accent_soft};
            selection-color: {accent_color};
            padding: 4px;
            outline: 0;
        }}
        QComboBox QAbstractItemView::item {{
            padding: 5px 8px;
            border-radius: 3px;
        }}
    """

    lineedit_style = f"""
        QLineEdit {{
            background-color: {log_bg_color};
            color: {text_color};
            border: 1px solid {border_color};
            border-radius: 6px;
            padding: 6px 10px;
            font-family: {current_font_family};
            font-size: 12px;
            selection-background-color: {accent_color};
            selection-color: {accent_text};
        }}
        QLineEdit:hover {{
            border-color: {text_muted};
        }}
        QLineEdit:focus {{
            border-color: {accent_color};
        }}
        QLineEdit:disabled {{
            color: {text_muted};
            background-color: {button_bg_color};
        }}
    """

    textedit_style = f"""
        QTextEdit {{
            background-color: {log_bg_color};
            color: {text_color};
            border: 1px solid {border_subtle};
            border-radius: 6px;
            font-family: {current_font_family};
            font-size: 12px;
            padding: 8px 10px;
            selection-background-color: {accent_color};
            selection-color: {accent_text};
        }}
    """ + scrollbar_style

    splitter_style = f"""
        QSplitter::handle {{
            background: transparent;
        }}
        QSplitter::handle:vertical {{
            height: 6px;
        }}
        QSplitter::handle:horizontal {{
            width: 6px;
        }}
        QSplitter::handle:hover {{
            background: {accent_soft};
            border-radius: 3px;
        }}
    """

    status_label_style = f"""
        QLabel {{
            color: {text_muted};
            font-family: {current_font_family};
            font-size: 11px;
        }}
    """

    step_card_style = f"""
        QFrame#StepCard {{
            background-color: {card_bg};
            border: 1px solid {card_border};
            border-radius: {card_border_radius}px;
        }}
        QFrame#StepCard[status="running"] {{
            border: 1px solid {warning_color};
        }}
        QFrame#StepCard[status="success"] {{
            border: 1px solid {card_border};
        }}
        QFrame#StepCard[status="error"] {{
            border: 1px solid {error_color};
        }}
        QLabel#StepTitle {{
            color: {text_color};
            font-family: {current_font_family};
            font-weight: {font_weight_title};
            font-size: {font_size_title}px;
            background: transparent;
        }}
        QLabel#DataKey {{
            color: {text_muted};
            font-family: {current_font_family};
            font-size: {font_size_label}px;
            font-weight: {font_weight_label};
            background: transparent;
        }}
        QLabel#DataValue {{
            color: {mono_color};
            background-color: {mono_bg};
            border-radius: 4px;
            padding: 3px 6px;
            font-family: {mono_font_family};
            font-size: {font_size_mono}px;
            font-weight: {font_weight_mono};
        }}
        QLabel#StepStatus {{
            font-size: {font_size_title}px;
            background: transparent;
        }}
    """

    nav_button_style = f"""
        QPushButton {{
            background-color: transparent;
            color: {text_muted};
            border: none;
            border-radius: 6px;
            padding: 10px 14px;
            font-family: {current_font_family};
            font-size: 12px;
            text-align: left;
        }}
        QPushButton:hover {{
            background-color: {accent_soft};
            color: {text_color};
        }}
        QPushButton:checked {{
            background-color: {accent_soft};
            color: {accent_color};
            font-weight: 600;
        }}
    """

    # Determine if we're in a light theme by checking background luminance
    _is_light = not background_color.startswith("rgba(13") and "#F" in background_color.upper()[:3] or background_color.startswith("#F")
    _wc_text = "#6B7280" if _is_light else "#5A5E6C"
    _wc_hover_bg = "rgba(0, 0, 0, 0.06)" if _is_light else "rgba(255, 255, 255, 0.08)"
    _wc_pressed_bg = "rgba(0, 0, 0, 0.10)" if _is_light else "rgba(255, 255, 255, 0.12)"

    win_control_style = f"""
        QPushButton {{
            border: none;
            background-color: transparent;
            border-radius: 4px;
            color: {_wc_text};
            font-family: "Segoe UI Symbol", "Segoe UI", {current_font_family};
            font-size: 14px;
            font-weight: 400;
            min-width: 36px;
            max-width: 36px;
            min-height: 24px;
            max-height: 24px;
            margin-left: 2px;
            padding: 0px;
        }}
        QPushButton#WinThemeButton:hover,
        QPushButton#WinMinButton:hover,
        QPushButton#WinMaxButton:hover {{
            color: {'#1F2937' if _is_light else '#FFFFFF'};
            background-color: {_wc_hover_bg};
        }}
        QPushButton#WinCloseButton:hover {{
            color: #FFFFFF;
            background-color: #E81123;
        }}
        QPushButton:pressed {{
            background-color: {_wc_pressed_bg};
        }}
        QPushButton#WinCloseButton:pressed {{
            background-color: #F1707A;
        }}
    """


# Initialize styles on import
update_styles()
