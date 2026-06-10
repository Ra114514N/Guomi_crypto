# Dual-Window Display Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split the single-window timeline into two independent windows (sender + receiver) with comparison blocks for HMAC and digest verification.

**Architecture:** WorkflowWorker emits step_data with a `target` field ("sender"/"receiver"). SenderWindow (the current MainWindow) handles sender steps and spawns ReceiverWindow when sending completes. ReceiverWindow renders verification steps with CompareBlock widgets showing claimed vs computed values.

**Tech Stack:** PySide6, existing styles/themes system, existing core/ crypto layer

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `core/receiver.py` | Modify | Add intermediate values to return dict |
| `gui/workers.py` | Modify | Add sender_done signal, split steps into sender/receiver targets, emit comparison data |
| `gui/data_widgets.py` | Modify | Add CompareBlock widget |
| `gui/receiver_window.py` | Create | Independent receiver window with timeline + log |
| `gui/main_window.py` | Modify | Filter sender steps, spawn ReceiverWindow, remove bench nav, add emoji labels, default ZUC |

---

### Task 1: Extend core/receiver.py return values

**Files:**
- Modify: `core/receiver.py:55-98`

- [ ] **Step 1: Add intermediate value tracking**

Add variables to capture claimed and computed values, then include them in the return dict:

```python
def receive(
    receiver_pri: str,
    receiver_pub: str,
    sm9_master_pub: object,
    output_dir: str | Path | None = None,
) -> dict:
    out = ensure_output_dir(output_dir)
    envelope = decode_envelope(load_envelope(out / "message.json"))
    header = envelope["header"]
    cipher = header["cipher"]
    mode = header.get("mode") or "cbc"
    sender_id = header["sender_id"]
    receiver_id = header["receiver_id"]
    suite_id = header["suite_id"]

    log.info("[receiver] loaded envelope, algorithm: %s", envelope["algo_meta"]["algo"])

    wrapped_secret = envelope["wrapped_secret"]
    nonce_or_iv = envelope["nonce_or_iv"]
    ct = envelope["ciphertext"]
    auth_tag = envelope["auth_tag"]
    signature = envelope["signature"]
    header_bytes = header_to_bytes(header)

    session_secret = unwrap_session_key(wrapped_secret, receiver_pri, receiver_pub)
    derived = derive_all(session_secret, context=_context_bytes(header["session_id"], sender_id, receiver_id, suite_id))
    sm4_key = derived["sm4_key"]
    zuc_key = derived["zuc_key"]
    integ_key = derived["integrity_key"]

    transcript = build_transcript(header_bytes, wrapped_secret, nonce_or_iv, ct, auth_tag)
    sig_ok = sm9_verify(signature, transcript, sm9_master_pub, sender_id)

    # Track claimed and computed HMAC for comparison display
    claimed_hmac = auth_tag.hex() if auth_tag else ""
    computed_hmac = ""

    if cipher == "sm4" and mode == "gcm":
        integrity_ok = sig_ok
    elif cipher == "sm4":
        integrity_obj = build_integrity_object(header_bytes, wrapped_secret, nonce_or_iv, ct)
        integrity_ok = verify_hmac_sm3(integ_key, integrity_obj, auth_tag)
        from crypto.sm3_integrity import hmac_sm3
        computed_hmac = hmac_sm3(integ_key, integrity_obj).hex()
    elif cipher == "zuc":
        integrity_obj = build_integrity_object(header_bytes, wrapped_secret, nonce_or_iv, ct)
        integrity_ok = verify_hmac_sm3(integ_key, integrity_obj, auth_tag)
        from crypto.sm3_integrity import hmac_sm3
        computed_hmac = hmac_sm3(integ_key, integrity_obj).hex()
    else:
        raise ValueError(f"Unknown cipher: {cipher}")

    # Track claimed and computed digest for comparison display
    claimed_digest = envelope["algo_meta"]["plain_digest_hex"]
    computed_digest = ""

    plaintext = b""
    digest_ok = False
    if integrity_ok and sig_ok:
        try:
            if cipher == "sm4":
                plaintext = sm4_decrypt(sm4_key, ct, mode=mode, iv=nonce_or_iv, tag=auth_tag if mode == "gcm" else None)
            else:
                plaintext = zuc_decrypt(zuc_key, nonce_or_iv, ct)
            computed_digest = sm3_digest(plaintext).hex()
            digest_ok = computed_digest == claimed_digest
            write_text(out / "recovered.txt", plaintext.decode("utf-8", errors="replace"))
        except Exception:
            integrity_ok = False

    result = {
        "algo_label": envelope["algo_meta"]["algo"],
        "sender_id": sender_id,
        "receiver_id": receiver_id,
        "plaintext_len": len(plaintext),
        "integrity_ok": integrity_ok,
        "signature_ok": sig_ok,
        "digest_ok": digest_ok,
        "success": integrity_ok and sig_ok and digest_ok,
        "output_dir": str(out),
        "claimed_hmac": claimed_hmac,
        "computed_hmac": computed_hmac,
        "claimed_digest": claimed_digest,
        "computed_digest": computed_digest,
    }

    if result["success"]:
        log.info("[receiver] all checks passed")
    else:
        log.warning(
            "[receiver] verification failed: integrity=%s sig=%s digest=%s",
            integrity_ok, sig_ok, digest_ok,
        )
    return result
```

- [ ] **Step 2: Verify existing tests still pass**

Run: `python -m pytest tests/test_crypto.py -v`
Expected: All 17 tests pass (receiver return dict is a superset of before)

- [ ] **Step 3: Commit**

```bash
git add core/receiver.py
git commit -m "feat: expose claimed/computed HMAC and digest from receiver for comparison display"
```

---

### Task 2: Add CompareBlock widget to data_widgets.py

**Files:**
- Modify: `gui/data_widgets.py` (append new class)

- [ ] **Step 1: Add CompareBlock class**

Append after the `ConclusionBanner` class:

```python
class CompareBlock(QFrame):
    """Upper/lower comparison display for verification data.

    Shows claimed value vs independently computed value with match/mismatch styling.
    """

    def __init__(self, title: str, claimed_label: str, claimed_value: str,
                 computed_label: str, computed_value: str, is_match: bool,
                 max_chars: int = 40, parent=None):
        super().__init__(parent)
        self._title = title
        self._claimed_label = claimed_label
        self._claimed_value = claimed_value
        self._computed_label = computed_label
        self._computed_value = computed_value
        self._is_match = is_match
        self._max_chars = max_chars

        self.setObjectName("CompareBlock")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(6)

        # Section title
        title_lbl = QLabel(self._title)
        title_lbl.setStyleSheet(
            f"color: {styles.text_muted}; font-size: 11px; font-weight: 500; "
            f"letter-spacing: 0.5px; background: transparent; "
            f"font-family: {styles.current_font_family};"
        )
        layout.addWidget(title_lbl)

        # Claimed row
        self._claimed_row = self._make_row(self._claimed_label, self._claimed_value)
        layout.addLayout(self._claimed_row)

        # Computed row
        self._computed_row = self._make_row(self._computed_label, self._computed_value)
        layout.addLayout(self._computed_row)

        # Badge
        if self._is_match:
            badge_text = "✓ 一致"
            badge_style = self._badge_pass_style()
        else:
            badge_text = "✗ 不一致"
            badge_style = self._badge_fail_style()

        badge = QLabel(badge_text)
        badge.setStyleSheet(badge_style)
        badge.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
        layout.addWidget(badge)

        self._apply_frame_style()

    def _make_row(self, label_text: str, value_text: str) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(10)
        row.setContentsMargins(0, 0, 0, 0)

        label = QLabel(label_text)
        label.setFixedWidth(90)
        label.setStyleSheet(
            f"color: {styles.text_muted}; font-size: 12px; background: transparent; "
            f"font-family: {styles.current_font_family};"
        )
        row.addWidget(label)

        display = value_text
        if len(value_text) > self._max_chars:
            display = value_text[:self._max_chars] + "..."

        value_lbl = QLabel(display)
        value_lbl.setToolTip(value_text)
        value_lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)

        if self._is_match:
            color = styles.capsule_pass_text if styles.capsule_pass_text else styles.success_color
            bg = styles.capsule_pass_bg if styles.capsule_pass_bg else "rgba(16, 185, 129, 0.1)"
            border = styles.capsule_pass_border if styles.capsule_pass_border else styles.success_color
        else:
            color = styles.capsule_fail_text if styles.capsule_fail_text else styles.error_color
            bg = styles.capsule_fail_bg if styles.capsule_fail_bg else "rgba(239, 68, 68, 0.08)"
            border = styles.capsule_fail_border if styles.capsule_fail_border else styles.error_color

        value_lbl.setStyleSheet(
            f"color: {color}; background-color: {bg}; border: 1px solid {border}; "
            f"border-radius: 4px; padding: 3px 8px; "
            f"font-family: {styles.mono_font_family}; font-size: 12px;"
        )
        row.addWidget(value_lbl, 1)
        return row

    def _apply_frame_style(self):
        self.setStyleSheet(
            f"QFrame#CompareBlock {{"
            f"  background-color: {styles.mono_bg};"
            f"  border: 1px solid {styles.card_border};"
            f"  border-radius: 8px;"
            f"}}"
        )

    def _badge_pass_style(self) -> str:
        color = styles.capsule_pass_text if styles.capsule_pass_text else styles.success_color
        bg = styles.capsule_pass_bg if styles.capsule_pass_bg else "rgba(16, 185, 129, 0.1)"
        border = styles.capsule_pass_border if styles.capsule_pass_border else styles.success_color
        return (
            f"color: {color}; background-color: {bg}; border: 1px solid {border}; "
            f"border-radius: 12px; padding: 4px 12px; font-size: 12px; font-weight: 600; "
            f"font-family: {styles.current_font_family};"
        )

    def _badge_fail_style(self) -> str:
        color = styles.capsule_fail_text if styles.capsule_fail_text else styles.error_color
        bg = styles.capsule_fail_bg if styles.capsule_fail_bg else "rgba(239, 68, 68, 0.08)"
        border = styles.capsule_fail_border if styles.capsule_fail_border else styles.error_color
        return (
            f"color: {color}; background-color: {bg}; border: 1px solid {border}; "
            f"border-radius: 12px; padding: 4px 12px; font-size: 12px; font-weight: 600; "
            f"font-family: {styles.current_font_family};"
        )
```

- [ ] **Step 2: Verify import works**

Run: `python -c "from gui.data_widgets import CompareBlock; print('OK')"`
Expected: OK

- [ ] **Step 3: Commit**

```bash
git add gui/data_widgets.py
git commit -m "feat: add CompareBlock widget for verification data comparison"
```

---

### Task 3: Rewrite WorkflowWorker with target-based step emission

**Files:**
- Modify: `gui/workers.py`

- [ ] **Step 1: Add sender_done signal and rewrite run() method**

The worker keeps the same constructor. Changes:
1. Add `sender_done = Signal()` 
2. Each `step_data.emit(...)` dict gets a `"target"` field
3. After send + tamper, emit `sender_done`
4. Receiver steps split into 5 (load/unseal, SM9 verify, HMAC compare, digest compare, conclusion)
5. HMAC and digest steps include claimed/computed values

```python
class WorkflowWorker(QThread):
    progress = Signal(str)
    step_data = Signal(dict)
    sender_done = Signal()
    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, plaintext_path: str, cipher: str, mode: str,
                 sender_id: str = "sender@sm9.local", attack: str = "none", parent=None):
        super().__init__(parent)
        self._path = plaintext_path
        self._cipher = cipher
        self._mode = mode
        self._sender_id = sender_id
        self._attack = attack or "none"

    def run(self):
        handler = SignalHandler(self.progress)
        handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
        root_logger = logging.getLogger()
        root_logger.addHandler(handler)
        try:
            from crypto.sm9_signature import generate_master_key
            from crypto.sm2_kex_or_wrap import generate_sm2_keypair
            from crypto.key_utils import save_key_hex
            from crypto.file_utils import ensure_output_dir
            from core.sender import send
            from core.receiver import receive

            out = ensure_output_dir(ARTIFACTS)

            # === SENDER STEPS ===

            # Sender Step 1: SM9 master key
            self.step_data.emit({"target": "sender", "step": 1,
                                 "title": "生成 SM9 主密钥对",
                                 "state": "running", "data": {}})
            self.progress.emit("▶ 发送端 1/3: 初始化 SM9 主密钥对")
            sm9_master, _ = generate_master_key()
            self.step_data.emit({"target": "sender", "step": 1,
                                 "title": "生成 SM9 主密钥对",
                                 "state": "success",
                                 "data": {"算法": "SM9 (GB/T 38635)",
                                          "用途": "身份签名 / 验签"}})
            self.progress.emit("  ✓ SM9 主密钥生成完成")

            # Sender Step 2: SM2 keypair
            self.step_data.emit({"target": "sender", "step": 2,
                                 "title": "生成 SM2 接收方密钥对",
                                 "state": "running", "data": {}})
            self.progress.emit("▶ 发送端 2/3: 生成 SM2 接收方密钥对")
            receiver_pri, receiver_pub = generate_sm2_keypair()
            save_key_hex(out / "receiver_pri.txt", receiver_pri)
            save_key_hex(out / "receiver_pub.txt", receiver_pub)
            self.step_data.emit({"target": "sender", "step": 2,
                                 "title": "生成 SM2 接收方密钥对",
                                 "state": "success",
                                 "data": {"公钥": receiver_pub[:48] + "...",
                                          "存储": str(out)}})
            self.progress.emit(f"  ✓ SM2 公钥: {receiver_pub[:32]}...")

            # Sender Step 3: Send (encrypt + sign + envelope)
            self.step_data.emit({"target": "sender", "step": 3,
                                 "title": "加密·签名·封装",
                                 "state": "running", "data": {}})
            self.progress.emit("▶ 发送端 3/3: 加密、签名、封装")
            send_result = send(
                plaintext_path=self._path,
                receiver_pub=receiver_pub,
                sm9_master_key=sm9_master,
                sender_id=self._sender_id,
                cipher=self._cipher,
                mode=self._mode,
                output_dir=out,
            )
            meta = send_result["meta"]
            self.step_data.emit({"target": "sender", "step": 3,
                                 "title": "加密·签名·封装",
                                 "state": "success",
                                 "data": {
                                     "加密算法": send_result["algo_label"],
                                     "明文摘要": send_result["plain_digest"][:32] + "...",
                                     "密文长度": f"{meta['algo_meta']['ciphertext_len']} 字节",
                                     "认证标签": meta["auth_tag_b64"][:32] + "...",
                                     "SM9 签名": meta["signature_b64"][:32] + "...",
                                 }})
            self.progress.emit(f"  ✓ 信封已写入: {out}/message.json")

            # Attack simulation
            if self._attack != "none":
                self._tamper_envelope(out / "message.json")

            # Signal sender done — triggers ReceiverWindow spawn
            self.sender_done.emit()

            # === RECEIVER STEPS ===

            self.progress.emit("━━━ 接收端开始 ━━━")

            # Receiver Step 1: Load + unseal
            self.step_data.emit({"target": "receiver", "step": 1,
                                 "title": "加载信封 · SM2 解封",
                                 "state": "running", "data": {}})
            self.progress.emit("▶ 接收端 1/5: 加载信封、SM2 解封")

            recv_result = receive(
                receiver_pri=receiver_pri,
                receiver_pub=receiver_pub,
                sm9_master_pub=sm9_master,
                output_dir=out,
            )

            self.step_data.emit({"target": "receiver", "step": 1,
                                 "title": "加载信封 · SM2 解封",
                                 "state": "success",
                                 "data": {"算法": recv_result["algo_label"],
                                          "会话秘密": "已恢复 (16 字节)"}})
            self.progress.emit("  ✓ 会话秘密已恢复")

            sig_ok = recv_result["signature_ok"]
            int_ok = recv_result["integrity_ok"]
            dig_ok = recv_result["digest_ok"]

            # Receiver Step 2: SM9 signature verification (badge only)
            self.step_data.emit({"target": "receiver", "step": 2,
                                 "title": "SM9 签名验证",
                                 "state": "running", "data": {}})
            self.progress.emit("▶ 接收端 2/5: SM9 签名验证")
            self.step_data.emit({"target": "receiver", "step": 2,
                                 "title": "SM9 签名验证",
                                 "state": "success" if sig_ok else "error",
                                 "data": {
                                     "SM9 签名验证": "✓ 通过 — 来源可信" if sig_ok else "✗ 失败 — 数据可能被篡改",
                                 }})
            self.progress.emit(f"  {'✓' if sig_ok else '✗'} 签名验证: {'通过' if sig_ok else '失败'}")

            # Receiver Step 3: HMAC integrity (compare block)
            self.step_data.emit({"target": "receiver", "step": 3,
                                 "title": "HMAC 完整性验证" if self._mode != "gcm" else "GCM 认证标签验证",
                                 "state": "running", "data": {}})
            self.progress.emit("▶ 接收端 3/5: 完整性验证")

            if self._cipher == "sm4" and self._mode == "gcm":
                # GCM mode: no independent HMAC, just badge
                self.step_data.emit({"target": "receiver", "step": 3,
                                     "title": "GCM 认证标签验证",
                                     "state": "success" if int_ok else "error",
                                     "data": {
                                         "GCM 认证": "✓ 通过" if int_ok else "✗ 失败",
                                     }})
            else:
                # CBC/CTR/ZUC: compare block with claimed vs computed
                self.step_data.emit({"target": "receiver", "step": 3,
                                     "title": "HMAC 完整性验证",
                                     "state": "success" if int_ok else "error",
                                     "data": {
                                         "_compare": True,
                                         "_compare_title": "HMAC-SM3 对比",
                                         "_claimed_label": "信封声称值",
                                         "_claimed_value": recv_result["claimed_hmac"],
                                         "_computed_label": "独立计算值",
                                         "_computed_value": recv_result["computed_hmac"],
                                         "_is_match": int_ok,
                                     }})
            self.progress.emit(f"  {'✓' if int_ok else '✗'} 完整性: {'通过' if int_ok else '失败'}")

            # Receiver Step 4: Digest comparison
            self.step_data.emit({"target": "receiver", "step": 4,
                                 "title": "SM3 摘要比对",
                                 "state": "running", "data": {}})
            self.progress.emit("▶ 接收端 4/5: SM3 摘要比对")
            computed_digest_display = recv_result["computed_digest"] if recv_result["computed_digest"] else "（解密失败，无法计算）"
            self.step_data.emit({"target": "receiver", "step": 4,
                                 "title": "SM3 摘要比对",
                                 "state": "success" if dig_ok else "error",
                                 "data": {
                                     "_compare": True,
                                     "_compare_title": "SM3 明文摘要对比",
                                     "_claimed_label": "信封声称值",
                                     "_claimed_value": recv_result["claimed_digest"],
                                     "_computed_label": "解密后计算",
                                     "_computed_value": computed_digest_display,
                                     "_is_match": dig_ok,
                                 }})
            self.progress.emit(f"  {'✓' if dig_ok else '✗'} 摘要: {'通过' if dig_ok else '失败'}")

            # Receiver Step 5: Conclusion
            all_ok = recv_result["success"]
            self.step_data.emit({"target": "receiver", "step": 5,
                                 "title": "最终结论",
                                 "state": "success" if all_ok else "error",
                                 "data": {
                                     "结论": "全部验证通过 — 数据完整、来源可信" if all_ok
                                             else "验证失败 — 安全性无法保证",
                                     "输出": f"{out}/recovered.txt" if all_ok else "—",
                                 }})
            self.progress.emit("✓ 流程完成" if all_ok else "✗ 验证失败")

            result = {"send": send_result, "receive": recv_result, "_sm9_master": sm9_master}
            self.finished.emit(result)
        except Exception as exc:
            self.error.emit(str(exc))
        finally:
            root_logger.removeHandler(handler)
```

Keep the existing `_tamper_envelope` and `_flip_b64` methods unchanged.

- [ ] **Step 2: Verify import works**

Run: `python -c "from gui.workers import WorkflowWorker; print('OK')"`
Expected: OK

- [ ] **Step 3: Commit**

```bash
git add gui/workers.py
git commit -m "feat: split worker steps into sender/receiver targets with comparison data"
```

---

### Task 4: Create ReceiverWindow

**Files:**
- Create: `gui/receiver_window.py`

- [ ] **Step 1: Write the ReceiverWindow class**

```python
"""Receiver window — independent display for receive-side verification steps."""

from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QFrame, QLabel, QPushButton, QGraphicsOpacityEffect,
)

from gui import styles
from gui.effects import add_drop_shadow
from gui.log_widget import LogWidget
from gui.timeline_view import TimelineView
from gui.data_widgets import CompareBlock, VerifyCapsule, ConclusionBanner
from gui.step_card import StepCardWidget


class _ThemeOverlay(QWidget):
    """Overlay for smooth theme transition in receiver window."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self._pixmap = QPixmap()
        self._opacity_effect = QGraphicsOpacityEffect(self)
        self._opacity_effect.setOpacity(1.0)
        self.setGraphicsEffect(self._opacity_effect)

    @property
    def opacity_effect(self):
        return self._opacity_effect

    def set_old_skin(self, pixmap: QPixmap):
        self._pixmap = pixmap
        self.resize(self.parent().size())
        self.raise_()
        self.show()

    def paintEvent(self, event):
        if not self._pixmap.isNull():
            painter = QPainter(self)
            painter.drawPixmap(0, 0, self._pixmap)
            painter.end()

    def resizeEvent(self, event):
        if self.parent():
            self.resize(self.parent().size())


class ReceiverWindow(QMainWindow):
    """Independent receiver-side window showing verification timeline."""

    def __init__(self, is_dark: bool = False, parent=None):
        super().__init__(parent)
        self._is_dark = is_dark
        self._drag_pos = None

        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMinimumSize(620, 520)
        self.resize(680, 620)
        self.setWindowTitle("📥 基于国密算法的安全数据传输与身份认证系统 — 接收端")

        self._build_ui()
        self._apply_theme()

    def _build_ui(self):
        central = QWidget(objectName="central")
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self._build_title_bar(main_layout)
        self._build_body(main_layout)

        add_drop_shadow(central, blur=32, dx=0, dy=6, alpha=85)

    def _build_title_bar(self, parent_layout: QVBoxLayout):
        self._title_bar = QFrame(objectName="titleBar")
        self._title_bar.setFixedHeight(44)
        layout = QHBoxLayout(self._title_bar)
        layout.setContentsMargins(16, 0, 10, 0)
        layout.setSpacing(12)

        title = QLabel("📥 基于国密算法的安全数据传输与身份认证系统 — 接收端")
        title.setObjectName("titleLabel")
        title.setFont(QFont(styles.current_font_family, 11, QFont.Bold))
        layout.addWidget(title)
        layout.addStretch()

        # Window controls
        self._min_btn = self._win_btn("—", "WinMinButton")
        self._min_btn.clicked.connect(self.showMinimized)
        layout.addWidget(self._min_btn)

        self._max_btn = self._win_btn("□", "WinMaxButton")
        self._max_btn.clicked.connect(self._toggle_maximize)
        layout.addWidget(self._max_btn)

        self._close_btn = self._win_btn("×", "WinCloseButton")
        self._close_btn.clicked.connect(self.close)
        layout.addWidget(self._close_btn)

        parent_layout.addWidget(self._title_bar)

    def _build_body(self, parent_layout: QVBoxLayout):
        body = QWidget()
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        # Timeline (main area)
        self.timeline = TimelineView()
        body_layout.addWidget(self.timeline, 1)

        # Log panel
        self._log_frame = QFrame(objectName="logPanel")
        self._log_frame.setFixedWidth(250)
        log_layout = QVBoxLayout(self._log_frame)
        log_layout.setContentsMargins(0, 8, 8, 8)
        log_layout.setSpacing(4)

        lbl = QLabel(">_ 日志")
        lbl.setStyleSheet(
            f"color: {styles.text_muted}; font-size: 11px; font-weight: 600; background: transparent;"
        )
        log_layout.addWidget(lbl)

        self.log_output = LogWidget()
        log_layout.addWidget(self.log_output)

        body_layout.addWidget(self._log_frame)
        parent_layout.addWidget(body, 1)

    # ── Public API ─────────────────────────────────────────────

    def on_step_data(self, data: dict):
        """Receive a step_data dict targeted at this window."""
        step = data["step"]
        title = data["title"]
        state = data["state"]
        kv = data.get("data", {})

        current_count = len(self.timeline._cards)

        if state == "running":
            self.timeline.add_step(step, title, state="running", animate=True)
        elif step > current_count:
            card = self.timeline.add_step(step, title, data=kv, state=state, animate=True)
        else:
            self.timeline.update_last_card_state(state)
            if kv:
                cards = self.timeline._cards
                if cards:
                    cards[-1].set_data_rows(kv)

    def on_progress(self, text: str):
        """Append a log message."""
        self.log_output.append_message(text)

    def sync_theme(self, is_dark: bool):
        """Synchronize theme with sender window."""
        if self._is_dark == is_dark:
            return

        old_skin = self.grab()
        overlay = _ThemeOverlay(self)
        overlay.set_old_skin(old_skin)
        overlay.repaint()

        self._is_dark = is_dark
        self._apply_theme()

        anim = QPropertyAnimation(overlay.opacity_effect, b"opacity", self)
        anim.setDuration(450)
        anim.setEasingCurve(QEasingCurve.InOutQuad)
        anim.setStartValue(1.0)
        anim.setEndValue(0.0)
        anim.finished.connect(overlay.deleteLater)
        anim.start()
        self._theme_anim = anim

    # ── Internal ───────────────────────────────────────────────

    def _apply_theme(self):
        styles.apply_color_scheme("默认", self._is_dark)
        styles.update_styles()

        central = self.centralWidget()
        central.setStyleSheet(styles.main_window_style)
        self._title_bar.setStyleSheet(styles.title_bar_style)

        self._log_frame.setStyleSheet(
            f"QFrame#logPanel {{ background-color: {styles.surface_color}; "
            f"border-left: 1px solid {styles.border_subtle}; }}"
        )

        self.log_output.setStyleSheet(styles.log_style)

        for btn in (self._min_btn, self._max_btn, self._close_btn):
            btn.setStyleSheet(styles.win_control_style)

        self.timeline.refresh_styles()

    def _win_btn(self, glyph: str, name: str) -> QPushButton:
        btn = QPushButton(glyph)
        btn.setObjectName(name)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(styles.win_control_style)
        return btn

    def _toggle_maximize(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    # ── Frameless Drag ─────────────────────────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and event.position().y() < 44:
            self._drag_pos = (event.globalPosition().toPoint()
                              - self.frameGeometry().topLeft())
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() & Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
```

- [ ] **Step 2: Verify import works**

Run: `python -c "from gui.receiver_window import ReceiverWindow; print('OK')"`
Expected: OK

- [ ] **Step 3: Commit**

```bash
git add gui/receiver_window.py
git commit -m "feat: add independent ReceiverWindow for receiver-side verification display"
```

---

### Task 5: Update StepCard routing to handle CompareBlock data

**Files:**
- Modify: `gui/step_card.py`

- [ ] **Step 1: Add _compare routing in set_data_rows()**

In `set_data_rows()`, add a check before the default bucket logic:

```python
def set_data_rows(self, data: dict[str, str], animate: bool = True) -> None:
    """Smart-route data into appropriate widgets based on step + content."""
    self._last_data = data
    self._clear_data_layout()

    if not data:
        return

    # CompareBlock routing: data contains _compare flag
    if data.get("_compare"):
        self._render_compare(data)
        return

    # Step 5 equivalent: verification capsule (single pass/fail badge)
    # Detect capsule data: single key-value where value starts with ✓ or ✗
    if len(data) == 1:
        key, value = next(iter(data.items()))
        if isinstance(value, str) and (value.startswith("✓") or value.startswith("✗")):
            ok = value.startswith("✓")
            self._data_layout.addWidget(VerifyCapsuleRow([(key, ok)], animate=animate))
            return

    # Step 6: conclusion banner
    if "结论" in data:
        self._render_conclusion(data)
        return

    # Default: bucket short vs. long data
    short_items: list[tuple[str, str]] = []
    long_items: list[tuple[str, str]] = []
    for key, value in data.items():
        value = str(value)
        if len(value) > LONG_VALUE_THRESHOLD:
            long_items.append((key, value))
        else:
            short_items.append((key, value))

    if short_items:
        row = QHBoxLayout()
        row.setSpacing(28)
        row.setContentsMargins(0, 0, 0, 0)
        for key, value in short_items:
            row.addWidget(MetaCell(key, value))
        row.addStretch()
        self._data_layout.addLayout(row)

    for key, value in long_items:
        self._data_layout.addWidget(LongDataRow(key, value))
```

- [ ] **Step 2: Add _render_compare method**

```python
def _render_compare(self, data: dict) -> None:
    """Render a CompareBlock from _compare data."""
    from gui.data_widgets import CompareBlock
    block = CompareBlock(
        title=data["_compare_title"],
        claimed_label=data["_claimed_label"],
        claimed_value=data["_claimed_value"],
        computed_label=data["_computed_label"],
        computed_value=data["_computed_value"],
        is_match=data["_is_match"],
    )
    self._data_layout.addWidget(block)
```

- [ ] **Step 3: Update imports at top of file**

Add `VerifyCapsuleRow` to the import from data_widgets (it's already imported, just verify).

- [ ] **Step 4: Verify import works**

Run: `python -c "from gui.step_card import StepCardWidget; print('OK')"`
Expected: OK

- [ ] **Step 5: Commit**

```bash
git add gui/step_card.py
git commit -m "feat: add CompareBlock and single-capsule routing to StepCard"
```

---

### Task 6: Update MainWindow (SenderWindow) — spawn receiver, filter steps, UI tweaks

**Files:**
- Modify: `gui/main_window.py`

- [ ] **Step 1: Change algorithm default to ZUC**

In `_build_top_bar`, reorder combo items so ZUC is first (default):

```python
self.algo_combo = QComboBox()
self.algo_combo.addItems(["zuc", "sm4-gcm", "sm4-cbc", "sm4-ctr"])
self.algo_combo.setFixedWidth(110)
```

- [ ] **Step 2: Add emoji labels to controls**

Before algo_combo add a label:
```python
algo_label = QLabel("🔐")
algo_label.setStyleSheet("background: transparent; font-size: 14px;")
layout.addWidget(algo_label)
```

Before attack_combo:
```python
attack_label = QLabel("⚔️")
attack_label.setStyleSheet("background: transparent; font-size: 14px;")
layout.addWidget(attack_label)
```

Before file_edit:
```python
file_label = QLabel("📁")
file_label.setStyleSheet("background: transparent; font-size: 14px;")
layout.addWidget(file_label)
```

- [ ] **Step 3: Remove benchmark from navigation**

Change `nav_items` to:
```python
nav_items = [
    ("demo", "◈\n演示"),
    ("send_recv", "◈\n收发"),
    ("env", "◈\n环境"),
]
```

Remove benchmark tab creation from `_build_center`:
```python
def _build_center(self, parent_layout: QHBoxLayout):
    self._stack = QStackedWidget()

    # Page 0: Timeline (demo + send/recv share this)
    self.timeline = TimelineView()
    self._stack.addWidget(self.timeline)

    # Page 1: Env tab
    self.env_tab = EnvTab(self.log_message)
    self._stack.addWidget(self.env_tab)

    self._stack.setCurrentIndex(0)
    parent_layout.addWidget(self._stack, 1)
```

Update `_on_nav` to remove bench case:
```python
def _on_nav(self, key: str):
    for k, btn in self._nav_buttons.items():
        btn.setChecked(k == key)
    self._current_nav = key

    if key == "demo" or key == "send_recv":
        self._stack.setCurrentIndex(0)
    elif key == "env":
        self._stack.setCurrentIndex(1)
```

Remove benchmark refresh from `_apply_theme`:
```python
# Delete these lines:
# if hasattr(self, 'benchmark_tab') and hasattr(self.benchmark_tab, 'refresh_styles'):
#     self.benchmark_tab.refresh_styles()
```

Remove `from gui.tabs.benchmark_tab import BenchmarkTab` from imports.

- [ ] **Step 4: Add ReceiverWindow spawning and step routing**

Add import at top:
```python
from gui.receiver_window import ReceiverWindow
```

Add `self._receiver_win = None` in `__init__`.

Update `_on_execute`:
```python
def _on_execute(self):
    from gui.workers import WorkflowWorker

    path = self.file_edit.text().strip()
    if not path or not Path(path).exists():
        self.log_message.emit("✗ 错误: 明文文件不存在")
        return

    value = self.algo_combo.currentText()
    if value == "zuc":
        cipher, mode = "zuc", "cbc"
    else:
        cipher, mode = "sm4", value.split("-")[1]

    self.run_btn.setEnabled(False)
    self.busy_dot.set_color(styles.warning_color)
    self.busy_dot.start()
    self.timeline.clear_steps()
    attack = self.attack_combo.currentData()
    if attack and attack != "none":
        self.log_message.emit(
            f"▶ 启动演示: {cipher.upper()}-{mode.upper()} | ⚠ 攻击模拟: {self.attack_combo.currentText()}"
        )
    else:
        self.log_message.emit(f"▶ 启动演示: {cipher.upper()}-{mode.upper()}")

    self._on_nav("demo")

    # Close previous receiver window if any
    if self._receiver_win:
        self._receiver_win.close()
        self._receiver_win = None

    self._exec_worker = WorkflowWorker(path, cipher, mode, attack=attack)
    self._exec_worker.progress.connect(self.log_message.emit)
    self._exec_worker.step_data.connect(self._on_step_data)
    self._exec_worker.sender_done.connect(self._on_sender_done)
    self._exec_worker.finished.connect(self._on_exec_done)
    self._exec_worker.error.connect(self._on_exec_error)
    self._exec_worker.start()
```

Add new methods:
```python
def _on_sender_done(self):
    """Sender steps complete — spawn receiver window."""
    self._receiver_win = ReceiverWindow(is_dark=self._is_dark)
    icon_path = self._resolve_asset("logo.ico")
    if icon_path.exists():
        self._receiver_win.setWindowIcon(QIcon(str(icon_path)))
    self._receiver_win.show()
    self.log_message.emit("📤 信封已发送 → 接收端窗口已打开")
```

Update `_on_step_data`:
```python
def _on_step_data(self, data: dict):
    target = data.get("target", "sender")

    if target == "receiver":
        if self._receiver_win:
            self._receiver_win.on_step_data(data)
        return

    # Sender steps — render in this window's timeline
    step = data["step"]
    title = data["title"]
    state = data["state"]
    kv = data.get("data", {})

    current_count = len(self.timeline._cards)

    if state == "running":
        self.timeline.add_step(step, title, state="running", animate=True)
    elif step > current_count:
        card = self.timeline.add_step(step, title, data=kv, state=state, animate=True)
    else:
        self.timeline.update_last_card_state(state)
        if kv:
            cards = self.timeline._cards
            if cards:
                cards[-1].set_data_rows(kv)
```

- [ ] **Step 5: Sync theme to receiver and handle close**

Update `_toggle_dark_mode`:
```python
def _toggle_dark_mode(self):
    old_skin = self.grab()

    overlay = ThemeTransitionOverlay(self)
    overlay.set_old_skin(old_skin)
    overlay.repaint()

    self._is_dark = not self._is_dark
    self._apply_theme()

    anim = QPropertyAnimation(overlay.opacity_effect, b"opacity", self)
    anim.setDuration(450)
    anim.setEasingCurve(QEasingCurve.InOutQuad)
    anim.setStartValue(1.0)
    anim.setEndValue(0.0)
    anim.finished.connect(overlay.deleteLater)
    anim.start()
    self._theme_anim = anim

    # Sync receiver window theme
    if self._receiver_win and self._receiver_win.isVisible():
        self._receiver_win.sync_theme(self._is_dark)

    mode = "深色" if self._is_dark else "浅色"
    self.log_message.emit(f"▶ 切换为{mode}模式")
```

Add `closeEvent`:
```python
def closeEvent(self, event):
    if self._receiver_win:
        self._receiver_win.close()
    super().closeEvent(event)
```

- [ ] **Step 6: Forward receiver progress to receiver window log**

In `_on_execute`, connect progress to receiver window too. Since receiver window doesn't exist yet at connection time, filter in the progress handler:

Add after sender_done connect:
```python
self._exec_worker.progress.connect(self._forward_receiver_log)
```

Add method:
```python
def _forward_receiver_log(self, text: str):
    """Forward receiver-related log messages to receiver window."""
    if self._receiver_win and ("接收端" in text or "━━━" in text):
        self._receiver_win.on_progress(text)
```

- [ ] **Step 7: Update window title**

In `_build_top_bar`, change title label:
```python
self.title_label = QLabel("📤 基于国密算法的安全数据传输与身份认证系统 — 发送端")
```

- [ ] **Step 8: Verify app launches**

Run: `python -c "from gui.main_window import MainWindow; print('OK')"`
Expected: OK

- [ ] **Step 9: Commit**

```bash
git add gui/main_window.py
git commit -m "feat: dual-window architecture — sender spawns receiver, filter steps, remove bench nav"
```

---

### Task 7: Integration test — run the full app

**Files:** None (manual verification)

- [ ] **Step 1: Run app**

Run: `python gui/run.py`

- [ ] **Step 2: Verify sender window**

- Title shows "📤 基于国密算法的安全数据传输与身份认证系统 — 发送端"
- Default algorithm is ZUC
- Emoji labels visible: 🔐 ⚔️ 📁
- Navigation has only: 演示 / 收发 / 环境 (no 性能)

- [ ] **Step 3: Run normal demo**

- Click ⚡启动演示
- Sender window shows 3 steps
- Receiver window pops up automatically
- Receiver shows: 加载解封 → SM9验签(badge) → HMAC对比(CompareBlock) → 摘要对比(CompareBlock) → 结论

- [ ] **Step 4: Test attack scenario**

- Select "篡改密文" attack
- Re-run demo
- Verify receiver window shows red mismatch in CompareBlock

- [ ] **Step 5: Test theme switch**

- Click ◑ in sender window
- Both windows transition smoothly
- CompareBlock colors update correctly

- [ ] **Step 6: Final commit**

```bash
git add -A
git commit -m "feat: dual-window display with verification comparison — complete"
```
