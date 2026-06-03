"""Environment detection tab — calls crypto.gmssl_loader synchronously."""

import platform
import sys
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton

from gui import styles
from gui.result_view import ResultView


class EnvTab(QWidget):
    def __init__(self, log_signal: Signal, parent=None):
        super().__init__(parent)
        self._log = log_signal
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        self.info_display = ResultView(placeholder="点击「检测环境」查看系统信息...")
        layout.addWidget(self.info_display, 1)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.detect_btn = QPushButton("🔄  检测环境")
        self.detect_btn.setCursor(Qt.PointingHandCursor)
        self.detect_btn.setObjectName("primaryButton")
        self.detect_btn.clicked.connect(self._on_detect)
        btn_row.addWidget(self.detect_btn)
        layout.addLayout(btn_row)

        self._on_detect()

    def refresh_styles(self) -> None:
        self.info_display.setStyleSheet(styles.textedit_style)
        if self.detect_btn.objectName() == "primaryButton":
            self.detect_btn.setStyleSheet(styles.primary_button_style)
        else:
            self.detect_btn.setStyleSheet(styles.button_style)
        # Re-render to pick up new colors
        self._render_current()

    def _on_detect(self):
        self._render_current()
        self._log.emit("▶ 环境检测完成 — 全部算法组件状态已列出")

    def _render_current(self):
        try:
            from crypto.gmssl_loader import is_available, error_message
            from core.protocol import PROTOCOL_VERSION
            sm9_available = is_available()
            sm9_err = error_message() if not sm9_available else ""
            protocol_version = PROTOCOL_VERSION
        except Exception as exc:
            sm9_available = False
            sm9_err = str(exc)
            protocol_version = "(未知)"

        project_root = Path(__file__).resolve().parent.parent.parent
        artifacts_dir = project_root / "artifacts"
        plain_file = project_root / "plain.txt"

        v = self.info_display
        v.clear_content()

        v.section("Python 环境")
        v.kv("版本", sys.version.split("\n")[0])
        v.kv("平台", platform.platform())
        v.kv("架构", platform.machine())
        v.kv_mono("项目根目录", str(project_root))

        v.section("信封协议")
        v.kv("协议版本", f"envelope v{protocol_version}")
        v.kv("封装格式", "单文件 JSON (message.json)")

        v.section("非对称算法")
        v.badge("SM2 密钥封装", ok=True, detail="gmssl-python · sm2_wrap 模式")
        if sm9_available:
            v.badge("SM9 身份签名", ok=True, detail="已加载，可正常使用")
        else:
            v.badge("SM9 身份签名", ok=False, detail=f"加载失败 — {sm9_err}")

        v.section("对称加密算法")
        v.badge("SM4-CBC", ok=True, detail="分组加密 · PKCS7 填充")
        v.badge("SM4-CTR", ok=True, detail="计数器模式 · 无填充")
        v.badge("SM4-GCM", ok=True, detail="认证加密 · 内置完整性")
        v.badge("ZUC-128", ok=True, detail="流加密 · 祖冲之算法")

        v.section("哈希与完整性")
        v.badge("SM3 哈希", ok=True, detail="256-bit 摘要")
        v.badge("HMAC-SM3", ok=True, detail="基于 SM3 的消息认证码")
        v.badge("HKDF-SM3", ok=True, detail="密钥派生 · 上下文绑定")

        v.section("文件路径")
        v.kv_mono("默认明文文件", str(plain_file))
        v.badge("明文文件", ok=plain_file.exists(),
                detail="文件存在" if plain_file.exists() else "文件不存在")
        v.kv_mono("输出目录", str(artifacts_dir))
        v.badge("输出目录", ok=artifacts_dir.exists(),
                detail="目录存在" if artifacts_dir.exists() else "未创建")

        if artifacts_dir.exists():
            files = sorted(artifacts_dir.iterdir())
            if files:
                v.subsection(f"已有输出文件 ({len(files)})")
                for f in files[:8]:
                    v.kv(f.name, f"{f.stat().st_size} 字节")
                if len(files) > 8:
                    v.hint(f"...另外还有 {len(files) - 8} 个文件")

        v.commit()
