"""SM2 非对称加密适配器。

封装 gmssl 库的 SM2 操作，提供统一接口：
- 密钥对生成
- 公钥加密 / 私钥解密
- 私钥签名 / 公钥验签

注意：gmssl 3.2.2 不提供标准 SM2 密钥协商（ECDH-SM2）接口，
因此本模块采用"SM2 公钥加密传输会话密钥"方案替代密钥协商。
"""

from __future__ import annotations

import binascii
from base64 import b64decode, b64encode
from random import SystemRandom
from typing import Tuple

from gmssl import sm2 as _SM2
from gmssl.func import random_hex


# ── 内部椭圆曲线辅助（复用原项目逻辑）──────────────────────────────────────

class _CurveFp:
    def __init__(self, A, B, P, N, Gx, Gy, name):
        self.A, self.B, self.P, self.N = A, B, P, N
        self.Gx, self.Gy, self.name = Gx, Gy, name


class _SM2Key:
    sm2p256v1 = _CurveFp(
        name="sm2p256v1",
        A=0xFFFFFFFEFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF00000000FFFFFFFFFFFFFFFC,
        B=0x28E9FA9E9D9F5E344D5A9E4BCF6509A7F39789F515AB8F92DDBCBD414D940E93,
        P=0xFFFFFFFEFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF00000000FFFFFFFFFFFFFFFF,
        N=0xFFFFFFFEFFFFFFFFFFFFFFFFFFFFFFFF7203DF6B21C6052B53BBF40939D54123,
        Gx=0x32C4AE2C1F1981195F9904466A39C9948FE30BBFF2660BE1715A4589334C74C7,
        Gy=0xBC3736A2F4F6779C59BDCEE36B692153D0A9877CC62A474002DF32E52139F0A0,
    )

    @staticmethod
    def _inv(a: int, n: int) -> int:
        if a == 0:
            return 0
        lm, hm = 1, 0
        low, high = a % n, n
        while low > 1:
            r = high // low
            nm, new = hm - lm * r, high - low * r
            lm, low, hm, high = nm, new, lm, low
        return lm % n

    @staticmethod
    def _to_jac(p):
        return p[0], p[1], 1

    @staticmethod
    def _from_jac(p, P):
        z = _SM2Key._inv(p[2], P)
        return (p[0] * z ** 2) % P, (p[1] * z ** 3) % P

    @staticmethod
    def _jac_double(p, A, P):
        x, y, z = p
        if not y:
            return 0, 0, 0
        ysq = (y ** 2) % P
        S = (4 * x * ysq) % P
        M = (3 * x ** 2 + A * z ** 4) % P
        nx = (M ** 2 - 2 * S) % P
        ny = (M * (S - nx) - 8 * ysq ** 2) % P
        nz = (2 * y * z) % P
        return nx, ny, nz

    @staticmethod
    def _jac_add(p, q, A, P):
        if not p[1]:
            return q
        if not q[1]:
            return p
        U1 = (p[0] * q[2] ** 2) % P
        U2 = (q[0] * p[2] ** 2) % P
        S1 = (p[1] * q[2] ** 3) % P
        S2 = (q[1] * p[2] ** 3) % P
        if U1 == U2:
            if S1 != S2:
                return 0, 0, 1
            return _SM2Key._jac_double(p, A, P)
        H = U2 - U1
        R = S2 - S1
        H2 = (H * H) % P
        H3 = (H * H2) % P
        U1H2 = (U1 * H2) % P
        nx = (R ** 2 - H3 - 2 * U1H2) % P
        ny = (R * (U1H2 - nx) - S1 * H3) % P
        nz = (H * p[2] * q[2]) % P
        return nx, ny, nz

    @staticmethod
    def _jac_mul(p, n, N, A, P):
        if p[1] == 0 or n == 0:
            return 0, 0, 1
        if n == 1:
            return p
        if n < 0 or n >= N:
            return _SM2Key._jac_mul(p, n % N, N, A, P)
        half = _SM2Key._jac_mul(p, n // 2, N, A, P)
        if n % 2 == 0:
            return _SM2Key._jac_double(half, A, P)
        return _SM2Key._jac_add(_SM2Key._jac_double(half, A, P), p, A, P)

    @staticmethod
    def multiply(point, n, N, A, P):
        return _SM2Key._from_jac(_SM2Key._jac_mul(_SM2Key._to_jac(point), n, N, A, P), P)


def generate_keypair() -> Tuple[str, str]:
    """生成 SM2 密钥对，返回 (私钥hex64, 公钥hex130-含04前缀)。"""
    curve = _SM2Key.sm2p256v1
    secret = SystemRandom().randrange(1, curve.N)
    x, y = _SM2Key.multiply((curve.Gx, curve.Gy), secret, N=curve.N, A=curve.A, P=curve.P)
    pri = hex(secret)[2:].zfill(64)
    pub = "04" + hex(x)[2:].zfill(64) + hex(y)[2:].zfill(64)
    return pri, pub


class SM2Adapter:
    """SM2 操作封装。

    pub_key: 不含 '04' 前缀的 128 位十六进制公钥字符串
    pri_key: 64 位十六进制私钥字符串
    """

    def __init__(self, pub_key: str | None = None, pri_key: str | None = None):
        # gmssl 要求公钥不含 04 前缀，用切片而非 lstrip 避免误删首位
        self._pub = pub_key[2:] if pub_key and pub_key.startswith("04") else pub_key
        self._pri = pri_key
        self._sm2 = _SM2.CryptSM2(public_key=self._pub, private_key=self._pri)

    # ── 加密 / 解密 ──────────────────────────────────────────────────────────

    def encrypt(self, plaintext: bytes) -> bytes:
        """用公钥加密，返回 base64 编码的密文字节。"""
        raw = self._sm2.encrypt(plaintext)
        return b64encode(raw)

    def decrypt(self, ciphertext: bytes) -> bytes:
        """用私钥解密 base64 编码的密文，返回明文字节。"""
        raw = b64decode(ciphertext)
        return self._sm2.decrypt(raw)

    # ── 签名 / 验签 ──────────────────────────────────────────────────────────

    def sign(self, message: bytes) -> str:
        """用私钥对消息签名（内部使用 sign_with_sm3），返回十六进制签名字符串。"""
        k_hex = random_hex(self._sm2.para_len)
        sm2c = _SM2.CryptSM2(public_key=self._pub, private_key=self._pri)
        return sm2c.sign_with_sm3(message, k_hex)

    def verify(self, message: bytes, signature: str) -> bool:
        """用公钥验签，返回 True/False。"""
        sm2c = _SM2.CryptSM2(public_key=self._pub, private_key=self._pri)
        return sm2c.verify_with_sm3(signature, message)
