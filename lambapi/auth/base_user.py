"""
BaseUser クラス

DynamoDB 認証システムの基本的なユーザーモデルです。
"""

import datetime
import hashlib
import re
from typing import Optional, Any, Dict

try:
    import bcrypt

    BCRYPT_AVAILABLE = True
except ImportError:
    BCRYPT_AVAILABLE = False


class Meta:
    """BaseUser のデフォルトメタ設定"""

    table_name = "users"
    expiration = 3600
    is_role_permission = False
    password_min_length = 8
    password_require_uppercase = False
    password_require_lowercase = False
    password_require_digit = True
    password_require_special = False
    enable_auth_logging = False
    auto_timestamps = True
    endpoint_url: Optional[str] = None
    token_include_fields: Optional[list] = None


class BaseUser:
    """基本的なユーザーモデルクラス"""

    Meta = Meta

    # 型ヒント用の属性定義
    id: Optional[str]
    password: Optional[str]

    def __init__(self, *args, **kwargs):
        """
        基本的なユーザーモデルのコンストラクタ
        """
        for key, value in kwargs.items():
            setattr(self, key, value)

    def _validate_password(self, password: str) -> None:
        """パスワードのバリデーション"""
        self.validate_password(password)

    @classmethod
    def validate_password(cls, password: str) -> None:
        """パスワードのバリデーション（クラスメソッド版）"""
        if len(password) < cls.Meta.password_min_length:
            raise ValueError(
                f"パスワードは{cls.Meta.password_min_length}文字以上である必要があります"
            )

        if cls.Meta.password_require_uppercase and not re.search(r"[A-Z]", password):
            raise ValueError("パスワードには大文字を含める必要があります")

        if cls.Meta.password_require_lowercase and not re.search(r"[a-z]", password):
            raise ValueError("パスワードには小文字を含める必要があります")

        if cls.Meta.password_require_digit and not re.search(r"\d", password):
            raise ValueError("パスワードには数字を含める必要があります")

        if cls.Meta.password_require_special and not re.search(
            r"[!@#$%^&*(),.?\":{}|<>]", password
        ):
            raise ValueError("パスワードには特殊文字を含める必要があります")

    def _hash_password(self, password: str) -> str:
        """パスワードをハッシュ化"""
        return self.hash_password(password)

    @classmethod
    def hash_password(cls, password: str) -> str:
        """パスワードをハッシュ化（クラスメソッド版）"""
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

    def _validate_token_fields(self, fields: list) -> None:
        """トークンフィールドのバリデーション"""
        if not isinstance(fields, list):
            raise ValueError("token_include_fields はリスト形式である必要があります")

        for field in fields:
            if not isinstance(field, str):
                raise ValueError("token_include_fields の要素は文字列である必要があります")

            # password は常に禁止
            if field == "password":
                raise ValueError("password フィールドはトークンに含めることができません")

            # 存在しないプロパティの警告（実行時チェック）
            if not hasattr(self, field):
                # ログ出力などで警告するが、エラーにはしない
                raise ValueError(f"警告: フィールド '{field}' は存在しません")

    def to_dict(self, include_password: bool = False) -> Dict[str, Any]:
        """オブジェクトを辞書形式に変換"""
        import decimal
        import base64
        from typing import Any

        result: Dict[str, Any] = {}
        for key, value in self.__dict__.items():
            if key == "password" and not include_password:
                continue
            if isinstance(value, datetime.datetime):
                result[key] = value.isoformat()
            elif isinstance(value, decimal.Decimal):
                result[key] = float(value) if value % 1 != 0 else int(value)
            elif isinstance(value, bytes):
                result[key] = base64.b64encode(value).decode("utf-8")
            elif isinstance(value, (set, frozenset)):
                result[key] = list(value)
            else:
                result[key] = value
        return result

    def to_token_payload(self) -> Dict[str, Any]:
        """JWT トークンのペイロード用辞書を生成（パスワード除外）"""
        import decimal
        import base64

        # バリデーション: token_include_fieldsの妥当性チェック
        include_fields = self.Meta.token_include_fields
        if include_fields is not None:
            self._validate_token_fields(include_fields)

        if include_fields is None:
            # デフォルト: 全フィールド（passwordは除外）
            payload = self.to_dict(include_password=False)
        else:
            # カスタム: 指定されたフィールドのみ
            payload = {}
            for field in include_fields:
                if hasattr(self, field) and field != "password":
                    value = getattr(self, field)
                    if isinstance(value, datetime.datetime):
                        payload[field] = value.isoformat()
                    elif isinstance(value, decimal.Decimal):
                        payload[field] = float(value) if value % 1 != 0 else int(value)
                    elif isinstance(value, bytes):
                        payload[field] = base64.b64encode(value).decode("utf-8")
                    elif isinstance(value, (set, frozenset)):
                        payload[field] = list(value)
                    else:
                        payload[field] = value

        # DynamoDB型の変換処理をpayload全体に適用
        def convert_dynamodb_types(obj):
            if isinstance(obj, decimal.Decimal):
                return float(obj) if obj % 1 != 0 else int(obj)
            elif isinstance(obj, bytes):
                return base64.b64encode(obj).decode("utf-8")
            elif isinstance(obj, (set, frozenset)):
                return list(obj)
            elif isinstance(obj, dict):
                return {k: convert_dynamodb_types(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_dynamodb_types(item) for item in obj]
            return obj

        payload = convert_dynamodb_types(payload)

        # JWT標準フィールドを追加
        now = datetime.datetime.now()
        payload["iat"] = int(now.timestamp())
        payload["exp"] = int((now + datetime.timedelta(seconds=self.Meta.expiration)).timestamp())
        return payload

    @classmethod
    def decode_token_payload(cls, token: str, secret_key: str) -> Dict[str, Any]:
        """JWTトークンをデコードしてペイロードを取得"""
        try:
            import jwt

            decoded = jwt.decode(token, secret_key, algorithms=["HS256"])
            return dict(decoded)
        except ImportError:
            raise RuntimeError("JWT library is not available")
        except jwt.ExpiredSignatureError:
            raise ValueError("トークンの有効期限が切れています")
        except jwt.InvalidTokenError:
            raise ValueError("無効なトークンです")

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
