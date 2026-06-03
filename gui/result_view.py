"""Rich result-display widget — renders structured sections, KV rows, badges.

Tabs build their result content by chaining helpers on `ResultView`:

    view.clear_content()
    view.section("发送端处理过程")
    view.kv("协议版本", header["version"])
    view.kv("算法套件", header["suite_id"])
    view.badge_row("签名验证", ok=True)
    view.commit()

Internally everything is accumulated into one HTML string and flushed in a
single `setHtml` call to avoid intermediate reflows.
"""

import html as _html
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QTextEdit

from gui import styles


class ResultView(QTextEdit):
    """A scrollable rich-text panel used for tab result output."""

    def __init__(self, parent=None, placeholder: str = ""):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setAcceptRichText(True)
        self.setTextInteractionFlags(
            Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard
        )
        if placeholder:
            self.setPlaceholderText(placeholder)
        f = QFont(styles.current_font_family, 10)
        self.setFont(f)
        self._buffer: list[str] = []

    # ── Buffered building ───────────────────────────────────────

    def clear_content(self) -> None:
        self._buffer.clear()
        self.clear()

    def commit(self) -> None:
        """Flush the buffered HTML to the widget."""
        document_html = (
            f'<div style="font-family: {styles.current_font_family}, '
            f"'Microsoft YaHei', sans-serif; "
            f'color: {styles.text_color}; font-size: 12px; line-height: 1.55;">'
            + "".join(self._buffer)
            + "</div>"
        )
        self.setHtml(document_html)
        self._buffer.clear()
        # Scroll to top after rendering a fresh report
        bar = self.verticalScrollBar()
        bar.setValue(0)

    # ── High-level building blocks ──────────────────────────────

    def section(self, title: str) -> "ResultView":
        """Major section header — accented bar + title."""
        safe = _html.escape(title)
        self._buffer.append(
            f'<div style="margin: 10px 0 6px 0;">'
            f'  <table cellspacing="0" cellpadding="0" style="width: 100%;">'
            f'    <tr>'
            f'      <td style="width: 4px; background-color: {styles.accent_color}; '
            f'             padding: 0;">&nbsp;</td>'
            f'      <td style="padding: 4px 10px; background-color: {styles.accent_soft};">'
            f'        <span style="color: {styles.accent_color}; font-weight: 700; '
            f'              letter-spacing: 0.5px;">{safe}</span>'
            f'      </td>'
            f'    </tr>'
            f'  </table>'
            f'</div>'
        )
        return self

    def subsection(self, title: str) -> "ResultView":
        """Smaller header (the 【...】 style headers in the original)."""
        safe = _html.escape(title)
        self._buffer.append(
            f'<div style="margin: 8px 0 2px 0;">'
            f'  <span style="color: {styles.accent_color}; font-weight: 600;">'
            f'    【{safe}】'
            f'  </span>'
            f'</div>'
        )
        return self

    def paragraph(self, text: str) -> "ResultView":
        safe = _html.escape(text)
        self._buffer.append(
            f'<div style="margin: 2px 0 2px 12px; color: {styles.text_color};">'
            f'{safe}</div>'
        )
        return self

    def hint(self, text: str) -> "ResultView":
        safe = _html.escape(text)
        self._buffer.append(
            f'<div style="margin: 2px 0 2px 12px; color: {styles.text_muted}; '
            f'font-style: italic;">{safe}</div>'
        )
        return self

    def kv(self, key: str, value: str, *, mono: bool = False) -> "ResultView":
        """Key/value pair, key in muted color, value normal (or monospace)."""
        kk = _html.escape(key)
        vv = _html.escape(str(value))
        value_style = (
            f"color: {styles.mono_color}; "
            f"font-family: Consolas, 'JetBrains Mono', monospace;"
            if mono else f"color: {styles.text_color};"
        )
        self._buffer.append(
            f'<table cellspacing="0" cellpadding="0" '
            f'       style="margin: 1px 0 1px 14px;">'
            f'  <tr>'
            f'    <td style="color: {styles.text_muted}; padding-right: 10px; '
            f'           white-space: nowrap; vertical-align: top;">{kk}</td>'
            f'    <td style="{value_style} vertical-align: top; '
            f'           word-break: break-all;">{vv}</td>'
            f'  </tr>'
            f'</table>'
        )
        return self

    def kv_mono(self, key: str, value: str) -> "ResultView":
        return self.kv(key, value, mono=True)

    def badge(self, label: str, *, ok: Optional[bool] = None,
              kind: str = "info", detail: str = "") -> "ResultView":
        """A status badge line: [✓ 通过] 详细描述..."""
        if ok is True:
            kind = "ok"
        elif ok is False:
            kind = "error"

        palette = {
            "ok": (styles.success_color, "✓"),
            "error": (styles.error_color, "✗"),
            "warning": (styles.warning_color, "⚠"),
            "info": (styles.info_color, "•"),
        }
        color, icon = palette.get(kind, palette["info"])
        safe_label = _html.escape(label)
        safe_detail = _html.escape(detail)
        detail_html = (
            f'<span style="color: {styles.text_muted}; margin-left: 8px;">— {safe_detail}</span>'
            if safe_detail else ""
        )
        self._buffer.append(
            f'<div style="margin: 4px 0 4px 12px;">'
            f'  <span style="display: inline-block; padding: 2px 10px; '
            f'         background-color: {color}; color: white; border-radius: 10px; '
            f'         font-weight: 600; font-size: 11px;">'
            f'    {icon} {safe_label}'
            f'  </span>'
            f'  {detail_html}'
            f'</div>'
        )
        return self

    def divider(self) -> "ResultView":
        self._buffer.append(
            f'<div style="margin: 8px 0; '
            f'       border-top: 1px solid {styles.border_subtle};"></div>'
        )
        return self

    def spacer(self, px: int = 4) -> "ResultView":
        self._buffer.append(f'<div style="height: {px}px;"></div>')
        return self

    def code_block(self, text: str) -> "ResultView":
        safe = _html.escape(text)
        self._buffer.append(
            f'<div style="margin: 4px 0 4px 14px; padding: 6px 10px; '
            f'       background-color: {styles.highlight_bg}; '
            f'       border-left: 3px solid {styles.accent_color}; '
            f'       border-radius: 3px;">'
            f'  <span style="font-family: Consolas, monospace; '
            f'         color: {styles.mono_color}; word-break: break-all;">{safe}</span>'
            f'</div>'
        )
        return self

    def conclusion(self, text: str, *, ok: bool = True) -> "ResultView":
        color = styles.success_color if ok else styles.error_color
        icon = "✓" if ok else "✗"
        safe = _html.escape(text)
        self._buffer.append(
            f'<div style="margin: 10px 14px 4px 14px; padding: 10px 14px; '
            f'       background-color: {styles.accent_soft}; '
            f'       border-left: 4px solid {color}; border-radius: 4px;">'
            f'  <span style="color: {color}; font-weight: 700; font-size: 13px;">'
            f'    {icon} {safe}'
            f'  </span>'
            f'</div>'
        )
        return self

    def raw_html(self, html_str: str) -> "ResultView":
        """Escape hatch — append raw HTML."""
        self._buffer.append(html_str)
        return self

    # ── Convenience for showing pre-existing markdown/text dump ─

    def set_preformatted(self, text: str) -> None:
        """Render plain text in a monospace block (used by benchmark table)."""
        safe = _html.escape(text)
        # Replace runs of spaces with non-breaking spaces to preserve alignment
        safe = safe.replace("  ", "&nbsp;&nbsp;")
        safe = safe.replace("\n", "<br>")
        self._buffer.append(
            f'<div style="margin: 6px 12px; padding: 10px 12px; '
            f'       background-color: {styles.highlight_bg}; '
            f'       border: 1px solid {styles.border_subtle}; border-radius: 4px; '
            f'       font-family: Consolas, monospace; font-size: 11px; '
            f'       color: {styles.text_color}; line-height: 1.55;">'
            f'{safe}'
            f'</div>'
        )
