# 国密安全数据传输系统

本项目是一个大学生课程设计，演示基于国密算法的安全数据传输流程。当前版本采用 envelope v3.0：发送端只生成一个统一报文 `message.json`，接收端只读取该报文完成解封装、验签、完整性验证和解密。

## 协议结构

`message.json` 是唯一协议载体，结构包含：

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

## 算法职责

| 算法 | 职责 |
| --- | --- |
| SM2 | 封装 16 字节会话秘密，不再描述为交互式密钥协商 |
| HKDF-SM3 | 从会话秘密派生 SM4/ZUC 密钥、IV/nonce 和 HMAC 密钥 |
| SM4 | 默认业务加密算法，支持 CBC / CTR / GCM |
| ZUC-128 | 兼容路径的流加密算法 |
| HMAC-SM3 | 为非 GCM 路径提供完整性保护 |
| SM9 | 对完整 transcript 签名 |

KDF 绑定上下文：

```text
session_id | sender_id | receiver_id | suite_id
```

签名 transcript 覆盖：

```text
header || wrapped_secret || nonce_or_iv || ciphertext || auth_tag
```

因此 `nonce/iv`、密文、封装密钥和协议头都处于同一个认证边界内。

## 发送流程

1. 生成随机 `session_secret`。
2. 生成 `session_id`、`timestamp`、`seq`。
3. 使用 SM2 封装 `session_secret`。
4. 使用 HKDF-SM3 派生业务密钥。
5. 使用 SM4 或 ZUC 加密明文。
6. 生成 GCM tag 或 HMAC-SM3 tag。
7. 使用 SM9 签名完整 transcript。
8. 写出单一报文 `artifacts/message.json`。

## 接收流程

1. 读取 `message.json`。
2. 使用 SM2 解封装 `session_secret`。
3. 使用相同上下文派生业务密钥。
4. 验证 SM9 签名和完整性标签。
5. 验证通过后解密。
6. 写出 `artifacts/recovered.txt`。

## 快速开始

```bash
pip install -r requirements.txt

python cli.py inspect-env
python cli.py demo
python cli.py demo --cipher sm4 --mode gcm
python cli.py demo --cipher zuc

python cli.py send --cipher sm4 --mode gcm --in plain.txt

python cli.py benchmark
python cli.py test
```

GUI：

```bash
python gui.py
```

## 输出文件

| 文件 | 说明 |
| --- | --- |
| `message.json` | 唯一协议报文 |
| `receiver_pri.txt` | 演示用接收方 SM2 私钥 |
| `receiver_pub.txt` | 演示用接收方 SM2 公钥 |
| `recovered.txt` | 接收端恢复出的明文 |
| `benchmark.md` | 性能测试报告 |
| `benchmark.csv` | 性能测试数据 |

旧版本中的 `ciphertext.bin`、`wrapped_key.bin`、`iv.bin`、`integrity_tag.bin`、`signature.bin`、`plain_digest.bin` 已弃用，相关内容现在都封装在 `message.json` 中。

说明：当前 Windows 环境中的 `gmssl-python` SM9 主密钥对象不能可靠跨进程序列化，相关 PEM 导出接口也可能触发原生库访问异常。因此完整验签流程使用 `demo` 或 GUI，它们在同一进程中持有 SM9 主密钥；`send` 命令用于生成 envelope 报文。

## 测试重点

测试覆盖：

- SM2 封装/解封装
- HKDF-SM3 上下文绑定
- SM3/HMAC-SM3
- SM4 CBC/CTR/GCM
- ZUC-128
- 完整 envelope 工作流
- 篡改 `ciphertext`、`nonce_or_iv`、`receiver_id` 后验证失败

如果当前 Python 环境缺少 `gmssl` 包，测试会跳过依赖国密适配层的用例。
