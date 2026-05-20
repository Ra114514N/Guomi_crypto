"""GmSSL 动态库加载器。

gmssl-python 2.2.2 的 gmssl.py 与旧版 gmssl 包同名，
本模块通过绝对路径加载 gmssl.py，避免 import 冲突。
"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path
from typing import Any

_GMSSL_PY = Path(sys.prefix) / "Lib" / "site-packages" / "gmssl.py"
if not _GMSSL_PY.exists():
    # Linux / macOS
    for _p in sys.path:
        _candidate = Path(_p) / "gmssl.py"
        if _candidate.exists():
            _GMSSL_PY = _candidate
            break

_gmssl_lib: Any = None
_available: bool = False
_error: str = ""


def _load() -> None:
    global _gmssl_lib, _available, _error
    if _gmssl_lib is not None:
        return
    if not _GMSSL_PY.exists():
        _error = f"gmssl.py not found (searched {_GMSSL_PY})"
        return
    try:
        spec = importlib.util.spec_from_file_location("_gmssl_native", str(_GMSSL_PY))
        mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
        _gmssl_lib = mod
        _available = True
    except Exception as e:
        _error = str(e)


_load()


def get_gmssl():
    """返回 gmssl-python 模块，不可用时抛出 ImportError。"""
    if not _available:
        raise ImportError(
            f"GmSSL native library unavailable: {_error}\n"
            "Install: download gmssl.dll from https://github.com/guanzhi/GmSSL/releases "
            "and place it in the Python environment directory."
        )
    return _gmssl_lib


def is_available() -> bool:
    return _available


def error_message() -> str:
    return _error
