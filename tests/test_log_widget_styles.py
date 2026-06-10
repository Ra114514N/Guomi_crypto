import os
import re

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from gui import styles
from gui.log_widget import LogWidget


def _app():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_default_theme_log_font_size_is_print_readable():
    styles.apply_color_scheme("\u9ed8\u8ba4", is_dark=False)
    assert styles.font_size_log == 16

    styles.apply_color_scheme("\u9ed8\u8ba4", is_dark=True)
    assert styles.font_size_log == 16


def test_log_widget_refresh_applies_current_font_size():
    _app()
    styles.apply_color_scheme("\u9ed8\u8ba4", is_dark=False)
    styles.font_size_log = 18
    styles.update_styles()

    widget = LogWidget()
    widget.refresh_styles()

    assert widget.font().pixelSize() == 18


def test_timestamp_font_is_one_pixel_smaller_than_log_body():
    _app()
    styles.apply_color_scheme("\u9ed8\u8ba4", is_dark=False)
    styles.font_size_log = 16
    styles.update_styles()

    widget = LogWidget()
    timestamp = widget._timestamp_html()

    match = re.search(r"font-size:\s*(\d+)px", timestamp)
    assert match is not None
    assert int(match.group(1)) == 15
