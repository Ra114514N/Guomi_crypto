"""Drive the real MainWindow timeline through a FAILED verification scenario.

This feeds failure step_data into the actual _on_step_data signal handler so
you see the real demo UI: step-5 capsules turning red and the step-6
conclusion banner showing the security warning — exactly as if a tampered
envelope had been received.

Run:
    python demo_fail.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from gui.main_window import MainWindow


# A scripted "tampered ciphertext" run: signature OK, but integrity + digest FAIL.
FAILURE_STEPS = [
    {"step": 1, "title": "生成 SM9 主密钥对", "state": "running", "data": {}},
    {"step": 1, "title": "生成 SM9 主密钥对", "state": "success",
     "data": {"算法": "SM9 (GB/T 38635)", "用途": "身份签名 / 验签"}},

    {"step": 2, "title": "生成 SM2 接收方密钥对", "state": "running", "data": {}},
    {"step": 2, "title": "生成 SM2 接收方密钥对", "state": "success",
     "data": {"公钥": "04a8b9c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9...",
              "存储": "artifacts"}},

    {"step": 3, "title": "发送端 — 加密·签名·封装", "state": "running", "data": {}},
    {"step": 3, "title": "发送端 — 加密·签名·封装", "state": "success",
     "data": {"加密算法": "SM4-CBC",
              "明文摘要": "215bc06e279d61a580fc663800adf952...",
              "密文长度": "943 字节",
              "认证标签": "wTSPu6vv0YEXw+9AzP9jKw==",
              "SM9 签名": "MGYEIJt7BUqdat7ALvcqapr/wudYZk7..."}},

    # ⚠ Attacker tampers with ciphertext in transit
    {"step": 4, "title": "接收端 — 解封·验签·解密", "state": "running", "data": {}},
    {"step": 4, "title": "接收端 — 解封·验签·解密", "state": "error",
     "data": {"恢复明文": "0 字节 (解密中止)", "算法": "SM4-CBC"}},

    # Verification: signature passes (header intact) but integrity + digest fail
    {"step": 5, "title": "安全验证", "state": "running", "data": {}},
    {"step": 5, "title": "安全验证", "state": "error",
     "data": {"SM9 签名验证": "✓ 通过",
              "完整性验证": "✗ 失败",
              "摘要比对": "✗ 失败"}},

    {"step": 6, "title": "最终结论", "state": "error",
     "data": {"结论": "验证失败 — 安全性无法保证",
              "输出": "—"}},
]


def main():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()

    # Make sure we're on the timeline page and it's clear
    win._on_nav("demo")
    win.timeline.clear_steps()
    win.busy_dot.start()
    win.log_message.emit("▶ [演示] 模拟密文在传输中被篡改的攻击场景")

    # Feed steps with realistic spacing so the domino + state changes are visible
    delay = 400
    for s in FAILURE_STEPS:
        QTimer.singleShot(delay, lambda d=s: win._on_step_data(d))
        # running→result pairs get a longer gap to show the busy state
        delay += 700

    def finish():
        win.busy_dot.stop()
        win.log_message.emit("✗ [演示] 完整性与摘要校验失败 — 数据已被篡改，拒绝接受")

    QTimer.singleShot(delay + 600, finish)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
