import base64
import hashlib
import hmac
import json
import secrets
import time

from Crypto.Cipher import AES
from Crypto.Cipher import PKCS1_v1_5
from Crypto.PublicKey import RSA
from Crypto.Util.Padding import pad


def aes_cbc_encrypt_base64(plaintext: bytes, key: bytes, iv: bytes) -> str:
    """
    AES-CBC 加密，返回 Base64 编码的密文（不包含 IV）。
    :param plaintext: 待加密数据（bytes）
    :param key: 16/24/32 字节的 AES 密钥
    :param iv: 16 字节的初始化向量
    :return: Base64 字符串
    """
    # 确保 IV 长度正确
    assert len(iv) == AES.block_size, "IV 长度必须为 16 字节"
    cipher = AES.new(key, AES.MODE_CBC, iv)
    padded = pad(plaintext, AES.block_size)
    ciphertext = cipher.encrypt(padded)
    return base64.b64encode(ciphertext).decode('ascii')


def rsa_encrypt(plaintext: bytes, public_key_pem) -> str:
    """
    :param plaintext: 待加密数据 (bytes)
    :param public_key_pem: PEM 格式公钥 (bytes)
    :return: Base64 编码的密文 (str)
    """
    key = RSA.import_key(public_key_pem)
    cipher = PKCS1_v1_5.new(key)
    cipher_bytes = cipher.encrypt(plaintext)
    cipher_b64 = base64.b64encode(cipher_bytes).decode('ascii')
    return cipher_b64


def hmac_sha256_base64(message: str, base64_key: str) -> str:
    # 解码 base64 格式的 key
    key_bytes = base64.b64decode(base64_key)
    message_bytes = message.encode('utf-8')

    # 使用 HMAC-SHA256 计算签名
    signature = hmac.new(key_bytes, message_bytes, hashlib.sha256).digest()

    # 返回 base64 编码后的结果
    return base64.b64encode(signature).decode('utf-8')


class GetFnOsData:
    def __init__(self):
        self.key = secrets.token_hex(16)
        self.iv = secrets.token_bytes(16)
        self.secret = None
        self.token = None
        self.uid = None
        self.admin = None
        self.backId = None
        self.machineId = None
        self.result = None

    @classmethod
    def get_req_id(cls):
        n = f"{int(time.time()):08x}"

        # 假设 _p.id 是一个整数，将其转换为 16 进制字符串，不足 4 位左侧补 0
        e = f"{0:04x}"
        return f'{n}000{int(time.time() * 1000)}{e}'

    def login_data(self, username, password, si, pub_key):
        req_id = self.get_req_id()
        aes_str = {
            "reqid": req_id,
            "user": username,
            "password": password,
            "deviceType": "Browser",
            "deviceName": "Windows-Google Chrome",
            "stay": False,
            "req": "user.login",
            "si": si
        }
        aes = aes_cbc_encrypt_base64(json.dumps(aes_str).encode('utf-8'), self.key.encode('utf-8'),
                                     self.iv)
        rsa = rsa_encrypt(self.key.encode('utf-8'), pub_key)
        return {
            "msg": {
                "req": "encrypted",
                "iv": base64.b64encode(self.iv).decode('ascii'),
                "rsa": rsa,
                "aes": aes
            },
            'req_id': req_id
        }

    @classmethod
    def get_rea_pub(cls):
        req_id = cls.get_req_id()
        return {
            'msg': {
                "reqid": req_id,
                "req": "util.crypto.getRSAPub"
            },
            'req_id': req_id
        }

    def sign_data(self, msg: dict):
        assert self.secret, "未获取到登录信息"
        return hmac_sha256_base64(json.dumps(msg), self.secret)

    def set_login_data(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def get_si(self):
        req_id = self.get_req_id()
        return {
            'msg': {"reqid": "682ff083682ff074000000140057", "req": "util.getSI"},
            'req_id': req_id
        }

    def auth_token(self, si):
        req_id = self.get_req_id()
        msg = {
            "reqid": req_id,
            "req": "user.authToken",
            "token": self.token,
            "si": si
        }
        return {
            'msg': f'{self.sign_data(msg)}={json.dumps(msg)}',
            'req_id': req_id
        }

    # region 文件相关
    def ls(self, path: str = None):
        req_id = self.get_req_id()
        msg = {
            "reqid": req_id,
            "req": "file.ls"
        }
        if path:
            msg['path'] = path
        return {
            'msg': f'{self.sign_data(msg)}={json.dumps(msg)}',
            'req_id': req_id
        }

    def mountmgr_list(self):
        req_id = self.get_req_id()
        msg = {
            "reqid": req_id,
            "req": "appcgi.mountmgr.list"
        }
        return {
            'msg': f'{self.sign_data(msg)}={json.dumps(msg)}',
            'req_id': req_id
        }

    # endregion
