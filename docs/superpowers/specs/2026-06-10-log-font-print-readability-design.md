# Log Font Print Readability Design

## Goal

Make the GUI console log readable when screenshots are printed on A4 paper, while preserving the existing terminal-like visual style.

## Context

The project uses a PySide6 GUI with separate sender and receiver windows. Both windows create a `LogWidget` from `gui/log_widget.py` and apply log styling through `gui/styles.py`.

Current behavior:

- `config/style.json` sets `font_size_log` to `13` in both light and dark themes.
- `gui/styles.py` has a fallback `font_size_log = 13`.
- `LogWidget.__init__()` creates a `QFont("Consolas")`, applies `styles.font_size_log`, and sets it directly on the QTextEdit.
- `main_window.py` and `receiver_window.py` refresh the log by calling `self.log_output.setStyleSheet(styles.log_style)`.
- The direct `QFont` assignment is not refreshed explicitly when styles are refreshed.

The user selected the larger-font approach and accepted extra wrapping in the log panel.

## Selected Approach

Use a robust 16px log font implementation:

1. Raise `font_size_log` from `13` to `16` in both light and dark theme tokens.
2. Raise the fallback `font_size_log` in `gui/styles.py` from `13` to `16`.
3. Keep the log body controlled by `styles.font_size_log`.
4. Make timestamps only slightly smaller than the body text: `max(styles.font_size_log - 1, 10)`.
5. Add a `LogWidget.refresh_styles()` method that reapplies both the direct `QFont` and `styles.log_style`.
6. Update sender and receiver window refresh paths to call `self.log_output.refresh_styles()`.

## Non-Goals

- Do not change log panel width.
- Do not change the sender or receiver layout.
- Do not add a user-facing font-size setting.
- Do not change log message content or classification rules.
- Do not change crypto, protocol, or worker behavior.

## Components

### `config/style.json`

The `font_size_log` token becomes `16` for both light and dark theme objects.

### `gui/styles.py`

The module fallback `font_size_log` becomes `16`, and `apply_color_scheme()` should use `16` as its fallback when the JSON token is missing.

### `gui/log_widget.py`

`LogWidget` gets a private `_apply_font()` helper and a public `refresh_styles()` method.

Expected behavior:

- `_apply_font()` creates the existing monospace font stack behavior with `QFont("Consolas")`, `QFont.Monospace`, and `styles.font_size_log`.
- `refresh_styles()` calls `_apply_font()` and then `self.setStyleSheet(styles.log_style)`.
- `__init__()` uses `_apply_font()` instead of duplicating font setup.
- `_timestamp_html()` uses `max(styles.font_size_log - 1, 10)`.

### `gui/main_window.py` and `gui/receiver_window.py`

Window style refresh should delegate log styling to `LogWidget.refresh_styles()` instead of directly applying only `styles.log_style`.

## Data Flow

Theme data flows as:

`config/style.json` -> `styles.apply_color_scheme()` -> `styles.font_size_log` and `styles.log_style` -> `LogWidget.refresh_styles()` -> QTextEdit font and stylesheet.

This makes the direct Qt font and QSS font-size stay aligned.

## Testing

Add focused tests for the non-GUI-heavy logic:

- Applying the project default light theme loads `font_size_log == 16`.
- Applying the project default dark theme loads `font_size_log == 16`.
- `LogWidget.refresh_styles()` reapplies the current `styles.font_size_log` to the widget font.
- Timestamp HTML uses `font_size_log - 1` for the timestamp size when the log size is 16.

Use the existing PySide6 test environment. Set `QT_QPA_PLATFORM=offscreen` when running widget tests.

## Acceptance Criteria

- Sender and receiver logs render at 16px body size.
- Timestamp text renders at 15px when log body size is 16px.
- Calling window `_refresh_styles()` updates the log widget font, not only the stylesheet.
- Existing tests pass.
- A GUI screenshot should show visibly larger log text suitable for A4 printing, with wrapping accepted.
