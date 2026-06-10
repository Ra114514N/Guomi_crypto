# Log Font Print Readability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make sender and receiver console logs use a 16px print-readable font with refresh-safe styling.

**Architecture:** Keep log sizing controlled by existing theme tokens. Add a small `LogWidget.refresh_styles()` boundary so QSS and the direct Qt font stay aligned whenever sender or receiver windows refresh their styles.

**Tech Stack:** Python 3.12, PySide6, pytest.

---

## File Structure

- Modify `config/style.json`: change light and dark `font_size_log` from `13` to `16`.
- Modify `gui/styles.py`: change fallback/default `font_size_log` from `13` to `16`, including the fallback inside `apply_color_scheme()`.
- Modify `gui/log_widget.py`: add `_apply_font()` and `refresh_styles()`, use them from `__init__()`, and update timestamp font size to `max(styles.font_size_log - 1, 10)`.
- Modify `gui/main_window.py`: call `self.log_output.refresh_styles()` from `_refresh_styles()`.
- Modify `gui/receiver_window.py`: call `self.log_output.refresh_styles()` from `_refresh_styles()`.
- Create `tests/test_log_widget_styles.py`: focused tests for theme token size, widget font refresh, and timestamp size.

---

### Task 1: Add Log Font Style Tests

**Files:**
- Create: `tests/test_log_widget_styles.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_log_widget_styles.py` with:

```python
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
    styles.apply_color_scheme("默认", is_dark=False)
    assert styles.font_size_log == 16

    styles.apply_color_scheme("默认", is_dark=True)
    assert styles.font_size_log == 16


def test_log_widget_refresh_applies_current_font_size():
    _app()
    styles.apply_color_scheme("默认", is_dark=False)
    styles.font_size_log = 18
    styles.update_styles()

    widget = LogWidget()
    widget.refresh_styles()

    assert widget.font().pixelSize() == 18


def test_timestamp_font_is_one_pixel_smaller_than_log_body():
    _app()
    styles.apply_color_scheme("默认", is_dark=False)
    styles.font_size_log = 16
    styles.update_styles()

    widget = LogWidget()
    timestamp = widget._timestamp_html()

    match = re.search(r"font-size:\s*(\d+)px", timestamp)
    assert match is not None
    assert int(match.group(1)) == 15
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
$env:QT_QPA_PLATFORM='offscreen'; pytest tests/test_log_widget_styles.py -q
```

Expected: at least `test_default_theme_log_font_size_is_print_readable` fails because current `font_size_log` is `13`.

---

### Task 2: Implement Print-Readable Log Font Refresh

**Files:**
- Modify: `config/style.json`
- Modify: `gui/styles.py`
- Modify: `gui/log_widget.py`
- Modify: `gui/main_window.py`
- Modify: `gui/receiver_window.py`

- [ ] **Step 1: Update theme tokens**

In `config/style.json`, change both occurrences:

```json
"font_size_log": 13
```

to:

```json
"font_size_log": 16
```

- [ ] **Step 2: Update style fallbacks**

In `gui/styles.py`, change the module default:

```python
font_size_log = 13
```

to:

```python
font_size_log = 16
```

Also change the `apply_color_scheme()` fallback:

```python
font_size_log = _get("font_size_log", 13)
```

to:

```python
font_size_log = _get("font_size_log", 16)
```

- [ ] **Step 3: Add refresh-safe font application**

In `gui/log_widget.py`, replace the inline font setup in `__init__()` with:

```python
self._apply_font()
```

Add this method to `LogWidget`:

```python
def refresh_styles(self) -> None:
    self._apply_font()
    self.setStyleSheet(styles.log_style)

def _apply_font(self) -> None:
    font = QFont("Consolas")
    font.setStyleHint(QFont.Monospace)
    font.setPixelSize(styles.font_size_log)
    self.setFont(font)
```

Update `_timestamp_html()` so the timestamp size is computed first:

```python
timestamp_size = max(styles.font_size_log - 1, 10)
```

and use:

```python
f'font-size: {timestamp_size}px;">'
```

- [ ] **Step 4: Delegate log styling to LogWidget**

In `gui/main_window.py`, replace:

```python
self.log_output.setStyleSheet(styles.log_style)
```

with:

```python
self.log_output.refresh_styles()
```

In `gui/receiver_window.py`, make the same replacement.

- [ ] **Step 5: Run focused tests**

Run:

```powershell
$env:QT_QPA_PLATFORM='offscreen'; pytest tests/test_log_widget_styles.py -q
```

Expected: all tests pass.

- [ ] **Step 6: Run related regression tests**

Run:

```powershell
$env:QT_QPA_PLATFORM='offscreen'; pytest tests/test_navigation.py tests/test_receiver_window_presentation.py tests/test_log_widget_styles.py -q
```

Expected: all selected tests pass.

---

## Plan Self-Review

- Spec coverage: The plan updates theme tokens, style fallbacks, timestamp sizing, widget refresh behavior, and sender/receiver refresh call sites.
- Placeholder scan: No `TBD`, `TODO`, or unspecified implementation steps remain.
- Type consistency: The planned methods are `LogWidget.refresh_styles()` and `LogWidget._apply_font()`, and call sites use `self.log_output.refresh_styles()`.
