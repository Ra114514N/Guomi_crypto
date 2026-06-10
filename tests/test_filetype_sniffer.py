"""crypto.filetype_sniffer 单元测试。"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from crypto.filetype_sniffer import check_consistency, sniff_type

PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16
PDF_BYTES = b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n"
ZIP_BYTES = b"PK\x03\x04" + b"\x00" * 26


class TestSniffType:
    def test_png(self):
        assert sniff_type(PNG_BYTES) == "PNG 图像"

    def test_pdf(self):
        assert sniff_type(PDF_BYTES) == "PDF 文档"

    def test_zip(self):
        assert sniff_type(ZIP_BYTES) == "ZIP 压缩包"

    def test_utf8_text(self):
        assert sniff_type("普通中文文本，hello world".encode("utf-8")) == "UTF-8 文本"

    def test_json_text(self):
        assert sniff_type(b'{"key": "value", "n": 1}') == "JSON 文本"

    def test_unknown_binary(self):
        assert sniff_type(b"\xde\xad\xbe\xef\x00\x01\x02\xff" * 4) == "二进制数据（未知格式）"

    def test_empty(self):
        assert sniff_type(b"") == "空文件"


class TestCheckConsistency:
    def test_match(self):
        claimed, detected, ok = check_consistency("photo.png", PNG_BYTES)
        assert claimed == "PNG 图像 (.png)"
        assert detected == "PNG 图像"
        assert ok

    def test_mismatch(self):
        claimed, detected, ok = check_consistency("evil.exe", PNG_BYTES)
        assert claimed.endswith("(.exe)")
        assert detected == "PNG 图像"
        assert not ok

    def test_unknown_extension_unfalsifiable(self):
        claimed, detected, ok = check_consistency("data.xyz", PNG_BYTES)
        assert claimed == "未知类型 (.xyz)"
        assert detected == "PNG 图像"
        assert ok

    def test_no_extension(self):
        claimed, _, ok = check_consistency("README", PDF_BYTES)
        assert claimed == "未声明"
        assert ok

    def test_empty_filename(self):
        claimed, _, ok = check_consistency("", ZIP_BYTES)
        assert claimed == "未声明"
        assert ok

    def test_text_extension_accepts_json(self):
        # .txt 内容恰好是合法 JSON，也应视为一致
        _, detected, ok = check_consistency("note.txt", b'{"a": 1}')
        assert detected == "JSON 文本"
        assert ok
