# 项目全景文档

> 目标读者：接手开发者或 AI 编程助手。读完本文可在不翻源码的前提下理解项目全貌、找到任何模块、上手修改。

---

## 一、项目定位

**名称**：基于国密算法的安全数据传输与身份认证系统

**性质**：大学综合实践课程设计（四川大学）

**一句话概括**：用 SM2/SM3/SM4/ZUC/SM9 五种国密算法实现一次完整的「发送 → 接收」安全通信，并以 PySide6 GUI 逐步可视化每一个密码学中间过程。

**运行方式**：`python gui/run.py`（开发）或双击 `基于国密算法的安全数据传输与身份认证系统.exe`（打包产物）。

---

## 二、技术栈

| 层 | 技术 | 版本 |
|----|------|------|
| 语言 | Python | 3.12 |
| GUI 框架 | PySide6 (Qt for Python) | 6.11 |
| 国密纯 Python | gmssl | 3.2.2 |
| 国密原生绑定 | gmssl-python (SM9) | 2.2.2 |
| 原生库 | GmSSL DLL (Release) | 3.1.1 |
| 随机数 | pycryptodome | 3.20 |
| 打包 | PyInstaller | 6.14 |

---

## 三、目录结构

```
d:\11_crypto\scu\
├── gui/                    ← 前端（全部改动集中在这里）
│   ├── run.py              GUI 入口（QApplication 创建 + MainWindow）
│   ├── main_window.py      发送端主窗口：顶栏 + 三栏布局 + 事件调度 + 弹出接收端 + 主题过渡动画 + 无边框缩放
│   ├── receiver_window.py  接收端独立窗口：标题栏 + 时间线 + 日志（发送完成后自动弹出）
│   ├── timeline_view.py    中央时间线容器（QScrollArea 管理卡片流）
│   ├── step_card.py        单步骤卡片（状态机 + 入场动画 + 内容驱动渲染路由）
│   ├── data_widgets.py     卡片内子组件（MetaCell / LongDataRow / VerifyCapsuleRow / ConclusionBanner / CompareBlock）
│   ├── workers.py          QThread 后台工作线程（target 区分收发端 + 攻击模拟篡改逻辑）
│   ├── log_widget.py       右侧日志台（自动分类 + 语法高亮）
│   ├── styles.py           QSS 主题系统（全局色彩 + 排版 token + 样式字符串生成）
│   ├── effects.py          动效组件（BusyDot / StatusIndicator）
│   ├── result_view.py      辅助富文本面板（env 页使用）
│   ├── theme_selector.py   已简化为深浅 toggle（保留文件但不再弹窗）
│   ├── elided_label.py     省略号标题标签（截断 + 完整 tooltip）
│   ├── frameless_resize.py 无边框缩放支持（edge_flags_at / cursor_shape_for_edges / ResizeCursorFilter）
│   └── tabs/               功能页
│       ├── env_tab.py      环境检测页
│       ├── demo_tab.py     演示页（已整合进 main_window 时间线）
│       ├── send_recv_tab.py 收发页（已从导航屏蔽，文件保留）
│       └── benchmark_tab.py 性能测试页（已从导航屏蔽，文件保留）
│
├── core/                   ← 业务逻辑（仅按需扩展返回字段，不改算法逻辑）
│   ├── protocol.py         协议常量（版本 3.1，套件 ID）
│   ├── sender.py           发送端流程（按原始字节读明文，header 携带 filename）
│   ├── receiver.py         接收端验证（返回 claimed/computed HMAC & 摘要、文件类型对比、恢复路径）
│   ├── workflow.py          一键完整流程（sender + receiver）
│   └── benchmark.py        性能基准测试
│
├── crypto/                 ← 算法适配层（不要动）
│   ├── gmssl_loader.py     动态加载 gmssl-python（支持 frozen 路径）
│   ├── sm2_kex_or_wrap.py  SM2 会话密钥封装/解封
│   ├── sm3_integrity.py    SM3 摘要 + HMAC-SM3 + transcript 构建
│   ├── sm4_adapter.py      SM4 CBC/CTR/GCM 加解密
│   ├── sm9_signature.py    SM9 签名/验签
│   ├── zuc_adapter.py      ZUC-128 流加密
│   ├── kdf_utils.py        HKDF-SM3 密钥派生
│   ├── key_utils.py        密钥读写工具
│   ├── metadata_utils.py   envelope JSON 构建/读写/解码
│   ├── filetype_sniffer.py magic bytes 文件类型嗅探 + 扩展名一致性检查
│   └── file_utils.py       文件操作辅助
│
├── tools/
│   └── capture_demo.py     自动截图采集（深浅主题 + 攻击场景 + 接收端滚动到底）
│
├── config/
│   └── style.json          唯一的配色数据文件（含 light + dark）
│
├── tests/
│   ├── test_crypto.py      回归测试（含二进制无损往返、篡改文件名）
│   ├── test_filetype_sniffer.py 嗅探器单测
│   └── test_build_spec.py  打包配置守护测试（新增 GUI 模块 + shiboken6 收录检查）
│
├── artifacts/              运行产物（message.json / recovered.txt 等）
├── cli.py                  CLI 入口（argparse）
├── plain.txt               示例明文
├── logo.png / logo.ico     应用图标
├── gmssl_release.dll       Release 编译的 GmSSL 原生库
├── build.spec              PyInstaller 打包配置
├── demo_fail.py            攻击场景演示脚本
└── test_verify_states.py   验证失败组合测试看板
```

---

## 四、协议流程（核心叙事）

系统模拟一次完整安全通信，分 6 步：

```
发送端                                    接收端
─────────                                ─────────
1. 生成 16B 会话秘密 + session_id
2. SM2 公钥封装会话秘密 → wrapped_secret
3. HKDF-SM3 派生 5 把子密钥（上下文绑定）
4. SM4/ZUC 加密明文 → ciphertext
5. HMAC-SM3 完整性标签（或 GCM tag）
6. SM9 签名 transcript
   ──── 写 message.json ────→
                                         1. 加载信封
                                         2. SM2 私钥解封 → 恢复会话秘密
                                         3. HKDF-SM3 重新派生子密钥
                                         4. SM9 验签 → 来源可信？
                                         5. HMAC 验证 → 未被篡改？
                                         6. 解密 + SM3 摘要比对 → 解密正确？
```

最终三项全过 → `success = True`。GUI 接收端窗口用 SM9 签名胶囊 + HMAC/摘要上下对比块呈现这三项验证。

### 信封报文（`artifacts/message.json`）

```json
{
  "header": { "version", "suite_id", "cipher", "mode", "kex_mode",
              "sender_id", "receiver_id", "filename", "session_id", "timestamp", "seq" },
  "algo_meta": { "algo", "ciphertext_len", "plain_digest_hex", "has_gcm_tag" },
  "wrapped_secret_b64": "...",
  "nonce_or_iv_b64": "...",
  "ciphertext_b64": "...",
  "auth_tag_b64": "...",
  "signature_b64": "..."
}
```

---

## 五、GUI 架构（双窗口）

系统采用**发送端 + 接收端两个独立窗口**（同进程视觉分离）。发送端为主控窗口，发送完成后自动弹出接收端窗口。

### 发送端窗口布局（main_window.py）

```
┌──────────────────────────────────────────────────────────────┐
│ [logo] 📤 基于国密算法的安全数据传输与身份认证系统—发送端  🔐[算法▼] ⚔️[攻击▼] 📁[文件] [⚡启动] ◑ — □ ×  │ ← 顶栏 44px
├────────┬─────────────────────────────────────┬───────────────┤
│  ◈演示 │  TimelineView                       │ >_ 日志       │
│  ◈环境 │  ┌────────────────────────────────┐ │ [HH:MM:SS] …  │
│        │  │ ✓ 1. 生成SM9主密钥对           │ │               │
│        │  │ ✓ 2. 生成SM2接收方密钥对       │ │               │
│        │  │ ✓ 3. 加密·签名·封装           │ │               │
│  >_    │  └────────────────────────────────┘ │               │
└────────┴─────────────────────────────────────┴───────────────┘
  72px宽（仅演示/环境，无「收发」「性能」导航）  flex      280px固定
```

### 接收端窗口布局（receiver_window.py）

```
┌──────────────────────────────────────────────────┐
│ [logo] 📥 基于国密算法的安全数据传输与身份认证系统—接收端          ◑ — □ ×    │ ← 标题栏 44px（无控制栏/无导航）
├─────────────────────────────────────┬────────────┤
│  TimelineView                       │ >_ 日志    │
│  1. 加载信封·SM2解封                │            │
│  2. SM9签名验证（pass/fail 胶囊）   │  300px固定 │
│  3. HMAC完整性（CompareBlock 对比） │            │
│  4. SM3摘要比对（CompareBlock 对比）│            │
│  5. 文件类型识别（CompareBlock 对比）│           │
│  6. 最终结论（ConclusionBanner）    │            │
└─────────────────────────────────────┴────────────┘
```

### 数据流

```
用户点击「⚡启动演示」
  → MainWindow._on_execute()
    → WorkflowWorker(path, cipher, mode, attack) 创建并 start()
      ┌── worker 线程 ──────────────────────────────────────────┐
      │ step_data 信号 dict 带 "target" 字段（"sender"/"receiver"）│
      │ 发送端步骤 1-3 → target="sender"                        │
      │ 发送+篡改完成 → emit sender_done()                      │
      │ 接收端步骤 1-6 → target="receiver"                      │
      └─────────────────────────────────────────────────────────┘
    → MainWindow._on_sender_done(): 创建并 show ReceiverWindow
    → MainWindow._on_step_data(dict):
      → target=="sender": 渲染到本窗口 timeline
      → target=="receiver": 转发给 self._receiver_win.on_step_data()
        → StepCardWidget 内容驱动路由（见 step_card.py set_data_rows）：
           含 "_compare" 键: CompareBlock（信封声称值 vs 独立计算值上下对比）
           单键且值以 ✓/✗ 开头: 单胶囊 VerifyCapsuleRow
           含 "结论" 键: ConclusionBanner
           其他: MetaCell（短数据横排）+ LongDataRow（长数据按宽度自适应省略+复制）
```

接收端验证对比的数据来自 `core/receiver.py` 返回的 `claimed_hmac` / `computed_hmac` / `claimed_digest` / `computed_digest` / `claimed_type` / `detected_type` / `type_match` 字段（另有 `filename` / `recovered_path` / `decrypt_ok`）。SM9 签名验证无可对比的中间值，只展示 pass/fail 胶囊。

### 主题系统

- 唯一配色文件：`config/style.json`（一个「默认」主题，含 light/dark 两套；含色值 + 排版 token + 浅色胶囊专用 token）
- `styles.py` 在启动时和切换时调用 `apply_color_scheme("默认", is_dark)`，把 JSON 值灌入全局变量，再用 `update_styles()` 拼出 QSS 字符串
- 所有组件通过引用 `styles.xxx` 变量获取颜色，`refresh_styles()` 级联刷新
- 切换主题用**截图淡出过渡动画**：grab 整窗 → overlay 覆盖 → 静默换装 → 450ms 淡出（`_toggle_dark_mode` / `ThemeTransitionOverlay`）
- 发送端切主题时通过 `sync_theme(is_dark)` 同步通知接收端窗口

切换方式：发送端顶栏 `◑` 按钮，点一下 toggle `_is_dark`。

---

## 六、攻击模拟

顶栏「攻击模拟」下拉栏，在 `WorkflowWorker` 发送后、接收前真实篡改 `message.json`：

| 选项 | 篡改方式 | 预期效果 |
|------|----------|----------|
| 正常传输 | 不篡改 | 三项全过 |
| 篡改密文 | flip ciphertext 中间字节 | 签名✗ 完整性✗ 摘要✗ |
| 篡改 IV/Nonce | flip nonce 中间字节 | 签名✗ 完整性✗ 摘要✗ |
| 伪造接收方 ID | 改 header.receiver_id | 签名✗ 完整性✗ 摘要✗ |
| 篡改文件名 | 改 header.filename | 签名✗ 完整性✗ 摘要✗（header 受签名+HMAC 双保护） |
| 伪造 SM9 签名 | flip signature 中间字节 | 签名✗ 完整性✓ 摘要✓（仅签名本身被伪造） |

实现在 `workers.py` 的 `_tamper_envelope()` 方法。

---

## 七、打包

```powershell
pyinstaller build.spec --noconfirm
```

产物：`dist/GuomiCrypto/基于国密算法的安全数据传输与身份认证系统.exe`（约 117MB 单目录分发）

**关键路径适配**（frozen 模式）：
- `sys._MEIPASS` → 只读资源（gmssl.py/dll、config/、plain.txt、logo）
- `sys.executable` 同级 → 可写输出（artifacts/）

**gmssl.dll 必须是 Release 编译**（链接 vcruntime140.dll，Win11 自带）。项目根目录的 `gmssl_release.dll` 即为此产物。

**shiboken6 运行库**：PySide6 扩展模块导入 QtWidgets 时需要 `shiboken6.abi3.dll`，`build.spec` 已将其额外复制到 `PySide6/` 目录（兼容性副本）。`tests/test_build_spec.py` 守护该配置及新增 GUI 模块（receiver_window / elided_label / frameless_resize）的 hiddenimports 收录。

打包产物归档在 `release/`（已 gitignore，不入库）。

---

## 八、常见修改场景速查

### 改配色
编辑 `config/style.json`，light/dark 对应字段即可。无需改代码。

### 改卡片内数据的渲染逻辑
- 短数据（横排）：`gui/data_widgets.py` → `MetaCell`
- 长数据（截断+复制）：`gui/data_widgets.py` → `LongDataRow`
- 验证胶囊（pass/fail）：`gui/data_widgets.py` → `VerifyCapsuleRow`
- 结论横幅：`gui/data_widgets.py` → `ConclusionBanner`
- 上下对比块（信封声称值 vs 独立计算值）：`gui/data_widgets.py` → `CompareBlock`
- 路由规则：`gui/step_card.py` → `set_data_rows()` 方法（**内容驱动**，非步骤号驱动）：
  - data 含 `"_compare": True` → CompareBlock
  - 单键且值以 ✓/✗ 开头 → 单胶囊
  - data 含 `"结论"` 键 → ConclusionBanner
  - 其他 → MetaCell / LongDataRow

### 改每一步展示的数据字段
`gui/workers.py` → `WorkflowWorker.run()` 里每个 `self.step_data.emit(...)` 的 `data` 字典（注意带 `"target"` 字段区分收发端）。

### 改接收端对比展示的数据来源
`core/receiver.py` → `receive()` 返回的 `claimed_hmac` / `computed_hmac` / `claimed_digest` / `computed_digest` / `claimed_type` / `detected_type` / `type_match` 字段。

### 加新的攻击模拟
1. `gui/main_window.py` 的 `self.attack_combo.addItem(...)` 加选项
2. `gui/workers.py` 的 `_tamper_envelope()` 加 elif 分支

### 改布局
- 发送端：`gui/main_window.py` 的 `_build_top_bar` / `_build_nav` / `_build_center` / `_build_log_panel`
- 接收端：`gui/receiver_window.py` 的 `_build_title_bar` / `_build_body`

### 恢复「性能」导航入口
`gui/main_window.py`：在 `nav_items` 加回 `("bench", "◈\n性能")`，在 `_build_center` 重新实例化 `BenchmarkTab` 并 addWidget，在 `_on_nav` 加回 bench 分支。

### 改动画
- 卡片入场：`gui/step_card.py` → `_run_entrance()`（400ms OutCubic 淡入）
- 胶囊多米诺：`gui/data_widgets.py` → `VerifyCapsuleRow.__init__` 的 QTimer 延迟
- BusyDot 脉动：`gui/effects.py` → `BusyDot`

### 改窗口控制按钮
`gui/styles.py` → `win_control_style` 变量 + `gui/main_window.py` → `_win_control_button()`

### 验证 GUI 改动效果（截图采集）
```powershell
python tools/capture_demo.py 前缀 [攻击键]   # 攻击键: none/ciphertext/nonce/receiver_id/filename/signature
```
自动跑完整演示并输出深浅主题各一组截图（发送端 + 接收端 + 接收端滚动到底含最终结论）。`docs_screenshot*.png` 前缀已被 gitignore。

### 重新编译 GmSSL Release DLL
```powershell
git clone https://github.com/guanzhi/GmSSL.git --branch v3.1.1 --depth 1
cd GmSSL && mkdir build && cd build
cmake .. -G "Visual Studio 17 2022" -A x64
cmake --build . --config Release
# 产物: build/bin/Release/gmssl.dll
```

---

## 九、依赖关系图

```
gui/run.py
  └── gui/main_window.py（发送端主窗口）
        ├── gui/styles.py ←── config/style.json
        ├── gui/timeline_view.py
        │     └── gui/step_card.py
        │           └── gui/data_widgets.py
        ├── gui/log_widget.py
        ├── gui/workers.py
        │     ├── core/sender.py ──┐
        │     ├── core/receiver.py ├── crypto/*
        │     └── core/workflow.py ┘
        ├── gui/effects.py
        ├── gui/receiver_window.py（接收端独立窗口，由发送端弹出）
        │     ├── gui/timeline_view.py
        │     ├── gui/log_widget.py
        │     └── gui/data_widgets.py（CompareBlock 等）
        └── gui/tabs/*.py
              └── gui/result_view.py
```

`core/` 和 `crypto/` 是纯逻辑层，不依赖任何 GUI 模块。`gui/` 只通过 `WorkflowWorker` 的信号与业务层交互。发送端与接收端窗口同进程，通过 `WorkflowWorker` 信号的 `target` 字段路由各自步骤。

---

## 十、注意事项

1. **gmssl 双包冲突**：`gmssl==3.2.2`（纯 Python SM2/SM3/SM4）和 `gmssl-python==2.2.2`（原生 SM9 绑定）都注册为 `gmssl` 命名空间。`crypto/gmssl_loader.py` 用 `importlib.util.spec_from_file_location` 按绝对路径加载后者，避免冲突。
2. **SM9 同进程限制**：SM9 主密钥对象不能跨进程序列化（Windows 上），所以发送和接收必须在同一次 `WorkflowWorker` 运行中完成。
3. **无边框窗口**：`Qt.FramelessWindowHint` + `WA_TranslucentBackground`。两个窗口均支持：标题栏拖动（`mousePressEvent`/`mouseMoveEvent` 判断 y < 44px）+ 边缘拖拽缩放（`_EDGE = 12` px 检测区，`_edge_at()` / `_do_resize()`）。悬停缩放光标由 `gui/frameless_resize.py` 的 `ResizeCursorFilter` 保证——递归安装到所有子组件并监听 `ChildAdded`，临时覆盖被子组件遮挡处的光标，离开边缘时恢复原光标。
4. **QScrollArea + QGraphicsOpacityEffect 冲突**：卡片入场淡入用 opacity effect，动画结束后立即 `setGraphicsEffect(None)` 移除，否则滚动时会渲染残影。验证胶囊已完全去掉 opacity effect，改用纯状态切换实现多米诺。
5. **主题切换截图过渡的闪烁修复**：overlay 必须挂在 QMainWindow（`self`）而非 central widget——挂 central 会触发其 drop shadow effect 缓存失效导致窗口边界抖动。换装前需 `overlay.repaint()` 强制同步绘制旧截图，否则底层会先于 overlay 露出新样式。
