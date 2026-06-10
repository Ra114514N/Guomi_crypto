"""协议常量。"""

from __future__ import annotations

PROTOCOL_VERSION = "3.1"
DEFAULT_SENDER_ID = "sender@sm9.local"
DEFAULT_RECEIVER_ID = "receiver@sm2.local"
DEFAULT_ARTIFACTS_DIR = "artifacts"

CIPHER_SM4 = "sm4"
CIPHER_ZUC = "zuc"

MODE_CBC = "cbc"
MODE_CTR = "ctr"
MODE_GCM = "gcm"

KEX_SM2_WRAP = "sm2_wrap"

SUITE_SM4_GCM = "sm2-wrap+hkdf-sm3+sm4-gcm+sm9"
SUITE_SM4_CBC = "sm2-wrap+hkdf-sm3+sm4-cbc+hmac-sm3+sm9"
SUITE_SM4_CTR = "sm2-wrap+hkdf-sm3+sm4-ctr+hmac-sm3+sm9"
SUITE_ZUC = "sm2-wrap+hkdf-sm3+zuc+hmac-sm3+sm9"
