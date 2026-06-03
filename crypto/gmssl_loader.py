"""GmSSL 动态库加载器。

gmssl-python 2.2.2 的 gmssl.py 与旧版 gmssl 包同名，
本模块通过绝对路径加载 gmssl.py，避免 import 冲突。

打包后（PyInstaller frozen）环境下，gmssl.py 和 gmssl.dll
应位于 exe 同级目录。
"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path
from typing import Any

# Determine base directory: frozen (PyInstaller) vs. normal
if getattr(sys, 'frozen', False):
    # PyInstaller 6.x puts data/binaries in _internal/ (sys._MEIPASS)
    _BASE = Path(getattr(sys, '_MEIPASS', Path(sys.executable).parent))
else:
    _BASE = Path(sys.prefix)

# Search for gmssl.py (the gmssl-python 2.2.2 single-file module)
_SEARCH_PATHS = [
    _BASE / "gmssl.py",                              # frozen: exe 同级
    _BASE / "Lib" / "site-packages" / "gmssl.py",    # normal: conda/venv
]
# Fallback: scan sys.path
for _p in sys.path:
    _SEARCH_PATHS.append(Path(_p) / "gmssl.py")

_GMSSL_PY: Path | None = None
for _candidate in _SEARCH_PATHS:
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
    if _GMSSL_PY is None or not _GMSSL_PY.exists():
        _error = f"gmssl.py not found (searched {_SEARCH_PATHS[:3]})"
        return
    try:
        # Ensure the directory containing gmssl.dll is in DLL search path
        dll_dir = str(_GMSSL_PY.parent)
        if hasattr(os, 'add_dll_directory'):
            os.add_dll_directory(dll_dir)
        if dll_dir not in os.environ.get("PATH", ""):
            os.environ["PATH"] = dll_dir + os.pathsep + os.environ.get("PATH", "")

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
