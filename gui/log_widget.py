"""Rich log widget — auto-classifies messages, colorizes, prepends timestamps."""

import html
import re
from datetime import datetime

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QTextCursor, QFont
from PySide6.QtWidgets import QTextEdit

from gui import styles


# Pattern probes used to classify a free-form log line.
_RE_SECTION_HEAVY = re.compile(r"═══")
_RE_SECTION_DASH = re.compile(r"──+|━━+")
_RE_PROGRESS = re.compile(r"^\s*▶")
_RE_OK = re.compile(r"^\s*✓|✓\s|\b(完成|通过|成功)\b")
_RE_ERR = re.compile(r"^\s*✗|✗\s|^\s*错误[:：]|\b(失败|出错|异常)\b|^\s*\[ERROR\]|^\s*\[ERR\]")
_RE_WARN = re.compile(r"^\s*⚠|^\s*警告[:：]|^\s*\[WARN\]|^\s*\[WARNING\]")
_RE_INFO_TAG = re.compile(r"^\s*\[INFO\]\s*")
_RE_DEBUG_TAG = re.compile(r"^\s*\[DEBUG\]\s*")

# Inline patterns that should render in monospace / accent color.
_RE_HEXISH = re.compile(r"\b[0-9a-fA-F]{12,}\b")
_RE_B64ISH = re.compile(r"\b[A-Za-z0-9+/]{16,}={0,2}\.{3}")


class LogWidget(QTextEdit):
    """QTextEdit subclass that emits richly styled, timestamped log entries.

    Use `append_message(text)` to log; the widget classifies the line by
    leading marker and renders accordingly. The widget always scrolls to the
    bottom on new content.
    """

    MAX_BLOCKS = 5000  # rolling cap to keep memory bounded

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setAcceptRichText(False)
        self.setTextInteractionFlags(
            Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard
        )
        self.setUndoRedoEnabled(False)
        font = QFont("Consolas")
        font.setStyleHint(QFont.Monospace)
        font.setPointSize(10)
        self.setFont(font)
        self._show_timestamps = True

    # ── Public API ─────────────────────────────────────────────

    def set_show_timestamps(self, on: bool) -> None:
        self._show_timestamps = on

    def append_message(self, text: str) -> None:
        """Auto-classify and append a single message (which may have newlines)."""
        if not text:
            return
        for line in text.splitlines():
            self._append_classified(line)
        self._trim_to_cap()
        self._scroll_to_bottom()

    def append_plain(self, text: str) -> None:
        """Append text verbatim, with timestamp but no classification styling."""
        for line in text.splitlines():
            self._emit_line(line, level="plain")
        self._trim_to_cap()
        self._scroll_to_bottom()

    def clear_log(self) -> None:
        self.clear()

    # ── Classification & rendering ─────────────────────────────

    def _append_classified(self, line: str) -> None:
        if not line.strip():
            # blank line — preserve spacing but no timestamp
            self._raw_append("<div>&nbsp;</div>")
            return

        if _RE_SECTION_HEAVY.search(line):
            self._emit_line(line, level="section_major")
        elif _RE_SECTION_DASH.search(line) and not _RE_PROGRESS.search(line):
            self._emit_line(line, level="section")
        elif _RE_PROGRESS.search(line):
            self._emit_line(line, level="progress")
        elif _RE_ERR.search(line):
            self._emit_line(line, level="error")
        elif _RE_WARN.search(line):
            self._emit_line(line, level="warning")
        elif _RE_OK.search(line):
            self._emit_line(line, level="ok")
        elif _RE_DEBUG_TAG.search(line):
            self._emit_line(_RE_DEBUG_TAG.sub("", line), level="debug")
        elif _RE_INFO_TAG.search(line):
            self._emit_line(_RE_INFO_TAG.sub("", line), level="info")
        else:
            self._emit_line(line, level="info")

    def _emit_line(self, line: str, *, level: str) -> None:
        ts = self._timestamp_html()
        body = self._render_body(line, level)

        styles_map = {
            "section_major": (
                f"color: #FFFFFF; font-weight: 700; letter-spacing: 0.5px;"
            ),
            "section": (
                f"color: {styles.log_timestamp_color}; font-weight: 600;"
            ),
            "progress": (
                f"color: {styles.log_highlight_color}; font-weight: 600;"
            ),
            "ok": (
                f"color: {styles.log_success_color}; font-weight: 500;"
            ),
            "error": (
                f"color: {styles.error_color}; font-weight: 600;"
            ),
            "warning": (
                f"color: {styles.warning_color};"
            ),
            "info": (
                f"color: {styles.log_info_color};"
            ),
            "debug": (
                f"color: {styles.log_timestamp_color}; font-style: italic;"
            ),
            "plain": (
                f"color: {styles.log_info_color};"
            ),
        }
        style = styles_map.get(level, styles_map["info"])

        line_html = (
            f'<div style="margin: 0; padding: 1px 0; line-height: 1.5;">'
            f'{ts}<span style="{style}">{body}</span>'
            f'</div>'
        )
        self._raw_append(line_html)

    def _render_body(self, line: str, level: str) -> str:
        text = html.escape(line)

        if level in ("section_major", "section", "progress"):
            return text

        # Highlight inline hex tokens with mono cyan color
        def hex_repl(m):
            return (
                f'<span style="color: {styles.mono_color}; '
                f'font-family: {styles.mono_font_family};">'
                f'{m.group(0)}</span>'
            )

        text = _RE_HEXISH.sub(hex_repl, text)
        return text

    def _timestamp_html(self) -> str:
        if not self._show_timestamps:
            return ""
        ts = datetime.now().strftime("%H:%M:%S")
        return (
            f'<span style="color: {styles.log_timestamp_color}; '
            f'font-family: {styles.mono_font_family}; font-size: 10px;">'
            f'[{ts}] </span>'
        )

    def _raw_append(self, html_str: str) -> None:
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertHtml(html_str)
        cursor.insertBlock()
        # Reset block format to default so the next block isn't styled.

    def _trim_to_cap(self) -> None:
        doc = self.document()
        excess = doc.blockCount() - self.MAX_BLOCKS
        if excess > 0:
            cursor = QTextCursor(doc)
            cursor.movePosition(QTextCursor.Start)
            for _ in range(excess):
                cursor.select(QTextCursor.BlockUnderCursor)
                cursor.removeSelectedText()
                cursor.deleteChar()  # remove the trailing newline

    def _scroll_to_bottom(self) -> None:
        QTimer.singleShot(0, self._do_scroll)

    def _do_scroll(self) -> None:
        bar = self.verticalScrollBar()
        bar.setValue(bar.maximum())
