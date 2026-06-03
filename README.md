# Guomi Crypto Secure Transport

本项目是一个大学生课程设计，实现了一套基于国密算法的安全数据传输演示系统。系统以单一 envelope 报文为核心，模拟发送端生成安全报文、接收端验证并恢复明文的完整流程。

## 功能概览

- SM2：封装会话秘密。
- HKDF-SM3：派生加密密钥、IV/nonce 和完整性密钥。
- SM4：支持 CBC、CTR、GCM 三种加密模式。
- ZUC-128：提供流加密路径。
- HMAC-SM3：为非 GCM 模式提供完整性保护。
- SM9：对完整协议 transcript 进行数字签名与验签。
- CLI：提供环境检查、演示、发送、基准测试和测试入口。
- GUI：基于 PySide6 的图形界面，以时间线卡片逐步展示协议中间过程，并内置攻击模拟与多主题切换。

## 协议报文

发送端输出一个统一报文：

```text
artifacts/message.json
```

报文结构：

```text
Envelope {
  header: {
    version,
    suite_id,
    cipher,
    mode,
    kex_mode,
    sender_id,
    receiver_id,
    session_id,
    timestamp,
    seq,
    integrity_algo
  },
  algo_meta,
  wrapped_secret_b64,
  nonce_or_iv_b64,
  ciphertext_b64,
  auth_tag_b64,
  signature_b64
}
```

KDF 上下文绑定：

```text
session_id | sender_id | receiver_id | suite_id
```

SM9 签名 transcript：

```text
header || wrapped_secret || nonce_or_iv || ciphertext || auth_tag
```

## 项目结构

```text
core/
  protocol.py       协议常量
  sender.py         发送端流程
  receiver.py       接收端流程
  workflow.py       一键完整流程
  benchmark.py      性能测试

crypto/
  sm2_kex_or_wrap.py  SM2 会话秘密封装
  sm3_integrity.py    SM3/HMAC/transcript 工具
  sm4_adapter.py      SM4 CBC/CTR/GCM
  sm9_signature.py    SM9 签名与验签
  zuc_adapter.py      ZUC-128
  kdf_utils.py        HKDF-SM3 派生
  metadata_utils.py   envelope 读写

gui/
  run.py            GUI 入口
  main_window.py    主窗口（顶栏 + 左导航 + 时间线 + 日志台）
  timeline_view.py  步骤卡片时间线容器
  step_card.py      单步骤卡片
  data_widgets.py   卡片内数据组件（键值格、长串截断、验证胶囊）
  workers.py        后台线程（含攻击模拟篡改逻辑）
  log_widget.py     语法高亮日志台
  styles.py         QSS 主题系统
  theme_selector.py 主题切换弹窗
  effects.py        动效与自绘组件

config/
  style.json        配色主题数据

tests/
  test_crypto.py    回归测试

cli.py                命令行入口
plain.txt             示例明文
```

## 环境准备

建议使用 Python 3.10 或更高版本。可以使用系统 Python、虚拟环境或 conda 环境。

使用普通 Python 环境：

```bash
python -m pip install -r requirements.txt
```

使用 venv：

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
```

使用 conda：

```bash
conda create -n guomi-crypto python=3.12
conda activate guomi-crypto
python -m pip install -r requirements.txt
```

SM9 依赖 GmSSL 原生动态库。如果环境中缺少原生库，SM9 完整流程无法运行。可以先执行环境检查命令确认本机支持情况。

## 命令行使用

环境检查：

```bash
python cli.py inspect-env
```

完整演示：

```bash
python cli.py demo
python cli.py demo --cipher sm4 --mode gcm
python cli.py demo --cipher zuc
```

生成 envelope：

```bash
python cli.py send --cipher sm4 --mode gcm --in plain.txt
```

性能测试：

```bash
python cli.py benchmark
```

运行测试：

```bash
python -m pytest tests/ -q
```

## GUI 使用

```bash
python gui/run.py
```

GUI 采用深色控制台风格，左侧导航切换四个功能页：

- 演示：选择算法后点击「启动演示」，以时间线卡片逐步展示发送与接收的 6 个核心步骤，验证结果以并行胶囊徽章呈现。
- 收发：分步演示发送与接收过程。
- 环境：查看运行环境与各算法组件状态。
- 性能：运行基准测试。

顶栏控件：

- 算法选择器：sm4-gcm / sm4-cbc / sm4-ctr / zuc。
- 攻击模拟：在发送后、接收前真实篡改信封，触发接收端的真实校验失败。可选「正常传输 / 篡改密文 / 篡改 IV·Nonce / 伪造接收方 ID / 伪造 SM9 签名」。
- 主题按钮：切换默认 / 深空 / 深蓝 / 暖橙 / 墨绿 / 紫罗兰等多套配色及深浅模式。

右侧日志台实时输出带语法高亮和时间戳的执行日志。

### 攻击模拟说明

攻击模拟用于演示国密协议的分层安全保证。选择某种攻击后，`WorkflowWorker` 会在发送端写出 `message.json` 之后、接收端读取之前篡改对应字段，接收端跑的是真实的 SM2 / HMAC-SM3 / SM9 校验，失败由密码学产生而非伪造。典型结果：

| 攻击 | SM9 签名 | 完整性 | 摘要 |
|------|----------|--------|------|
| 正常传输 | 通过 | 通过 | 通过 |
| 篡改密文 | 失败 | 失败 | 失败 |
| 篡改 IV/Nonce | 失败 | 失败 | 失败 |
| 伪造接收方 ID | 失败 | 失败 | 失败 |
| 伪造 SM9 签名 | 失败 | 通过 | 失败 |

「伪造 SM9 签名」一行体现了完整性（数据未被篡改）与来源认证（确为发送方所签）是两个独立的安全属性。

## 输出文件

运行后主要输出在 `artifacts/`：

```text
message.json      统一协议报文
receiver_pri.txt  演示用接收方 SM2 私钥
receiver_pub.txt  演示用接收方 SM2 公钥
recovered.txt     接收端恢复出的明文
benchmark.md      性能测试报告
benchmark.csv     性能测试数据
```

## 测试覆盖

测试包括：

- SM2 封装和解封装。
- HKDF-SM3 上下文绑定。
- HMAC-SM3 完整性验证。
- SM4 CBC/CTR/GCM 加解密。
- ZUC-128 加解密。
- envelope 完整发送接收流程。
- 篡改 ciphertext、nonce_or_iv、receiver_id 后验证失败。

当前验证结果：

```text
17 passed
```

## 说明

当前 Windows 环境中的 `gmssl-python` SM9 主密钥对象不能稳定跨进程序列化，因此推荐使用 `demo` 或 GUI 完整演示流程。它们在同一进程中持有 SM9 主密钥，可以完成签名和验签。

使用「伪造 SM9 签名」攻击模拟时，GmSSL 原生库会向终端打印若干 C 层诊断信息（如 `sm9_point_is_on_curve`）。这是底层库对畸形签名的正常报错，不影响 GUI 运行，验签会正确返回失败。





