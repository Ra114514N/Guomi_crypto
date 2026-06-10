# 实施规划：二进制无损恢复 · 文件类型识别 · 卡片信息密度

> 日期：2026-06-10
> 实施顺序：任务 A（修 BUG）→ 任务 B（文件类型）→ 任务 C（字号密度，截图-观察-返修闭环）
> A 与 B 改动面重叠（header.filename 同时是 A 的扩展名来源），由同一后端子代理一次完成。

---

## 任务 A：二进制无损恢复（正确性 BUG，最高优先级）

### 根因

- 发送端无损：`core/sender.py:67` 用 `read_bytes()` 读原始字节加密。
- 接收端损坏：`core/receiver.py:90`
  `write_text(out / "recovered.txt", plaintext.decode("utf-8", errors="replace"))`
  任何非 UTF-8 文件（图片/PDF/zip/GBK 文本）每个非法字节被替换为 U+FFFD，永久损坏。
- 隐蔽性：SM3 摘要比对发生在写盘之前、针对解密字节，GUI 三项全绿但产物已坏。

### 修复

1. `core/receiver.py`：`write_text(...)` → `write_bytes(out / recovered_name, plaintext)`。
   `recovered_name = "recovered" + Path(header["filename"]).suffix`；header 无 filename 时回退 `recovered.bin`。
2. 解密异常语义修正：`receiver.py:91-92` 当前把 `integrity_ok` 置 False（HMAC 明明已通过）。
   改为：新增 `decrypt_ok` 字段；解密失败只导致 `digest_ok=False`、`decrypt_ok=False`，不回写 `integrity_ok`。
3. 返回 dict 新增：`filename`、`recovered_path`、`decrypt_ok`。

### 验证

- 新测试：含 `0xFF`、`0x00` 等非 UTF-8 字节的二进制明文走完整 send→receive，
  断言恢复文件字节与原文**逐字节相等**（parametrize: sm4-cbc / sm4-gcm / zuc）。
- 现有 `plain.txt` 流程恢复名仍为 `recovered.txt`（扩展名继承），不破坏现有断言。

---

## 任务 B：文件类型识别（双轨：协议声称 + 内容嗅探）

### 协议层（声称值）

1. `crypto/metadata_utils.py` `build_header()` 新增参数 `filename: str = ""`，写入 header。
2. `core/sender.py` 传 `filename=Path(plaintext_path).name`（仅文件名，不含路径）。
3. `core/protocol.py` `PROTOCOL_VERSION` "3.0" → "3.1"。
4. header_bytes 同时进入 SM9 transcript 与 HMAC integrity object → filename 自动获得签名+完整性双保护。

### 内容嗅探（独立计算值）

新模块 `crypto/filetype_sniffer.py`（纯标准库，无新依赖）：

- `sniff_type(data: bytes) -> str`：magic bytes 识别，返回中文标签。
  覆盖：PNG / JPEG / GIF / BMP / WEBP / PDF / ZIP(含 docx·xlsx·jar) / 7z / RAR / GZIP /
  PE 可执行 / ELF / MP3 / MP4 / WAV·RIFF / SQLite / JSON·UTF-8 文本启发式 / 空文件 /
  兜底「二进制数据（未知格式）」。
- `check_consistency(filename: str, data: bytes) -> tuple[str, str, bool]`：
  返回（声称描述, 检测标签, 是否一致）。扩展名未知 → 一致性视为 True（无法证伪），
  声称描述显示「未知类型 (.xyz)」。

### 接收端集成

- `core/receiver.py` 解密成功后调用嗅探，返回 dict 新增：
  `claimed_type`、`detected_type`、`type_match`。
- 解密失败时 `detected_type = ""`，`type_match = False`。

### GUI（接收端时间线 5 步 → 6 步）

- `gui/workers.py`：插入接收端步骤 5「文件类型识别」，用现有 `_compare` 路由渲染 CompareBlock：
  「信封声称类型 vs 内容检测类型」；原「最终结论」顺延为步骤 6，输出路径用真实恢复文件名。
  进度文案 `接收端 X/5` → `接收端 X/6`。`type_match` 仅作展示，不改变 `success` 判定。
- 新攻击项「篡改文件名」：
  - `gui/main_window.py` `attack_combo.addItem("篡改文件名", "filename")`
  - `gui/workers.py` `_tamper_envelope()` 加分支：`header["filename"] = "evil.exe"`
  - 预期效果：签名✗ 完整性✗ 摘要✗（header 受双保护）。
- 发送端步骤 3 卡片数据补「文件名」字段。

### 验证

- 嗅探器单测：PNG/PDF/ZIP/UTF-8 文本/未知二进制/空。
- 篡改 filename 后 `success == False` 的回归测试。
- README 攻击模拟表格加一行。

---

## 任务 C：卡片字号与信息密度（截图-观察-返修模式）

### 验收标准

- 所有展示内容尽可能占满卡片，显著减少留白。
- 最终整窗截图缩放到 A4 纸打印后文字仍清晰可读。
- 深浅两套主题同步调整，互不破坏。

### 第一轮静态调整（子代理执行）

| 项 | 现值 | 目标 |
|---|---|---|
| font_size_title / body / mono / label / log | 16/14/13/12/12 | 18/16/15/13/13 |
| card_padding / card_spacing | 24/14 | 16/10 |
| step_card 数据区缩进/行距 (`step_card.py:91`) | 34px / 10px | 24px / 8px |
| CompareBlock 标题/值/徽章硬编码 11–12px | 硬编码 | 改引 token |
| LongDataRow 复制按钮 11px、窗口日志标题 11px | 硬编码 | 改引 token |
| VerifyCapsule / VerifyCapsuleRow 固定高 56/60 | 固定 | 随字号放大（约 64/68） |
| LongDataRow max_chars 56 / CompareBlock max_chars 40 | — | 48 / 36（字大后单行容纳变少） |

约束：`config/style.json` 的 light 与 dark 两套 token 同步改；
所有改动必须经过 `styles.py` token 体系，组件内不得新增硬编码 px。

### 第二轮起：截图-观察-返修闭环（主会话执行）

1. 编写 `tools/capture_demo.py`：启动 QApplication → MainWindow → 自动触发演示 →
   等接收端窗口出齐 → `grab()` 两窗口存 PNG → 退出。
2. 观察截图：字号是否够大、留白是否仍多、长串截断是否过短、胶囊/对比块是否被裁切。
3. 微调 token → 重新截图，循环至满足 A4 验收标准。
4. 深浅两套各截一轮确认。

---

## 提交切分

1. `fix: binary-safe plaintext recovery with original file extension`（任务 A + header.filename 协议变更 + 测试）
2. `feat: file type identification as sixth receiver step + filename tamper attack`（任务 B GUI 部分）
3. `style: enlarge card typography and tighten whitespace`（任务 C 全部轮次完成后一次提交）
4. `docs: sync README/CLAUDE.md`（协议 3.1、6 步时间线、新攻击项、字号 token 表）

## 风险点

- header 新增字段对旧 envelope 不向后兼容——本项目收发永远同进程同版本，可接受；receiver 用 `header.get("filename", "")` 容错。
- 字号放大后 1220×780 默认窗口可能容不下 6 步时间线 → 接收端窗口默认高度已是 960，必要时微调默认尺寸而非缩字号。
- `VerifyCapsule` 固定高度若不随字号放大会裁切文字——已列入第一轮清单。
