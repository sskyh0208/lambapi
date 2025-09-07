"""
DynamoDBAuth クラス

DynamoDB 認証システムのメインクラスです。
"""

import datetime
import jwt
import logging
from typing import Dict, Any, Optional, List, Union, Callable, Type
from functools import wraps
from pynamodb.models import Model
from pynamodb.exceptions import PutError

from ..request import Request
from ..exceptions import (
    AuthenticationError,
    ValidationError,
    ConflictError,
    NotFoundError,
    AuthConfigError,
    ModelValidationError,
    PasswordValidationError,
    FeatureDisabledError,
    RolePermissionError,
)


class DynamoDBAuth:
    """DynamoDB 認証システムのメインクラス"""

    def __init__(
        self,
        user_model: Type[Model],
        session_model: Type[Model],
        secret_key: str,
        expiration: int = 3600,
        is_email_login: bool = False,
        is_role_permission: bool = False,
        token_include_fields: Optional[List[str]] = None,
        password_min_length: int = 8,
        password_require_uppercase: bool = False,
        password_require_lowercase: bool = False,
        password_require_digit: bool = True,
        password_require_special: bool = False,
        enable_auth_logging: bool = False,
    ):
        """
        DynamoDBAuth のコンストラクタ

        Args:
            user_model: PynamoDB Model を継承したユーザーモデル
            secret_key: JWT 署名用の秘密鍵
            session_model: セッション管理用のPynamoDB Model（オプション）
            expiration: トークンの有効期限（秒）
            is_email_login: emailログイン機能の有効化
            is_role_permission: ロール権限機能の有効化
            token_include_fields: JWTトークンに含めるフィールドのリスト
            password_min_length: パスワードの最小文字数
            password_require_uppercase: パスワードに大文字を要求するか
            password_require_lowercase: パスワードに小文字を要求するか
            password_require_digit: パスワードに数字を要求するか
            password_require_special: パスワードに特殊文字を要求するか
            enable_auth_logging: 認証ログを有効にするか
        """
        # PynamoDB モデルの検証
        if not hasattr(user_model, "Meta"):
            raise AuthConfigError(
                f"user_model must be a PynamoDB Model, got {type(user_model)}",
                config_type="user_model",
            )

        if not hasattr(session_model, "Meta"):
            raise AuthConfigError(
                f"session_model must be a PynamoDB Model, got {type(session_model)}",
                config_type="session_model",
            )

        # バリデーション実行
        if is_email_login:
            self._validate_email_index(user_model)

        if token_include_fields:
            self._validate_token_fields(user_model, token_include_fields)

        self._validate_session_model(session_model)

        # 設定値の保存
        self.user_model = user_model
        self.session_model = session_model
        self.secret_key = secret_key
        self.expiration = expiration
        self.is_email_login = is_email_login
        self.is_role_permission = is_role_permission
        self.token_include_fields = token_include_fields

        # パスワード設定
        self.password_min_length = password_min_length
        self.password_require_uppercase = password_require_uppercase
        self.password_require_lowercase = password_require_lowercase
        self.password_require_digit = password_require_digit
        self.password_require_special = password_require_special

        # ログ設定
        self.logger = logging.getLogger(__name__)
        if enable_auth_logging:
            self.logger.setLevel(logging.INFO)

    def _validate_email_index(self, user_model):
        """emailログインに必要なGSIの存在チェック"""
        email_index_found = False
        email_index_name = None

        # モデルの属性をチェック
        for attr_name in dir(user_model):
            attr = getattr(user_model, attr_name)
            # GlobalSecondaryIndexの検出
            if hasattr(attr, "Meta") and hasattr(attr.Meta, "index_name"):
                # emailフィールドがhash_keyかチェック
                if hasattr(attr, "email") or "email" in attr_name.lower():
                    email_index_found = True
                    email_index_name = attr_name
                    break

        if not email_index_found:
            raise AuthConfigError(
                f"is_email_login=True requires a GlobalSecondaryIndex with 'email' "
                f"as hash_key in model '{user_model.__name__}'. "
                f"Please define an email index like: email_index = EmailIndex()",
                config_type="email_index",
            )

        # インデックス名を保存（後でクエリ時に使用）
        self._email_index_attr = email_index_name

    def _validate_token_fields(self, user_model, fields: List[str]):
        """トークンフィールドがモデルに存在するかチェック"""
        from pynamodb.attributes import Attribute

        model_attributes = []

        # PynamoDBのAttributeを収集
        for attr_name in dir(user_model):
            attr = getattr(user_model, attr_name)
            if isinstance(attr, Attribute):
                model_attributes.append(attr_name)

        missing_fields = []
        for field in fields:
            if field == "password":
                raise ModelValidationError(
                    "password フィールドはトークンに含めることができません", field_name="password"
                )

            if field not in model_attributes:
                missing_fields.append(field)

        if missing_fields:
            raise ModelValidationError(
                f"以下のフィールドがモデル '{user_model.__name__}' に存在しません: "
                f"{', '.join(missing_fields)}\n"
                f"利用可能なフィールド: {', '.join(sorted(model_attributes))}",
                model_name=user_model.__name__,
                details={
                    "missing_fields": missing_fields,
                    "available_fields": sorted(model_attributes),
                },
            )

    def _validate_session_model(self, session_model) -> None:
        """session_modelのバリデーション"""
        if session_model is None:
            raise AuthConfigError("session_modelは必須です", config_type="session_model")

        # PynamoDBのModelかチェック
        try:
            if not issubclass(session_model, Model):
                raise AuthConfigError(
                    "session_modelはPynamoDBのModelクラスである必要があります",
                    config_type="session_model",
                )
        except ImportError:
            raise AuthConfigError(
                "session_modelを使用するにはPynamoDBが必要です", config_type="session_model"
            )

        # 必要な属性があるかチェック
        required_attributes = ["id", "user_id", "token", "expires_at"]

        try:
            from pynamodb.attributes import Attribute
        except ImportError:
            raise AuthConfigError(
                "session_modelの検証にはPynamoDBが必要です", config_type="session_model"
            )

        # PynamoDBのAttributeを収集
        model_attributes = []
        for attr_name in dir(session_model):
            attr = getattr(session_model, attr_name)
            if isinstance(attr, Attribute):
                model_attributes.append(attr_name)

        missing_attributes = []
        for attr in required_attributes:
            if attr not in model_attributes:
                missing_attributes.append(attr)

        if missing_attributes:
            raise ModelValidationError(
                f"session_model '{session_model.__name__}' に必要な属性が存在しません: "
                f"{', '.join(missing_attributes)}\n"
                f"必要な属性: {', '.join(required_attributes)}\n"
                f"利用可能な属性: {', '.join(sorted(model_attributes))}",
                model_name=session_model.__name__,
                details={
                    "missing_attributes": missing_attributes,
                    "required_attributes": required_attributes,
                    "available_attributes": sorted(model_attributes),
                },
            )

    def _validate_password(self, password: str) -> None:
        """パスワードのバリデーション"""
        import re

        if len(password) < self.password_min_length:
            raise PasswordValidationError(
                f"パスワードは{self.password_min_length}文字以上である必要があります",
                requirement_type="min_length",
            )

        if self.password_require_uppercase and not re.search(r"[A-Z]", password):
            raise PasswordValidationError(
                "パスワードには大文字を含める必要があります", requirement_type="uppercase"
            )

        if self.password_require_lowercase and not re.search(r"[a-z]", password):
            raise PasswordValidationError(
                "パスワードには小文字を含める必要があります", requirement_type="lowercase"
            )

        if self.password_require_digit and not re.search(r"\d", password):
            raise PasswordValidationError(
                "パスワードには数字を含める必要があります", requirement_type="digit"
            )

        if self.password_require_special and not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
            raise PasswordValidationError(
                "パスワードには特殊文字を含める必要があります", requirement_type="special_char"
            )

    def _validate_email(self, email: str) -> None:
        """emailアドレスの形式バリデーション"""
        import re

        if not email:
            raise ValidationError("email は必須です")

        # より厳密なメール形式チェック
        email_pattern = (
            r"^[a-zA-Z0-9]([a-zA-Z0-9._-]*[a-zA-Z0-9])?@"
            r"[a-zA-Z0-9]([a-zA-Z0-9.-]*[a-zA-Z0-9])?\.[a-zA-Z]{2,}$"
        )
        if not re.match(email_pattern, email):
            raise ValidationError("有効なメールアドレスを入力してください")

        # 連続するドットをチェック
        if ".." in email:
            raise ValidationError("有効なメールアドレスを入力してください")

        # メールアドレスの長さチェック
        if len(email) > 254:  # RFC 5321での制限
            raise ValidationError("メールアドレスは254文字以内である必要があります")

        # ローカル部の長さチェック
        local_part = email.split("@")[0]
        if len(local_part) > 64:  # RFC 5321での制限
            raise ValidationError("メールアドレスのローカル部は64文字以内である必要があります")

    def _verify_password_hash(self, hashed_password: str, password: str) -> bool:
        """ハッシュ化されたパスワードを検証"""
        import bcrypt

        return bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))

    def _hash_password(self, password: str) -> str:
        """パスワードをハッシュ化"""
        # パスワードバリデーション実行
        self._validate_password(password)

        import bcrypt

        hashed_bytes = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
        return hashed_bytes.decode("utf-8")

    def _create_token_payload(self, user) -> Dict[str, Any]:
        """JWTトークンのペイロードを生成"""
        import datetime
        import decimal
        import base64

        payload: Dict[str, Any] = {}

        # token_include_fieldsが指定されている場合はそれを使用
        if self.token_include_fields:
            for field in self.token_include_fields:
                if hasattr(user, field) and field != "password":
                    value = getattr(user, field)
                    # PynamoDB型の変換
                    if isinstance(value, datetime.datetime):
                        payload[field] = value.isoformat()
                    elif isinstance(value, decimal.Decimal):
                        converted_value: Union[float, int] = (
                            float(value) if value % 1 != 0 else int(value)
                        )
                        payload[field] = converted_value
                    elif isinstance(value, bytes):
                        payload[field] = base64.b64encode(value).decode("utf-8")
                    elif isinstance(value, (set, frozenset)):
                        payload[field] = list(value)
                    else:
                        payload[field] = value
        else:
            # デフォルト: 全フィールド（passwordは除外）
            for attr_name in dir(user):
                if not attr_name.startswith("_") and attr_name != "password":
                    try:
                        value = getattr(user, attr_name)
                        if not callable(value):
                            payload[attr_name] = value
                    except AttributeError:
                        continue

        # JWT標準フィールドを追加
        now = datetime.datetime.now()
        payload["iat"] = int(now.timestamp())
        payload["exp"] = int((now + datetime.timedelta(seconds=self.expiration)).timestamp())

        return payload

    def _generate_jwt_token(self, user) -> str:
        """JWT トークンを生成"""
        payload = self._create_token_payload(user)
        token = jwt.encode(payload, self.secret_key, algorithm="HS256")
        return str(token)

    def _decode_jwt_token(self, token: str) -> Dict[str, Any]:
        """JWT トークンをデコード"""
        try:
            decoded = jwt.decode(token, self.secret_key, algorithms=["HS256"])
            return dict(decoded)
        except jwt.ExpiredSignatureError:
            raise AuthenticationError("トークンの有効期限が切れています")
        except jwt.InvalidTokenError:
            raise AuthenticationError("無効なトークンです")

    def _generate_id(self, user_id: str) -> str:
        """セッションIDを生成"""
        return f"session_{user_id}"

    def _save_session(self, user, token: str, payload: Dict[str, Any]) -> None:
        """セッション情報を DynamoDB に保存"""
        try:
            id = self._generate_id(user.id)
            ttl = payload.get("exp", int(datetime.datetime.now().timestamp()) + self.expiration)

            # セッション作成/更新
            session = self.session_model()
            setattr(session, "id", id)
            setattr(session, "user_id", user.id)
            setattr(session, "token", token)
            setattr(session, "expires_at", ttl)
            session.save()

        except Exception as e:
            self.logger.error(f"セッション保存エラー: {str(e)}")
            raise AuthenticationError("セッションの保存に失敗しました")

    def _verify_session(self, user, token: str) -> bool:
        """セッション情報を DynamoDB で検証"""
        try:
            id = self._generate_id(user.id)

            try:
                session = self.session_model.get(id)

                # トークンが一致するかチェック
                if getattr(session, "token") != token:
                    return False

                # セッションの有効期限をチェック
                now = int(datetime.datetime.now().timestamp())
                expires_at = getattr(session, "expires_at", None)
                if expires_at and expires_at < now:
                    # 期限切れセッションを削除
                    session.delete()
                    return False

                return True

            except self.session_model.DoesNotExist:
                return False

        except Exception as e:
            self.logger.error(f"セッション検証エラー: {str(e)}")
            return False

    def _delete_session(self, user) -> None:
        """セッション情報を DynamoDB から削除"""
        try:
            id = self._generate_id(user.id)

            try:
                session = self.session_model.get(id)
                session.delete()
            except self.session_model.DoesNotExist:
                # セッションが存在しない場合はスキップ
                pass

        except Exception as e:
            self.logger.error(f"セッション削除エラー: {str(e)}")

    def _get_user_by_id(self, user_id: Optional[str]):
        """ユーザー ID でユーザーを取得"""
        if not user_id:
            return None

        try:
            return self.user_model.get(user_id)
        except self.user_model.DoesNotExist:
            return None
        except Exception as e:
            self.logger.error(f"ユーザー取得エラー: {str(e)}")
            return None

    def _save_user(self, user) -> None:
        """ユーザーを DynamoDB に保存"""
        try:
            user.save()
        except Exception as e:
            self.logger.error(f"ユーザー保存エラー: {str(e)}")
            raise ConflictError("ユーザーの保存に失敗しました")

    def _delete_user(self, user_id: str) -> None:
        """ユーザーを DynamoDB から削除"""
        try:
            user = self.user_model.get(user_id)
            user.delete()
        except self.user_model.DoesNotExist:
            raise NotFoundError("ユーザーが見つかりません")
        except Exception as e:
            self.logger.error(f"ユーザー削除エラー: {str(e)}")
            raise NotFoundError("ユーザーの削除に失敗しました")

    def signup(self, user: Any) -> str:
        """ユーザー登録（PynamoDB Model対応）"""
        # Modelインスタンスかチェック
        try:
            if not isinstance(user, Model):
                raise ModelValidationError(
                    "user は PynamoDB Model インスタンスである必要があります", model_name="user"
                )
        except ImportError:
            raise AuthConfigError("PynamoDB が必要です", config_type="dependencies")

        # 必須フィールドの検証
        if not hasattr(user, "id") or not getattr(user, "id"):
            raise ValidationError("id は必須です")
        if not hasattr(user, "password") or not getattr(user, "password"):
            raise ValidationError("password は必須です")

        # emailログインが有効化されている場合は、emailフィールドの検証も行う
        if self.is_email_login:
            if not hasattr(user, "email") or not getattr(user, "email"):
                raise ValidationError("email は必須です")
            # emailバリデーション実行
            self._validate_email(getattr(user, "email"))

        # パスワードをハッシュ化（バリデーション込み）
        hashed_password = self._hash_password(getattr(user, "password"))
        setattr(user, "password", hashed_password)

        # 既存ユーザーチェック
        try:
            # ユーザー保存
            id_attr = getattr(self.user_model, "id")
            user.save(condition=id_attr.does_not_exist())
        except PutError as pe:
            if "ConditionalCheckFailedException" in str(pe):
                raise ConflictError("ユーザーIDは既に存在します")
            else:
                raise ValidationError(f"ユーザーの保存に失敗しました: {str(pe)}")
        try:
            # 作成されたユーザーでトークン生成
            token = self._generate_jwt_token(user)
            payload = self._create_token_payload(user)

            # セッション保存
            self._save_session(user, token, payload)

            return token

        except Exception as e:
            raise ValidationError(f"ユーザーの作成に失敗しました: {str(e)}")

    def login(self, user_id: str, password: str) -> str:
        """IDでユーザーログイン"""
        try:
            # PynamoDBでユーザー取得
            user = self.user_model.get(user_id)

        except self.user_model.DoesNotExist:
            raise AuthenticationError("認証に失敗しました")

        # パスワード検証
        if not self._verify_password_hash(getattr(user, "password"), password):
            raise AuthenticationError("認証に失敗しました")

        # JWT トークン生成
        token = self._generate_jwt_token(user)
        payload = self._create_token_payload(user)

        # セッション保存
        self._save_session(user, token, payload)

        return token

    def email_login(self, email: str, password: str) -> str:
        """emailでユーザーログイン（GSI使用）"""
        if not self.is_email_login:
            raise FeatureDisabledError(
                "Emailログインは無効化されています", feature_name="email_login"
            )

        if not self._email_index_attr:
            raise AuthConfigError(
                "Emailログイン用のGSIが設定されていません", config_type="email_index"
            )

        try:
            # GSIを使ってemailで検索
            email_index = getattr(self.user_model, self._email_index_attr)
            users = list(email_index.query(email))

            if not users:
                raise AuthenticationError("認証に失敗しました")

            user = users[0]

            # パスワード検証
            if not self._verify_password_hash(getattr(user, "password"), password):
                raise AuthenticationError("認証に失敗しました")
            # JWT トークン生成
            token = self._generate_jwt_token(user)
            payload = self._create_token_payload(user)

            # セッション保存
            self._save_session(user, token, payload)

            return token

        except Exception as e:
            if isinstance(e, AuthenticationError):
                raise
            else:
                raise AuthenticationError("認証に失敗しました")

    def logout(self, user) -> Dict[str, Any]:
        """ユーザーログアウト"""

        try:
            self._delete_session(user)
        except Exception as e:
            self.logger.error(f"ログアウトエラー: {str(e)}")

        return {"message": "ログアウトしました"}

    def delete_user(self, user_id: str) -> Dict[str, Any]:
        """ユーザー削除"""
        user = self._get_user_by_id(user_id)
        if not user:
            raise NotFoundError("ユーザーが見つかりません")

        self._delete_user(user_id)

        return {"message": "ユーザーを削除しました"}

    def update_password(self, id: str, new_password: str):
        """パスワード更新"""
        if not id:
            raise ValidationError("id は必須です")

        if not new_password:
            raise ValidationError("new_password は必須です")

        try:
            user = self._get_user_by_id(id)
            if not user:
                raise NotFoundError("ユーザーが見つかりません")

            # パスワードをハッシュ化してアップデート
            hashed_password = self._hash_password(new_password)
            user.password = hashed_password
            user.save()

            return user
        except Exception as e:
            if isinstance(e, (ValidationError, NotFoundError)):
                raise
            raise ValidationError(str(e))

    def _extract_token(self, request: Request) -> Optional[str]:
        """リクエストからトークンを抽出"""
        auth_header = request.headers.get("Authorization") or request.headers.get("authorization")
        if not auth_header:
            return None

        if not auth_header.startswith("Bearer "):
            return None

        return auth_header[7:]

    def get_authenticated_user(self, request: Request):
        """認証済みユーザーを取得"""
        token = self._extract_token(request)
        if not token:
            raise AuthenticationError("認証トークンが見つかりません")

        # JWT トークンの検証
        payload = self._decode_jwt_token(token)

        # ユーザーIDを取得してユーザーを再取得
        user_id = payload.get("id")
        if not user_id:
            raise AuthenticationError("無効なトークンです")

        user = self._get_user_by_id(user_id)
        if not user:
            raise AuthenticationError("ユーザーが見つかりません")

        # セッション検証
        if not self._verify_session(user, token):
            raise AuthenticationError("セッションが無効です")

        return user

    def require_role(self, required_roles: Union[str, List[str]]) -> Callable:
        """ロールベースの認証デコレータ"""
        if isinstance(required_roles, str):
            required_roles = [required_roles]

        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                import inspect
                from ..dependencies import get_function_dependencies

                sig = inspect.signature(func)

                # リクエストオブジェクトを取得（kwargs から）
                request = kwargs.get("request")
                if not request:
                    # args からも探してみる
                    for arg in args:
                        if hasattr(arg, "headers") and hasattr(
                            arg, "json"
                        ):  # Request オブジェクトの特徴
                            request = arg
                            break

                if not request:
                    # リクエストオブジェクトが見つからない場合、現在のコンテキストから取得を試す
                    import sys

                    frame = sys._getframe()
                    while frame:
                        if "request" in frame.f_locals:
                            request = frame.f_locals["request"]
                            if hasattr(request, "headers") and hasattr(request, "json"):
                                break
                        frame = frame.f_back  # type: ignore

                    if not request:
                        raise AuthenticationError("リクエストオブジェクトが見つかりません")

                # ユーザー認証
                user = self.get_authenticated_user(request)

                # ロール権限チェック
                if self.is_role_permission:
                    user_role = getattr(user, "role", None)
                    if user_role not in required_roles:
                        raise RolePermissionError(
                            f"必要なロール: {', '.join(required_roles)}",
                            user_role=user_role,
                            required_roles=required_roles,
                            resource="endpoint",
                            action="access",
                        )

                # 認証されたユーザーを request オブジェクトに保存（依存性注入システム用）
                setattr(request, "_authenticated_user", user)

                # 新しい依存性注入システムが使用されているかチェック
                dependencies = get_function_dependencies(func)
                if dependencies:
                    # 依存性注入システムが使用されている場合、
                    # 認証ユーザーは自動的に注入されるので、そのまま実行
                    return func(*args, **kwargs)
                else:
                    # 従来のシステム：user パラメータを手動注入
                    if "user" in sig.parameters:
                        # user を適切な位置に注入
                        if kwargs:
                            kwargs["user"] = user
                            return func(*args, **kwargs)
                        else:
                            # user を最初の引数として渡し、残りの引数を続ける
                            return func(user, *args, **kwargs)
                    else:
                        # user パラメータがない場合はそのまま実行
                        return func(*args, **kwargs)

            # ラップされた関数に元の関数の属性を保持
            wrapper._auth_required = True  # type: ignore
            wrapper._required_roles = required_roles  # type: ignore
            return wrapper

        return decorator

    def validate_password(self, password: str) -> None:
        """パスワードのバリデーション"""
        self._validate_password(password)

    def hash_password(self, password: str) -> str:
        """パスワードをハッシュ化"""
        return self._hash_password(password)

    def decode_token(self, token: str) -> Dict[str, Any]:
        """JWTトークンをデコードして情報を取得

        Args:
            token: デコードするJWTトークン

        Returns:
            Dict[str, Any]: トークンの情報（ペイロード）

        Raises:
            AuthenticationError: トークンが無効または期限切れの場合
        """
        return self._decode_jwt_token(token)
