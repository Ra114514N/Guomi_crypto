# 双窗口展示方案设计

> 日期：2026-06-03
> 状态：已确认，待实现

## 目标

将现有单窗口时间线展示重构为"发送端 + 接收端"两个独立窗口，接收端窗口中对 HMAC 和摘要进行上下对比展示，直观证明系统确实执行了安全验证。

## 约束

- 当前阶段仅做视觉分离，仍为同进程同 worker 线程
- SM9 主密钥对象不可跨进程，send/receive 必须在同一 worker 中完成
- core/ 层只做最小改动（增加返回字段），不改逻辑
- 保留深浅主题切换能力，两个窗口共享主题状态

## 架构

### 窗口职责

| | 发送端 (SenderWindow) | 接收端 (ReceiverWindow) |
|---|---|---|
| 窗口标题 | 📤 基于国密算法的安全数据传输与身份认证系统 — 发送端 | 📥 基于国密算法的安全数据传输与身份认证系统 — 接收端 |
| 控制栏 | 🔐算法(默认zuc) / ⚔️攻击模拟 / 📁文件 / ⚡启动 / ◑主题 | 无控制栏 |
| 时间线步骤 | 1.生成SM9密钥 2.生成SM2密钥 3.加密签名封装 | 1.加载解封 2.SM9验签 3.HMAC对比 4.摘要对比 5.结论 |
| 导航 | 演示 / 环境（屏蔽基准测试） | 无导航（单页时间线） |
| 日志面板 | 保留 | 保留（独立日志） |
| 弹出时机 | 程序启动时显示 | 发送端步骤3完成 + 攻击篡改执行后自动弹出 |
| 窗口位置 | 系统默认 | 系统默认 |

### 接收端验证展示规则

| 验证项 | 展示方式 | 数据来源 |
|--------|----------|----------|
| SM9 签名 | 胶囊 badge (pass/fail) | recv_result["signature_ok"] |
| HMAC 完整性 | CompareBlock：信封声称值 vs 独立计算值 | claimed: envelope.auth_tag_b64, computed: recv_result["computed_hmac"] |
| SM3 摘要 | CompareBlock：信封声称值 vs 解密后计算值 | claimed: envelope.plain_digest_hex, computed: recv_result["computed_digest"] |

**GCM 模式特殊处理**：SM4-GCM 模式下无独立 HMAC 计算（GCM 内置认证）。此时第 3 步标题改为"GCM 认证标签验证"，仅展示 GCM tag 值 + pass/fail 胶囊（不做 CompareBlock 对比），结论跟随解密是否成功。

### 数据流

```
用户点击"⚡启动演示"
  → SenderWindow 创建 WorkflowWorker(path, cipher, mode, attack)
    → Worker step 1: 生成SM9主密钥
        → emit step_data(target="sender", step=1, ...)
    → Worker step 2: 生成SM2密钥对
        → emit step_data(target="sender", step=2, ...)
    → Worker step 3: send() 加密签名封装
        → emit step_data(target="sender", step=3, ...)
    → Worker: 攻击篡改 message.json (如有)
    → Worker: emit signal "sender_done" → SenderWindow 弹出 ReceiverWindow
    → Worker step 4: receive() 解封验证解密
        → emit step_data(target="receiver", step=1, ...) 加载解封
        → emit step_data(target="receiver", step=2, ...) SM9验签 (pass/fail)
        → emit step_data(target="receiver", step=3, ...) HMAC对比 (claimed + computed)
        → emit step_data(target="receiver", step=4, ...) 摘要对比 (claimed + computed)
        → emit step_data(target="receiver", step=5, ...) 最终结论
    → Worker: emit finished(result)
```

## 新增组件

### ReceiverWindow (`gui/receiver_window.py`)

精简版独立窗口：
- 无边框 + 透明背景 + 圆角（复用现有窗口风格）
- 标题栏：logo + "📥 基于国密算法的安全数据传输与身份认证系统 — 接收端" + 主题切换按钮 + 窗口控制
- 中央区域：TimelineView（复用现有组件）
- 右侧：LogWidget（独立日志实例）
- 无左侧导航栏
- 暴露 `on_step_data(dict)` 供 SenderWindow 转发接收端步骤
- 暴露 `refresh_styles()` 供主题切换时级联刷新
- 主题切换时同步：SenderWindow 切主题后通知 ReceiverWindow 也切换

### CompareBlock (`gui/data_widgets.py` 新增)

上下对比展示组件：
- 构造参数：`title: str, claimed_label: str, claimed_value: str, computed_label: str, computed_value: str, is_match: bool`
- 布局：
  - section-label 标题（如 "HMAC-SM3 对比"）
  - 上行：claimed_label + claimed_value（截断 + tooltip 全文）
  - 下行：computed_label + computed_value
  - 底部：badge (pass/fail)
- 颜色：match 时两行用 capsule_pass 色系，mismatch 时用 capsule_fail 色系
- 支持 `refresh_theme_style()` 主题切换刷新

## 改动清单

### `core/receiver.py`

在 `receive()` 函数返回的 result dict 中新增字段：
- `claimed_hmac`: str — auth_tag 的 hex 表示（信封中声称的 HMAC 值）
- `computed_hmac`: str — 接收方独立计算的 HMAC hex（非 GCM 模式下）；GCM 模式下为空字符串
- `claimed_digest`: str — envelope.algo_meta.plain_digest_hex
- `computed_digest`: str — 解密后明文的 SM3 摘要 hex；解密失败时为空字符串

### `gui/workers.py`

- 新增 Signal: `sender_done = Signal()` — 发送步骤完成时发射，触发弹出接收端窗口
- step_data 信号的 dict 新增 `"target"` 字段: `"sender"` 或 `"receiver"`
- 接收端步骤拆分为 5 步（加载解封 / SM9验签 / HMAC对比 / 摘要对比 / 结论）
- HMAC 对比步骤携带 claimed_hmac + computed_hmac
- 摘要对比步骤携带 claimed_digest + computed_digest

### `gui/main_window.py` (SenderWindow)

- 窗口标题改为 "📤 基于国密算法的安全数据传输与身份认证系统 — 发送端"
- 控制栏 emoji 提示：🔐算法 ⚔️攻击 📁文件
- 导航栏移除"性能"按钮，不创建 BenchmarkTab
- `_on_step_data()` 过滤 target=="sender" 的步骤才渲染到本窗口 timeline
- 监听 worker.sender_done → 创建并 show ReceiverWindow
- 将 target=="receiver" 的 step_data 转发给 ReceiverWindow
- 主题切换时同步通知 ReceiverWindow

### `gui/receiver_window.py` (新文件)

- 独立 QMainWindow，精简布局（标题栏 + timeline + 日志）
- `on_step_data(dict)` — 接收接收端步骤数据，渲染到自身 timeline
- step 2 (SM9验签) 用 VerifyCapsule badge
- step 3/4 (HMAC/摘要) 用 CompareBlock
- step 5 (结论) 用 ConclusionBanner
- 主题切换跟随发送端

### `gui/data_widgets.py`

- 新增 `CompareBlock` 类
- StepCardWidget 的 `set_data_rows()` 路由逻辑需识别 CompareBlock 数据格式

### `gui/step_card.py`

- `set_data_rows()` 新增路由：当 data 中包含 `_compare` 键时，渲染为 CompareBlock

## 屏蔽基准测试

- `gui/main_window.py`: 导航栏移除 "bench" 按钮
- 不 import / 不实例化 BenchmarkTab
- 保留 `gui/tabs/benchmark_tab.py` 文件

## 主题同步机制

SenderWindow 持有 ReceiverWindow 引用。切换主题时：
1. SenderWindow._toggle_dark_mode() 执行自身主题切换
2. 如果 ReceiverWindow 存在且可见，调用 ReceiverWindow.sync_theme(is_dark)
3. ReceiverWindow.sync_theme() 内部执行 apply_color_scheme + refresh_styles + overlay 过渡动画

## 窗口生命周期

- ReceiverWindow 在每次"启动演示"时创建（如果已存在则先 close 旧的再创建新的）
- 用户可以随时关闭 ReceiverWindow（不影响发送端）
- 程序退出时 SenderWindow.closeEvent() 同时关闭 ReceiverWindow
