"""文件工具：统一读写、输出目录管理。"""

from __future__ import annotations

from pathlib import Path


OUTPUT_DIR = Path(__file__).parent.parent / "output"


def ensure_output_dir(path: Path | str | None = None) -> Path:
    d = Path(path) if path else OUTPUT_DIR
    d.mkdir(parents=True, exist_ok=True)
    return d


def read_text(path: Path | str, encoding: str = "utf-8") -> str:
    return Path(path).read_text(encoding=encoding)


def write_text(path: Path | str, content: str, encoding: str = "utf-8") -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(content, encoding=encoding)


def read_bytes(path: Path | str) -> bytes:
    return Path(path).read_bytes()


def write_bytes(path: Path | str, data: bytes) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(data)
