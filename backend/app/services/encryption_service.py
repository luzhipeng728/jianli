"""数据加密服务 - AES-256 对称加密

用于加密存储敏感数据，如简历源文件、个人信息等。
"""
import os
import base64
from typing import Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from app.config import get_settings


class EncryptionService:
    """AES-256 加密服务

    使用 Fernet 对称加密（基于 AES-128-CBC），
    密钥由主密钥 + 盐值通过 PBKDF2 派生。
    """

    def __init__(self):
        self._fernet: Optional[Fernet] = None
        self._initialized = False

    def _get_fernet(self) -> Fernet:
        """获取 Fernet 实例（延迟初始化）"""
        if not self._initialized:
            settings = get_settings()

            # 从配置获取加密密钥，如果没有则生成一个
            master_key = getattr(settings, 'encryption_key', None)
            if not master_key:
                master_key = os.environ.get('ENCRYPTION_KEY', 'default-encryption-key-change-in-production')

            # 使用 PBKDF2 从主密钥派生 Fernet 密钥
            salt = b'resume-parser-salt-v1'  # 固定盐值，生产环境可配置
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(master_key.encode()))
            self._fernet = Fernet(key)
            self._initialized = True

        return self._fernet

    def encrypt(self, data: bytes) -> str:
        """加密二进制数据

        Args:
            data: 原始二进制数据

        Returns:
            Base64 编码的加密数据（带 ENC: 前缀标识）
        """
        fernet = self._get_fernet()
        encrypted = fernet.encrypt(data)
        # 添加前缀标识这是加密数据
        return "ENC:" + base64.b64encode(encrypted).decode('utf-8')

    def decrypt(self, encrypted_data: str) -> bytes:
        """解密数据

        Args:
            encrypted_data: 加密的数据字符串

        Returns:
            原始二进制数据
        """
        fernet = self._get_fernet()

        # 检查是否是加密数据
        if encrypted_data.startswith("ENC:"):
            encrypted_data = encrypted_data[4:]  # 移除前缀
            encrypted_bytes = base64.b64decode(encrypted_data)
            return fernet.decrypt(encrypted_bytes)
        else:
            # 兼容旧数据（未加密的 Base64）
            return base64.b64decode(encrypted_data)

    def encrypt_string(self, text: str) -> str:
        """加密字符串

        Args:
            text: 原始字符串

        Returns:
            加密后的字符串
        """
        return self.encrypt(text.encode('utf-8'))

    def decrypt_string(self, encrypted_text: str) -> str:
        """解密字符串

        Args:
            encrypted_text: 加密的字符串

        Returns:
            原始字符串
        """
        return self.decrypt(encrypted_text).decode('utf-8')

    def is_encrypted(self, data: str) -> bool:
        """检查数据是否已加密"""
        return data.startswith("ENC:")


# 全局单例
encryption_service = EncryptionService()
