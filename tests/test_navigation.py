from __future__ import annotations

import ast
from pathlib import Path


def test_main_window_left_nav_has_single_demo_entry():
    source = Path("gui/main_window.py").read_text(encoding="utf-8")
    tree = ast.parse(source)

    nav_items = None
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            if any(isinstance(target, ast.Name) and target.id == "nav_items" for target in node.targets):
                nav_items = ast.literal_eval(node.value)
                break

    assert nav_items is not None
    assert [key for key, _label in nav_items] == ["demo", "env"]


def test_file_picker_button_has_visual_hint():
    source = Path("gui/main_window.py").read_text(encoding="utf-8")

    assert 'browse_btn = QPushButton("📂 选择")' in source
    assert "browse_btn.setFixedSize(72, 30)" in source
    assert 'browse_btn.setToolTip("选择明文文件")' in source


def test_log_clear_button_has_readable_size():
    source = Path("gui/main_window.py").read_text(encoding="utf-8")

    assert 'clear_btn = QPushButton("清空")' in source
    assert "clear_btn.setFixedSize(58, 28)" in source
    assert 'clear_btn.setToolTip("清空日志")' in source
