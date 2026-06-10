# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for 基于国密算法的安全数据传输与身份认证系统.

Build:
    pyinstaller build.spec --noconfirm

Output:
    dist/GuomiCrypto/  (single-directory distribution)
"""

import sys
from pathlib import Path

block_cipher = None
ROOT = Path(SPECPATH)

# gmssl.py (the gmssl-python 2.2.2 single-file native binding module)
_GMSSL_PY = Path(sys.prefix) / "Lib" / "site-packages" / "gmssl.py"
_SHIBOKEN_DLL = Path(sys.prefix) / "Lib" / "site-packages" / "shiboken6" / "shiboken6.abi3.dll"

a = Analysis(
    [str(ROOT / "gui" / "run.py")],
    pathex=[str(ROOT)],
    binaries=[
        # Release-compiled GmSSL native library
        (str(ROOT / "gmssl_release.dll"), "."),
        # PySide6 extension modules load this DLL while importing QtWidgets.
        # Keep the normal shiboken6 copy and add a compatibility copy next to PySide6/*.pyd.
        (str(_SHIBOKEN_DLL), "PySide6"),
    ],
    datas=[
        # gmssl.py module (loaded dynamically by gmssl_loader.py)
        (str(_GMSSL_PY), "."),
        # Theme config
        (str(ROOT / "config"), "config"),
        # Default plaintext sample
        (str(ROOT / "plain.txt"), "."),
        # Logo assets
        (str(ROOT / "logo.png"), "."),
        (str(ROOT / "logo.ico"), "."),
    ],
    hiddenimports=[
        # crypto layer
        "crypto",
        "crypto.sm2_adapter",
        "crypto.sm3_adapter",
        "crypto.sm4_adapter",
        "crypto.zuc_adapter",
        "crypto.sm9_signature",
        "crypto.gmssl_loader",
        "crypto.kdf_utils",
        "crypto.metadata_utils",
        "crypto.sm3_integrity",
        "crypto.sm2_kex_or_wrap",
        "crypto.key_utils",
        "crypto.file_utils",
        # core layer
        "core",
        "core.sender",
        "core.receiver",
        "core.workflow",
        "core.benchmark",
        "core.protocol",
        # gui layer
        "gui",
        "gui.styles",
        "gui.effects",
        "gui.log_widget",
        "gui.result_view",
        "gui.step_card",
        "gui.data_widgets",
        "gui.timeline_view",
        "gui.theme_selector",
        "gui.workers",
        "gui.main_window",
        "gui.receiver_window",
        "gui.elided_label",
        "gui.frameless_resize",
        "gui.tabs",
        "gui.tabs.env_tab",
        "gui.tabs.demo_tab",
        "gui.tabs.send_recv_tab",
        "gui.tabs.benchmark_tab",
        # gmssl pure-python (SM2/SM3/SM4)
        "gmssl",
        "gmssl.sm2",
        "gmssl.sm3",
        "gmssl.sm4",
        "gmssl.func",
        # ctypes needed by gmssl.py (dynamically loaded, not traced by PyInstaller)
        "ctypes",
        "ctypes.util",
    ],
    noarchive=False,
)

# Rename the bundled gmssl_release.dll to gmssl.dll so ctypes can find it
for i, (dest, src, kind) in enumerate(a.binaries):
    if "gmssl_release" in dest:
        a.binaries[i] = ("gmssl.dll", src, kind)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="基于国密算法的安全数据传输与身份认证系统",
    icon=str(ROOT / "logo.ico"),
    console=False,
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    name="GuomiCrypto",
)
