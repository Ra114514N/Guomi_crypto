"""自动截图采集：启动演示 → 等收发两窗口完成 → 各截一张深浅主题图。

用法：
    python tools/capture_demo.py [输出前缀] [攻击键]

攻击键：none / ciphertext / nonce / receiver_id / filename / signature

产物（默认前缀 docs_screenshot，已被 .gitignore 覆盖）：
    {prefix}_sender_light.png / {prefix}_receiver_light.png
    {prefix}_receiver_light_bottom.png（接收端滚动到底，含最终结论）
    {prefix}_sender_dark.png  / {prefix}_receiver_dark.png
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

PREFIX = sys.argv[1] if len(sys.argv) > 1 else "docs_screenshot"
ATTACK = sys.argv[2] if len(sys.argv) > 2 else "none"
SETTLE_MS = 2400          # 等卡片入场/胶囊多米诺动画结束
THEME_SETTLE_MS = 900     # 等主题过渡 overlay 淡出


def main() -> None:
    app = QApplication(sys.argv)

    from gui.main_window import MainWindow

    win = MainWindow()
    win.show()

    idx = win.attack_combo.findData(ATTACK)
    if idx >= 0:
        win.attack_combo.setCurrentIndex(idx)

    def grab_pair(suffix: str) -> None:
        win.grab().save(str(ROOT / f"{PREFIX}_sender_{suffix}.png"))
        recv = win._receiver_win
        if recv is not None:
            recv.grab().save(str(ROOT / f"{PREFIX}_receiver_{suffix}.png"))
            bar = recv.timeline._scroll.verticalScrollBar()
            if bar.maximum() > 0:
                bar.setValue(bar.maximum())
                recv.repaint()
                recv.grab().save(str(ROOT / f"{PREFIX}_receiver_{suffix}_bottom.png"))
                bar.setValue(0)
        print(f"captured {suffix}")

    def on_poll() -> None:
        worker = win._exec_worker
        if worker is None or not worker.isFinished():
            return
        poll.stop()
        QTimer.singleShot(SETTLE_MS, capture_light)

    def capture_light() -> None:
        grab_pair("light")
        win._toggle_dark_mode()
        QTimer.singleShot(THEME_SETTLE_MS, capture_dark)

    def capture_dark() -> None:
        grab_pair("dark")
        app.quit()

    poll = QTimer()
    poll.timeout.connect(on_poll)
    poll.start(300)

    QTimer.singleShot(600, win._on_execute)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
