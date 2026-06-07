from __future__ import annotations

from pathlib import Path


PROJECT_NAME = "基于国密算法的安全数据传输与身份认证系统"


def test_gui_titles_use_full_project_name():
    main_source = Path("gui/main_window.py").read_text(encoding="utf-8")
    receiver_source = Path("gui/receiver_window.py").read_text(encoding="utf-8")

    assert f'{PROJECT_NAME} — 发送端' in main_source
    assert f'{PROJECT_NAME} — 接收端' in receiver_source
    assert f'setToolTip("{PROJECT_NAME} — 发送端")' in main_source
    assert f'setToolTip("{PROJECT_NAME} — 接收端")' in receiver_source
    assert "国密安全传输" not in main_source
    assert "国密安全传输" not in receiver_source


def test_packaged_exe_uses_full_project_name():
    spec_source = Path("build.spec").read_text(encoding="utf-8")

    assert f'name="{PROJECT_NAME}"' in spec_source
    assert "国密安全传输系统" not in spec_source
