"""文件类型嗅探：magic bytes 内容识别 + 扩展名声称一致性比对。

双轨设计：
- ``sniff_type``  仅看字节内容（独立计算值），不信任任何元数据；
- ``check_consistency``  把信封 header 里声称的文件名扩展（声称值）与
  内容嗅探结果对比，供接收端展示「声称 vs 检测」。

纯标准库实现，不引入新依赖。
"""

from __future__ import annotations

import json
from pathlib import Path

# 中文类型标签（sniff_type 的返回值域）
LABEL_EMPTY = "空文件"
LABEL_PNG = "PNG 图像"
LABEL_JPEG = "JPEG 图像"
LABEL_GIF = "GIF 图像"
LABEL_BMP = "BMP 图像"
LABEL_WEBP = "WebP 图像"
LABEL_PDF = "PDF 文档"
LABEL_ZIP = "ZIP 压缩包"
LABEL_7Z = "7z 压缩包"
LABEL_RAR = "RAR 压缩包"
LABEL_GZIP = "GZIP 压缩包"
LABEL_PE = "PE 可执行文件"
LABEL_ELF = "ELF 可执行文件"
LABEL_MP3 = "MP3 音频"
LABEL_MP4 = "MP4 视频"
LABEL_WAV = "WAV 音频"
LABEL_SQLITE = "SQLite 数据库"
LABEL_JSON = "JSON 文本"
LABEL_TEXT = "UTF-8 文本"
LABEL_UNKNOWN = "二进制数据（未知格式）"

# (前缀, 偏移, 标签)，按声明顺序匹配
_MAGIC_TABLE: list[tuple[bytes, int, str]] = [
    (b"\x89PNG\r\n\x1a\n", 0, LABEL_PNG),
    (b"\xff\xd8\xff", 0, LABEL_JPEG),
    (b"GIF87a", 0, LABEL_GIF),
    (b"GIF89a", 0, LABEL_GIF),
    (b"%PDF-", 0, LABEL_PDF),
    (b"PK\x03\x04", 0, LABEL_ZIP),
    (b"PK\x05\x06", 0, LABEL_ZIP),  # 空 ZIP
    (b"PK\x07\x08", 0, LABEL_ZIP),  # 分卷 ZIP
    (b"7z\xbc\xaf\x27\x1c", 0, LABEL_7Z),
    (b"Rar!\x1a\x07", 0, LABEL_RAR),
    (b"\x1f\x8b", 0, LABEL_GZIP),
    (b"\x7fELF", 0, LABEL_ELF),
    (b"SQLite format 3\x00", 0, LABEL_SQLITE),
    (b"ID3", 0, LABEL_MP3),
    (b"ftyp", 4, LABEL_MP4),  # MP4/MOV 家族：box size 后跟 'ftyp'
]


def sniff_type(data: bytes) -> str:
    """根据 magic bytes 识别字节内容类型，返回中文标签。"""
    if not data:
        return LABEL_EMPTY

    for magic, offset, label in _MAGIC_TABLE:
        if data[offset:offset + len(magic)] == magic:
            return label

    # RIFF 容器需看子类型再细分
    if data[:4] == b"RIFF":
        if data[8:12] == b"WEBP":
            return LABEL_WEBP
        if data[8:12] == b"WAVE":
            return LABEL_WAV
        return LABEL_UNKNOWN

    # MP3 裸帧（无 ID3 标签）：帧同步字 0xFFEx/0xFFFx
    if len(data) >= 2 and data[0] == 0xFF and data[1] in (0xF2, 0xF3, 0xFB):
        return LABEL_MP3

    # BMP 的 'BM' 与 PE 的 'MZ' 都是弱 magic，放在强 magic 之后
    if data[:2] == b"BM":
        return LABEL_BMP
    if data[:2] == b"MZ":
        return LABEL_PE

    # 文本启发式：strict UTF-8 可解码且不含 NUL 字节
    if b"\x00" not in data:
        try:
            text = data.decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            pass
        else:
            try:
                json.loads(text)
                return LABEL_JSON
            except (json.JSONDecodeError, ValueError):
                return LABEL_TEXT

    return LABEL_UNKNOWN


# 扩展名 → (声称类型名, 与之一致的检测标签集合)
_EXT_TABLE: dict[str, tuple[str, frozenset[str]]] = {
    ".png": ("PNG 图像", frozenset({LABEL_PNG})),
    ".jpg": ("JPEG 图像", frozenset({LABEL_JPEG})),
    ".jpeg": ("JPEG 图像", frozenset({LABEL_JPEG})),
    ".gif": ("GIF 图像", frozenset({LABEL_GIF})),
    ".bmp": ("BMP 图像", frozenset({LABEL_BMP})),
    ".webp": ("WebP 图像", frozenset({LABEL_WEBP})),
    ".pdf": ("PDF 文档", frozenset({LABEL_PDF})),
    ".zip": ("ZIP 压缩包", frozenset({LABEL_ZIP})),
    ".docx": ("Word 文档", frozenset({LABEL_ZIP})),  # OOXML 本质是 ZIP
    ".xlsx": ("Excel 表格", frozenset({LABEL_ZIP})),
    ".7z": ("7z 压缩包", frozenset({LABEL_7Z})),
    ".rar": ("RAR 压缩包", frozenset({LABEL_RAR})),
    ".gz": ("GZIP 压缩包", frozenset({LABEL_GZIP})),
    ".exe": ("Windows 可执行文件", frozenset({LABEL_PE})),
    ".dll": ("Windows 动态库", frozenset({LABEL_PE})),
    ".mp3": ("MP3 音频", frozenset({LABEL_MP3})),
    ".mp4": ("MP4 视频", frozenset({LABEL_MP4})),
    ".wav": ("WAV 音频", frozenset({LABEL_WAV})),
    ".db": ("SQLite 数据库", frozenset({LABEL_SQLITE})),
    ".sqlite": ("SQLite 数据库", frozenset({LABEL_SQLITE})),
    ".txt": ("纯文本", frozenset({LABEL_TEXT, LABEL_JSON})),
    ".md": ("Markdown 文本", frozenset({LABEL_TEXT, LABEL_JSON})),
    ".json": ("JSON 文本", frozenset({LABEL_JSON, LABEL_TEXT})),
    ".py": ("Python 源码", frozenset({LABEL_TEXT, LABEL_JSON})),
    ".log": ("日志文本", frozenset({LABEL_TEXT, LABEL_JSON})),
}


def check_consistency(filename: str, data: bytes) -> tuple[str, str, bool]:
    """比对声称的文件名扩展与字节内容嗅探结果。

    返回 ``(声称描述, 检测标签, 是否一致)``：
    - 已知扩展名：声称描述如「PNG 图像 (.png)」，一致性取决于检测标签是否落在
      该扩展名对应的可接受集合内；
    - 未知扩展名：声称描述「未知类型 (.xyz)」，无法证伪，一致性视为 True；
    - 无扩展名 / 无文件名：声称「未声明」，一致性视为 True。
    """
    detected = sniff_type(data)
    suffix = Path(filename).suffix.lower() if filename else ""

    if not suffix:
        return "未声明", detected, True

    entry = _EXT_TABLE.get(suffix)
    if entry is None:
        return f"未知类型 ({suffix})", detected, True

    claimed_name, acceptable = entry
    return f"{claimed_name} ({suffix})", detected, detected in acceptable
