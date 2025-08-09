"""
BaseUser クラス

DynamoDB 認証システムの基本的なユーザーモデルです。
"""

import datetime
import uuid
import hashlib
import re
from typing import Optional, Any, Dict, Union

try:
    import bcrypt

    BCRYPT_AVAILABLE = True
except ImportError:
    BCRYPT_AVAILABLE = False


class Meta:
    """BaseUser のデフォルトメタ設定"""

    table_name = "users"
    expiration = 3600
    id_type = "uuid"
    is_email_login = False
    is_role_permission = False
    password_min_length = 8
    password_require_uppercase = False
    password_require_lowercase = False
    password_require_digit = True
    password_require_special = False
    enable_auth_logging = False
    auto_timestamps = True
    endpoint_url: Optional[str] = None


class BaseUser:
    """基本的なユーザーモデルクラス"""

    Meta = Meta

    def __init__(self, id: Union[str, None] = None, password: Optional[str] = None):
        """
        基本的なユーザーモデルのコンストラクタ

        Args:
            id: ユーザー ID（None の場合は自動生成）
            password: パスワード
        """
        if id is None:
            if self.Meta.id_type == "uuid":
                self.id = str(uuid.uuid4())
            else:
                raise ValueError("id と password は必須です")
        else:
            self.id = id

        self.password: Optional[str]
        if password is not None:
            self._validate_password(password)
            self.password = self._hash_password(password)
        else:
            self.password = None

        if self.Meta.auto_timestamps:
            now = datetime.datetime.now()
            self.created_at = now
            self.updated_at = now

    def _validate_password(self, password: str) -> None:
        """パスワードのバリデーション"""
        if len(password) < self.Meta.password_min_length:
            raise ValueError(
                f"パスワードは{self.Meta.password_min_length}文字以上である必要があります"
            )

        if self.Meta.password_require_uppercase and not re.search(r"[A-Z]", password):
            raise ValueError("パスワードには大文字を含める必要があります")

        if self.Meta.password_require_lowercase and not re.search(r"[a-z]", password):
            raise ValueError("パスワードには小文字を含める必要があります")

        if self.Meta.password_require_digit and not re.search(r"\d", password):
            raise ValueError("パスワードには数字を含める必要があります")

        if self.Meta.password_require_special and not re.search(
            r'[!@#$%^&*(),.?":{}|<>]', password
        ):
            raise ValueError("パスワードには特殊文字を含める必要があります")

    def _hash_password(self, password: str) -> str:
        """パスワードをハッシュ化"""
        if not BCRYPT_AVAILABLE:
            # bcrypt が利用できない場合は simple なハッシュ（テスト用）
            return hashlib.sha256(password.encode("utf-8")).hexdigest()
        hashed_bytes = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
        return str(hashed_bytes.decode("utf-8"))

    def verify_password(self, password: str) -> bool:
        """パスワードを検証"""
        if not self.password:
            return False

        if not BCRYPT_AVAILABLE:
            # bcrypt が利用できない場合は simple ハッシュで検証
            return self.password == hashlib.sha256(password.encode("utf-8")).hexdigest()

        result = bcrypt.checkpw(password.encode("utf-8"), self.password.encode("utf-8"))
        return bool(result)

    def _validate_email(self, email: str) -> None:
        """メールアドレスのバリデーション"""
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_pattern, email):
            raise ValueError("有効なメールアドレスを入力してください")

    def to_dict(self, include_password: bool = False) -> Dict[str, Any]:
        """オブジェクトを辞書形式に変換"""
        result = {}
        for key, value in self.__dict__.items():
            if key == "password" and not include_password:
                continue
            if isinstance(value, datetime.datetime):
                result[key] = value.isoformat()
            else:
                result[key] = value
        return result

    def to_token_payload(self) -> Dict[str, Any]:
        """JWT トークンのペイロード用辞書を生成（パスワード除外）"""
        payload = self.to_dict(include_password=False)
        now = datetime.datetime.now()
        payload["iat"] = int(now.timestamp())
        payload["exp"] = int((now + datetime.timedelta(seconds=self.Meta.expiration)).timestamp())
        return payload

    def update_attributes(self, **kwargs: Any) -> None:
        """属性を更新"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                if key == "password":
                    self._validate_password(value)
                    setattr(self, key, self._hash_password(value))
                elif key == "email" and hasattr(self, "email"):
                    self._validate_email(value)
                    setattr(self, key, value)
                else:
                    setattr(self, key, value)

        if self.Meta.auto_timestamps:
            self.updated_at = datetime.datetime.now()

    @classmethod
    def _get_table_name(cls) -> str:
        """テーブル名を取得"""
        return cls.Meta.table_name

    @classmethod
    def _get_expiration(cls) -> int:
        """トークン有効期限を取得"""
        return cls.Meta.expiration

    @classmethod
    def _is_email_login_enabled(cls) -> bool:
        """メールログインが有効かどうか"""
        return cls.Meta.is_email_login

    @classmethod
    def _is_role_permission_enabled(cls) -> bool:
        """ロール権限が有効かどうか"""
        return cls.Meta.is_role_permission

    @classmethod
    def _is_auth_logging_enabled(cls) -> bool:
        """認証ログが有効かどうか"""
        return cls.Meta.enable_auth_logging

    @classmethod
    def _get_endpoint_url(cls) -> Optional[str]:
        """DynamoDB エンドポイント URL を取得"""
        return cls.Meta.endpoint_url
