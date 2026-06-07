from __future__ import annotations

from pathlib import Path


def test_receiver_window_uses_larger_default_size_and_log_panel():
    source = Path("gui/receiver_window.py").read_text(encoding="utf-8")

    assert "self.setMinimumSize(840, 680)" in source
    assert "self.resize(1080, 960)" in source
    assert "self._log_frame.setFixedWidth(300)" in source
    assert "self.timeline = TimelineView(auto_scroll=False)" in source


def test_receiver_window_has_soft_present_method():
    receiver_source = Path("gui/receiver_window.py").read_text(encoding="utf-8")
    main_source = Path("gui/main_window.py").read_text(encoding="utf-8")

    assert "def present_from_sender(self, sender_geometry: QRect):" in receiver_source
    assert "self._receiver_win.present_from_sender(self.geometry())" in main_source
    assert 'b"windowOpacity"' in receiver_source
    assert 'b"pos"' in receiver_source
    assert "self.resize(target.size())" in receiver_source
    assert "sender_geometry.left() + 180" in receiver_source
