from __future__ import annotations

from pathlib import Path


def test_build_spec_includes_current_gui_modules():
    spec_source = Path("build.spec").read_text(encoding="utf-8")

    assert "gui.receiver_window" in spec_source
    assert "gui.elided_label" in spec_source
    assert "gui.frameless_resize" in spec_source


def test_build_spec_places_shiboken_runtime_next_to_pyside6_extensions():
    spec_source = Path("build.spec").read_text(encoding="utf-8")

    assert "shiboken6.abi3.dll" in spec_source
    assert "PySide6" in spec_source
