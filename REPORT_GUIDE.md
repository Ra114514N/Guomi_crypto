# 课程设计报告写作指引

题目可写为：基于 SM2 密钥封装、SM3 完整性验证与 SM9 签名的多算法安全数据传输系统设计与实现。

## 选题背景

本系统面向安全数据传输场景，综合使用 SM2、SM3、SM4、SM9 和 ZUC 等国密算法，演示从发送端到接收端的完整报文保护流程。当前实现重点不在网络传输，而在协议结构、密钥派生、加密、完整性验证和签名验签的工程组合。

## 模块说明

| 模块 | 文件 | 功能 |
| --- | --- | --- |
| 协议常量 | `core/protocol.py` | 定义 envelope v3.0 常量和算法套件 |
| 发送端 | `core/sender.py` | 生成单一 `message.json` envelope |
| 接收端 | `core/receiver.py` | 读取 envelope、验签、验完整性、解密 |
| 工作流 | `core/workflow.py` | 一键运行完整演示 |
| SM2 封装 | `crypto/sm2_kex_or_wrap.py` | 封装 16 字节会话秘密 |
| HKDF-SM3 | `crypto/kdf_utils.py` | 绑定上下文派生业务密钥 |
| SM3/HMAC | `crypto/sm3_integrity.py` | 生成 HMAC 和 transcript |
| SM4 | `crypto/sm4_adapter.py` | CBC / CTR / GCM 加密 |
| ZUC | `crypto/zuc_adapter.py` | ZUC-128 流加密 |
| SM9 | `crypto/sm9_signature.py` | 基于身份的签名和验签 |

## 协议结构

新协议采用单报文封装，不再输出多个散文件。`message.json` 包含：

```text
header,
algo_meta,
wrapped_secret_b64,
nonce_or_iv_b64,
ciphertext_b64,
auth_tag_b64,
signature_b64
```

`header` 包含：

```text
version, suite_id, cipher, mode, kex_mode,
sender_id, receiver_id, session_id, timestamp, seq, integrity_algo
```

## 安全设计要点

SM2 用于密钥封装，不写成交互式 ECDH 协商。更准确的表述是：发送端随机生成会话秘密，然后用接收方 SM2 公钥封装，接收方用 SM2 私钥解封。

HKDF-SM3 的上下文绑定为：

```text
session_id | sender_id | receiver_id | suite_id
```

完整 transcript 为：

```text
header || wrapped_secret || nonce_or_iv || ciphertext || auth_tag
```

SM9 对上述 transcript 签名。这样协议头、接收方身份、nonce/iv、密文和认证标签都处于同一个认证边界中。

## 测试说明

推荐截图命令：

```bash
conda run -n pytorch python -m pytest tests/ -v
```

当前回归测试覆盖：

- SM2 封装/解封装
- HKDF-SM3 上下文绑定
- SM3/HMAC-SM3
- SM4 CBC/CTR/GCM
- ZUC-128
- envelope 完整流程
- 篡改 ciphertext、nonce_or_iv、receiver_id 后验证失败

## 演示命令

```bash
conda run -n pytorch python cli.py inspect-env
conda run -n pytorch python cli.py demo --cipher sm4 --mode gcm
conda run -n pytorch python cli.py demo --cipher zuc
conda run -n pytorch python cli.py benchmark
conda run -n pytorch python gui.py
```

说明：当前 Windows 下的 `gmssl-python` SM9 主密钥对象不能稳定跨进程序列化，PEM 导出接口也可能触发原生库访问异常。因此报告演示完整验签流程时，应使用 `demo` 或 GUI 一键流程，它们在同一进程中持有 SM9 主密钥。

## 可写入报告的改进点

相比旧设计，新设计修正了以下协议结构问题：

- 由多文件拼装改为单一 envelope。
- `nonce/iv` 纳入认证边界。
- 去掉独立 `plain_digest.bin`。
- 引入 `session_id`、`timestamp`、`seq`、`receiver_id`。
- KDF 绑定协议上下文，降低跨上下文复用风险。
- SM9 签名绑定完整 transcript，而不是只签部分字段。
