"""
DynamoDB 認証モジュール

DynamoDB を使用した認証機能を提供します。
JWT トークンベースの認証とルーティング制御を実装。
"""

import hashlib
import hmac
import json
import time
import base64
import inspect
from typing import Dict, Any, Optional, Callable, Type
from functools import wraps

try:
    import boto3
    from boto3.dynamodb.conditions import Key
    import bcrypt
except ImportError:
    boto3 = None
    bcrypt = None

from .exceptions import AuthenticationError, AuthorizationError, ValidationError
from .request import Request


class BaseUser:
    """ユーザーモデルの基底クラス"""

    # バリデーション設定（継承クラスでオーバーライド可能）
    REQUIRED_FIELDS = ["user_id", "id"]  # user_id または id が必要

    def __init__(self, data: Dict[str, Any], validate: bool = True, require_email: bool = False):
        """ユーザーデータから初期化

        Args:
            data: ユーザーデータ辞書
            validate: バリデーションを実行するかどうか（デフォルト: True）
            require_email: email を必須にするかどうか（デフォルト: False）

        継承クラスでは、コンストラクタ内でカスタム属性を定義できます：

        Example:
            class CustomUser(BaseUser):
                def __init__(self, data: Dict[str, Any], **kwargs):
                    super().__init__(data, **kwargs)
                    self.full_name = f"{self.first_name} {self.last_name}"
                    self.is_admin = self._data.get('role') == 'admin'
        """
        self._data = data
        self._require_email = require_email

        # バリデーション実行
        if validate:
            self._validate_data()

        # 基本フィールドを属性として設定
        # プロパティと重複しないフィールドのみ設定
        for key, value in data.items():
            if not hasattr(self.__class__, key) or not isinstance(
                getattr(self.__class__, key), property
            ):
                setattr(self, key, value)

        # 継承クラスでのカスタム属性定義のために呼び出し
        self._setup_custom_attributes()

    def _validate_data(self) -> None:
        """データのバリデーション"""
        # user_id または id のいずれかが必要
        has_user_id = any(
            field in self._data and self._data[field] for field in self.REQUIRED_FIELDS
        )

        if not has_user_id:
            raise ValidationError(f"One of {self.REQUIRED_FIELDS} is required")

        # email が必須の場合はチェック
        if self._require_email:
            if "email" not in self._data or not self._data["email"]:
                raise ValidationError("email is required")

    def _setup_custom_attributes(self) -> None:
        """カスタム属性の設定（継承クラスでオーバーライド可能）"""
        pass

    @property
    def user_id(self) -> str:
        """ユーザー ID を取得"""
        return str(self._data.get("user_id") or self._data.get("id", ""))

    @property
    def email(self) -> Optional[str]:
        """メールアドレスを取得"""
        return self._data.get("email")

    def to_dict(self) -> Dict[str, Any]:
        """辞書形式でデータを返す"""
        return self._data.copy()

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(user_id={self.user_id})"


class TokenManager:
    """JWT 風のトークン管理クラス（シンプル実装）"""

    def __init__(self, secret_key: Optional[str] = None):
        if secret_key is None:
            secret_key = "lambapi-default-secret"  # nosec B105
        self.secret_key = secret_key.encode("utf-8")

    def generate_token(self, payload: Dict[str, Any], expires_in: int = 3600) -> str:
        """トークンを生成"""
        current_time = int(time.time())
        payload.update({"iat": current_time, "exp": current_time + expires_in})

        # ヘッダー
        header = {"alg": "HS256", "typ": "JWT"}
        header_b64 = (
            base64.urlsafe_b64encode(json.dumps(header, separators=(",", ":")).encode())
            .decode()
            .rstrip("=")
        )

        # ペイロード
        payload_b64 = (
            base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode())
            .decode()
            .rstrip("=")
        )

        # 署名
        message = f"{header_b64}.{payload_b64}".encode()
        signature = hmac.new(self.secret_key, message, hashlib.sha256).digest()
        signature_b64 = base64.urlsafe_b64encode(signature).decode().rstrip("=")

        return f"{header_b64}.{payload_b64}.{signature_b64}"

    def verify_token(self, token: str) -> Dict[str, Any]:
        """トークンを検証してペイロードを返す"""
        try:
            parts = token.split(".")
            if len(parts) != 3:
                raise AuthenticationError("Invalid token format")

            header_b64, payload_b64, signature_b64 = parts

            # 署名検証
            message = f"{header_b64}.{payload_b64}".encode()
            expected_signature = hmac.new(self.secret_key, message, hashlib.sha256).digest()
            expected_signature_b64 = (
                base64.urlsafe_b64encode(expected_signature).decode().rstrip("=")
            )

            if not hmac.compare_digest(signature_b64, expected_signature_b64):
                raise AuthenticationError("Invalid token signature")

            # ペイロード解析
            payload_padded = payload_b64 + "=" * (4 - len(payload_b64) % 4)
            payload_json = base64.urlsafe_b64decode(payload_padded).decode()
            payload = json.loads(payload_json)

            # 有効期限チェック
            if "exp" in payload:
                if int(time.time()) > payload["exp"]:
                    raise AuthenticationError("Token has expired")

            return dict(payload)

        except (ValueError, json.JSONDecodeError, KeyError) as e:
            raise AuthenticationError(f"Invalid token: {str(e)}")


class DynamoDBAuth:
    """DynamoDB 認証クラス"""

    def __init__(
        self,
        table_name: str,
        id_field: str = "id",
        use_email: bool = False,
        region_name: str = "us-east-1",
        secret_key: Optional[str] = None,
        user_model: Optional[Type[BaseUser]] = None,
    ):
        if not boto3:
            raise ImportError(
                "boto3 is required for DynamoDB authentication. " "Install with: pip install boto3"
            )
        if not bcrypt:
            raise ImportError(
                "bcrypt is required for password hashing. " "Install with: pip install bcrypt"
            )

        self.table_name = table_name
        self.id_field = id_field
        self.use_email = use_email
        self.region_name = region_name
        self.user_model = user_model or BaseUser

        # DynamoDB クライアント初期化
        self.dynamodb = boto3.resource("dynamodb", region_name=region_name)
        self.table = self.dynamodb.Table(table_name)

        # トークンマネージャー初期化
        self.token_manager = TokenManager(secret_key)

        # 無効化されたトークンを保存（簡易実装）
        self.revoked_tokens: set = set()

    def _create_user_instance(self, data: Dict[str, Any]) -> BaseUser:
        """認証設定を考慮してユーザーインスタンスを作成"""
        try:
            if self.user_model != BaseUser:
                # カスタムユーザーモデルの場合
                # 可能であれば認証設定を渡す
                try:
                    return self.user_model(data, require_email=self.use_email)
                except TypeError:
                    # require_email パラメータをサポートしていない場合
                    return self.user_model(data)
            else:
                # BaseUser の場合は認証設定を考慮してバリデーション
                return BaseUser(data, validate=True, require_email=self.use_email)
        except ValidationError as e:
            # ユーザーモデル作成時のバリデーションエラー
            raise AuthenticationError(f"Invalid user data: {str(e)}")

    def _hash_password(self, password: str) -> str:
        """パスワードをハッシュ化"""
        salt = bcrypt.gensalt()
        return str(bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8"))

    def _verify_password(self, password: str, hashed: str) -> bool:
        """パスワードを検証"""
        return bool(bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8")))

    def sign_up(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """新規ユーザー登録"""
        # 必須フィールドチェック
        required_fields = [self.id_field, "password"]
        if self.use_email and "email" not in data:
            required_fields.append("email")

        for field in required_fields:
            if field not in data or not data[field]:
                raise ValidationError(f"{field} is required")

        # パスワードハッシュ化
        hashed_password = self._hash_password(data["password"])

        # ユーザーデータ作成
        user_data = {
            self.id_field: data[self.id_field],
            "password": hashed_password,
            "created_at": int(time.time()),
        }

        if "email" in data:
            user_data["email"] = data["email"]

        # 追加フィールド
        for key, value in data.items():
            if key not in [self.id_field, "password", "email", "created_at"]:
                user_data[key] = value

        try:
            # DynamoDB に保存（重複チェック付き）
            self.table.put_item(
                Item=user_data, ConditionExpression=(f"attribute_not_exists({self.id_field})")
            )

            # レスポンス用データ（パスワードは除外）
            response_data = {k: v for k, v in user_data.items() if k != "password"}

            return {"message": "User created successfully", "user": response_data}

        except self.dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
            raise ValidationError(
                f"User with {self.id_field} '{data[self.id_field]}' " "already exists"
            )

    def login(self, credential: str, password: str) -> Dict[str, Any]:
        """ログイン処理"""
        try:
            # ユーザー取得
            if self.use_email and "@" in credential:
                # email でスキャン
                response = self.table.scan(FilterExpression=Key("email").eq(credential))
                users = response.get("Items", [])
                if not users:
                    raise AuthenticationError("Invalid credentials")
                user = users[0]
            else:
                # ID で直接取得
                response = self.table.get_item(Key={self.id_field: credential})
                user = response.get("Item")
                if not user:
                    raise AuthenticationError("Invalid credentials")

            # パスワード検証
            if not self._verify_password(password, user["password"]):
                raise AuthenticationError("Invalid credentials")

            # トークン生成
            token_payload = {"user_id": user[self.id_field], "email": user.get("email")}
            token = self.token_manager.generate_token(token_payload)

            # レスポンス用データ（パスワードは除外）
            user_data = {k: v for k, v in user.items() if k != "password"}

            return {"token": token, "user": user_data, "expires_in": 3600}

        except Exception as e:
            if isinstance(e, AuthenticationError):
                raise
            raise AuthenticationError("Login failed")

    def logout(self, token: str) -> Dict[str, Any]:
        """ログアウト処理（トークン無効化）"""
        try:
            # トークン検証（有効性チェック）
            self.token_manager.verify_token(token)

            # 無効化リストに追加
            self.revoked_tokens.add(token)

            return {"message": "Logged out successfully"}

        except AuthenticationError:
            raise AuthenticationError("Invalid token")

    def verify_token(self, token: str) -> Dict[str, Any]:
        """トークン検証・解析"""
        if token in self.revoked_tokens:
            raise AuthenticationError("Token has been revoked")

        return self.token_manager.verify_token(token)

    def require_auth(self, func: Callable) -> Callable:
        """認証必須デコレータ"""

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Request オブジェクトを取得
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break

            if not request:
                # kwargs から取得を試行
                request = kwargs.get("request")

            if not request:
                raise AuthorizationError("Request object not found")

            # Authorization ヘッダーからトークンを取得
            auth_header = request.headers.get("authorization") or request.headers.get(
                "Authorization"
            )
            if not auth_header:
                raise AuthenticationError("Authorization header missing")

            if not auth_header.startswith("Bearer "):
                raise AuthenticationError("Invalid authorization header format")

            token = auth_header[7:]  # 'Bearer ' を除去

            try:
                # トークン検証
                payload = self.verify_token(token)

                # ユーザーモデルを作成（認証設定を考慮したバリデーション）
                user_instance = self._create_user_instance(payload)

                # 関数のシグネチャを解析
                sig = inspect.signature(func)
                params = list(sig.parameters.keys())

                # user パラメータがある場合は user インスタンスを渡す
                if "user" in params:
                    kwargs["user"] = user_instance
                else:
                    # 従来の方式: request にユーザー情報を追加
                    setattr(request, "user", payload)

                return func(*args, **kwargs)

            except AuthenticationError:
                raise

        return wrapper

    def get_auth_routes(self) -> list[Any]:
        """認証用ルートを取得"""
        from .core import Route

        def signup_handler(request: Request) -> Dict[str, Any]:
            try:
                data = request.json()
                return self.sign_up(data)
            except Exception as e:
                if isinstance(e, (ValidationError, AuthenticationError)):
                    raise
                raise ValidationError(f"Signup failed: {str(e)}")

        def login_handler(request: Request) -> Dict[str, Any]:
            try:
                data = request.json()
                credential_field = "email" if self.use_email else self.id_field
                credential = data.get(credential_field)
                password = data.get("password")

                if not credential or not password:
                    raise ValidationError(f"{credential_field} and password are required")

                return self.login(credential, password)
            except Exception as e:
                if isinstance(e, (ValidationError, AuthenticationError)):
                    raise
                raise ValidationError(f"Login failed: {str(e)}")

        def logout_handler(request: Request) -> Dict[str, Any]:
            auth_header = request.headers.get("authorization") or request.headers.get(
                "Authorization"
            )
            if not auth_header or not auth_header.startswith("Bearer "):
                raise AuthenticationError("Invalid authorization header")

            token = auth_header[7:]
            return self.logout(token)

        routes = [
            Route("/auth/signup", "POST", signup_handler),
            Route("/auth/login", "POST", login_handler),
            Route("/auth/logout", "POST", logout_handler),
        ]

        return routes
