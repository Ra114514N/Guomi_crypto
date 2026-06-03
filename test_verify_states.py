"""Verify-state test harness.

Renders step-5 verification cards across all pass/fail combinations side-by-side
so you can visually confirm capsule colors, layout, and scroll stability.

Run:
    python test_verify_states.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel,
    QHBoxLayout, QPushButton, QFrame,
)

from gui import styles
from gui.timeline_view import TimelineView
from gui.step_card import StepCardWidget


# Apply deep-space dark theme
styles.apply_color_scheme("深空", True)


# Each tuple: (sig_ok, integ_ok, digest_ok, label)
SCENARIOS = [
    (True,  True,  True,  "全部通过"),
    (False, True,  True,  "单失败 · 签名"),
    (True,  False, True,  "单失败 · 完整性"),
    (True,  True,  False, "单失败 · 摘要"),
    (False, False, True,  "双失败 · 签名+完整性"),
    (False, True,  False, "双失败 · 签名+摘要"),
    (True,  False, False, "双失败 · 完整性+摘要"),
    (False, False, False, "全部失败"),
]


def fmt(ok: bool) -> str:
    return "✓ 通过" if ok else "✗ 失败"


class VerifyTestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("步骤 5 安全验证 · 多场景测试看板")
        self.resize(1100, 800)

        central = QWidget()
        central.setStyleSheet(f"background-color: {styles.background_color};")
        self.setCentralWidget(central)

        outer = QVBoxLayout(central)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.setSpacing(12)

        # Header
        title = QLabel("步骤 5 · 安全验证渲染矩阵")
        title.setStyleSheet(
            f"color: #FFFFFF; font-size: 16px; font-weight: 700; "
            f"background: transparent; font-family: {styles.current_font_family};"
        )
        outer.addWidget(title)

        subtitle = QLabel(f"覆盖 {len(SCENARIOS)} 种 (签名/完整性/摘要) 通过组合 — 滚动测试胶囊稳定性")
        subtitle.setStyleSheet(
            f"color: {styles.text_muted}; font-size: 12px; "
            f"background: transparent; font-family: {styles.current_font_family};"
        )
        outer.addWidget(subtitle)

        # Buttons row to also test step 6 conclusion
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        rebuild_btn = QPushButton("🔁  重新生成全部场景")
        rebuild_btn.setObjectName("primaryButton")
        rebuild_btn.setStyleSheet(styles.primary_button_style)
        rebuild_btn.setCursor(Qt.PointingHandCursor)
        rebuild_btn.clicked.connect(self.populate)
        btn_row.addWidget(rebuild_btn)
        btn_row.addStretch()
        outer.addLayout(btn_row)

        # Timeline
        self.timeline = TimelineView()
        outer.addWidget(self.timeline, 1)

        self.populate()

    def populate(self):
        self.timeline.clear_steps()

        for idx, (sig, integ, dig, label) in enumerate(SCENARIOS, 1):
            # Step 5 verification card
            self.timeline.add_step(
                step_number=5,
                title=f"安全验证 · 场景 {idx}: {label}",
                data={
                    "SM9 签名验证": fmt(sig),
                    "完整性验证":   fmt(integ),
                    "摘要比对":     fmt(dig),
                },
                state=StepCardWidget.STATE_SUCCESS if (sig and integ and dig)
                      else StepCardWidget.STATE_ERROR,
                animate=False,  # rendered all at once for stability
            )

            # Step 6 conclusion card (paired)
            ok = sig and integ and dig
            self.timeline.add_step(
                step_number=6,
                title=f"最终结论 · 场景 {idx}",
                data={
                    "结论": "全部验证通过 — 数据完整、来源可信" if ok
                            else "验证失败 — 安全性无法保证",
                    "输出": "artifacts/recovered.txt" if ok else "—",
                },
                state=StepCardWidget.STATE_SUCCESS if ok else StepCardWidget.STATE_ERROR,
                animate=False,
            )


def main():
    app = QApplication(sys.argv)
    win = VerifyTestWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
