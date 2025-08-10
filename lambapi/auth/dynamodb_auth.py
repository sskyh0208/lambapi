"""
DynamoDBAuth クラス

DynamoDB 認証システムのメインクラスです。
"""

import json
import datetime
import logging
import hashlib
from typing import Dict, Any, Optional, Type, List, Union, Callable
from functools import wraps

try:
    import boto3
    from botocore.exceptions import ClientError

    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False
    ClientError = Exception

try:
    import jwt

    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False

from .base_user import BaseUser
from ..request import Request
from ..exceptions import (
    AuthenticationError,
    AuthorizationError,
    ValidationError,
    ConflictError,
    NotFoundError,
)


class DynamoDBAuth:
    """DynamoDB 認証システムのメインクラス"""

    def __init__(
        self, custom_user: Optional[Type[BaseUser]] = None, secret_key: Optional[str] = None
    ):
        """
        DynamoDBAuth のコンストラクタ

        Args:
            custom_user: カスタムユーザーモデル（BaseUser を継承したクラス）
            secret_key: JWT 署名用の秘密鍵（優先度最高）
        """
        import os

        self.user_model = custom_user or BaseUser
        self.table_name = self.user_model._get_table_name()
        self.expiration = self.user_model._get_expiration()

        # secret_key の優先順位
        if secret_key:
            # 優先度 1: 明示的指定
            self.secret_key = secret_key
        else:
            # 優先度 2: 環境変数
            env_key = os.getenv("LAMBAPI_SECRET_KEY")
            if env_key:
                self.secret_key = env_key
            else:
                # エラー: どちらも設定されていない
                raise ValueError(
                    "Secret key is required for JWT authentication.\n"
                    "Set it via: DynamoDBAuth(secret_key='your-key') or "
                    "export LAMBAPI_SECRET_KEY='your-key'"
                )

        # DynamoDB クライアントの初期化
        endpoint_url = self.user_model._get_endpoint_url()
        if endpoint_url:
            self.dynamodb = boto3.resource("dynamodb", endpoint_url=endpoint_url)
        else:
            self.dynamodb = boto3.resource("dynamodb")

        self.table = self.dynamodb.Table(self.table_name)

        # ログ設定
        self.logger = logging.getLogger(__name__)
        if self.user_model._is_auth_logging_enabled():
            self.logger.setLevel(logging.INFO)

    def _log_auth_event(
        self, event: str, user_id: Optional[str] = None, details: Optional[Dict[str, Any]] = None
    ) -> None:
        """認証イベントのログ出力"""
        if self.user_model._is_auth_logging_enabled():
            log_data = {
                "event": event,
                "timestamp": datetime.datetime.now().isoformat(),
                "user_id": user_id,
                "details": details or {},
            }
            self.logger.info(f"Auth Event: {json.dumps(log_data)}")

    def _generate_jwt_token(self, user: BaseUser) -> str:
        """JWT トークンを生成"""
        payload = user.to_token_payload()
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

    def _generate_session_id(self, user: BaseUser) -> str:
        """ユーザー情報から短いセッション ID を生成"""
        # ユーザー ID と secret_key を組み合わせてハッシュ化し、最初の 16 文字を使用
        user_info = f"{user.id}_{self.secret_key}"
        full_hash = hashlib.sha256(user_info.encode("utf-8")).hexdigest()
        return full_hash[:16]  # 16 文字で十分一意

    def _save_session(self, user: BaseUser, token: str, payload: Dict[str, Any]) -> None:
        """セッション情報を DynamoDB に保存"""
        try:
            session_id = self._generate_session_id(user)
            ttl = (
                int(payload["exp"].timestamp())
                if isinstance(payload["exp"], datetime.datetime)
                else payload["exp"]
            )

            session_item = {
                "id": session_id,
                "token": token,
                "user_id": user.id,
                "exp": (
                    payload["exp"].isoformat()
                    if isinstance(payload["exp"], datetime.datetime)
                    else payload["exp"]
                ),
                "ttl": ttl,
            }

            self.table.put_item(Item=session_item)
        except Exception as e:
            self.logger.error(f"Session save error: {str(e)}")
            raise AuthenticationError("セッションの保存に失敗しました")

    def _verify_session(self, user: BaseUser, token: str) -> bool:
        """セッション情報を DynamoDB で検証"""
        try:
            session_id = self._generate_session_id(user)
            response = self.table.get_item(Key={"id": session_id})
            if "Item" in response:
                # 保存されているトークンと一致するかも確認
                stored_token = response["Item"].get("token")
                return bool(stored_token == token)
            return False
        except Exception as e:
            self.logger.error(f"Session verification error: {str(e)}")
            return False

    def _delete_session(self, user: BaseUser) -> None:
        """セッション情報を DynamoDB から削除"""
        try:
            session_id = self._generate_session_id(user)
            self.table.delete_item(Key={"id": session_id})
        except Exception as e:
            self.logger.error(f"Session deletion error: {str(e)}")

    def _get_user_by_id(self, user_id: str) -> Optional[BaseUser]:
        """ユーザー ID でユーザーを取得"""
        try:
            response = self.table.get_item(Key={"id": user_id})
            if "Item" in response:
                item = response["Item"]
                # セッションアイテムかチェック（exp と ttl のみ含む場合はセッション）
                if set(item.keys()) == {"id", "exp", "ttl"}:
                    return None

                # ユーザーオブジェクトを再構築
                user = self.user_model.__new__(self.user_model)
                for key, value in item.items():
                    if key == "created_at" or key == "updated_at":
                        try:
                            setattr(user, key, datetime.datetime.fromisoformat(value))
                        except (ValueError, TypeError):
                            setattr(user, key, value)
                    else:
                        setattr(user, key, value)
                return user
        except Exception as e:
            self.logger.error(f"User retrieval error: {str(e)}")
        return None

    def _get_user_by_email(self, email: str) -> Optional[BaseUser]:
        """メールアドレスでユーザーを取得（GSI 使用）"""
        if not self.user_model._is_email_login_enabled():
            return None

        try:
            response = self.table.query(
                IndexName="email-index",
                KeyConditionExpression=boto3.dynamodb.conditions.Key("email").eq(email),
            )
            if response["Items"]:
                item = response["Items"][0]
                # ユーザーオブジェクトを再構築
                user = self.user_model.__new__(self.user_model)
                for key, value in item.items():
                    if key == "created_at" or key == "updated_at":
                        try:
                            setattr(user, key, datetime.datetime.fromisoformat(value))
                        except (ValueError, TypeError):
                            setattr(user, key, value)
                    else:
                        setattr(user, key, value)
                return user
        except Exception as e:
            self.logger.error(f"User retrieval by email error: {str(e)}")
        return None

    def _save_user(self, user: BaseUser) -> None:
        """ユーザーを DynamoDB に保存"""
        try:
            user_dict = user.to_dict(include_password=True)
            self.table.put_item(Item=user_dict)
        except Exception as e:
            self.logger.error(f"User save error: {str(e)}")
            raise ConflictError("ユーザーの保存に失敗しました")

    def _delete_user(self, user_id: str) -> None:
        """ユーザーを DynamoDB から削除"""
        try:
            self.table.delete_item(Key={"id": user_id})
        except Exception as e:
            self.logger.error(f"User deletion error: {str(e)}")
            raise NotFoundError("ユーザーの削除に失敗しました")

    def signup(self, request: Request) -> Dict[str, Any]:
        """ユーザー登録"""
        try:
            data = request.json()
        except Exception:
            raise ValidationError("無効な JSON リクエストです")

        # 必須フィールドの検証
        if "id" not in data or "password" not in data:
            raise ValidationError("id と password は必須です")

        # 既存ユーザーチェック
        if self._get_user_by_id(data["id"]):
            raise ConflictError("この ID は既に使用されています")

        # メールログイン有効時のメールチェック
        if self.user_model._is_email_login_enabled():
            if "email" not in data:
                raise ValidationError("email は必須です")
            if self._get_user_by_email(data["email"]):
                raise ConflictError("このメールアドレスは既に使用されています")

        # ロール権限有効時のロールチェック
        if self.user_model._is_role_permission_enabled():
            if "role" not in data:
                data["role"] = "user"  # デフォルトロール

        try:
            # ユーザーオブジェクト作成（位置引数として渡す）
            if self.user_model == BaseUser:
                # BaseUser の場合
                user = self.user_model(data["id"], data["password"])
            else:
                # カスタムユーザーの場合、コンストラクタの順序に従う
                # CustomUser(id, password, name, email, role="user")
                try:
                    user = self.user_model(  # type: ignore
                        data["id"],
                        data["password"],
                        data.get("name", ""),
                        data.get("email", ""),
                        data.get("role", "user"),
                    )
                except Exception:
                    # フォールバック: BaseUser として作成
                    user = self.user_model(data["id"], data["password"])

            self._save_user(user)

            self._log_auth_event("user_signup", user.id)

            return {"message": "ユーザー登録が完了しました", "user_id": user.id}
        except ValueError as e:
            raise ValidationError(str(e))

    def login(self, request: Request) -> Dict[str, Any]:
        """ユーザーログイン"""
        try:
            data = request.json()
        except Exception:
            raise ValidationError("無効な JSON リクエストです")

        # 必須フィールドの検証
        if ("id" not in data and "email" not in data) or "password" not in data:
            raise ValidationError("id/email と password は必須です")

        # ユーザー取得
        user = None
        if "id" in data:
            user = self._get_user_by_id(data["id"])
        elif "email" in data and self.user_model._is_email_login_enabled():
            user = self._get_user_by_email(data["email"])

        if not user or not user.verify_password(data["password"]):
            self._log_auth_event("login_failed", data.get("id", data.get("email")))
            raise AuthenticationError("認証に失敗しました")

        # JWT トークン生成
        token = self._generate_jwt_token(user)
        payload = user.to_token_payload()

        # セッション保存（同じユーザーの場合は自動的に上書きされる）
        self._save_session(user, token, payload)

        self._log_auth_event("login_success", user.id)

        return {"message": "ログインしました", "token": token, "user": user.to_dict()}

    def logout(self, request: Request) -> Dict[str, Any]:
        """ユーザーログアウト"""
        token = self._extract_token(request)
        if not token:
            raise AuthenticationError("認証トークンが見つかりません")

        try:
            payload = self._decode_jwt_token(token)
            # ユーザー情報を再構築してセッション削除
            user = self.user_model.__new__(self.user_model)
            for key, value in payload.items():
                if key not in ["iat", "exp"]:
                    setattr(user, key, value)

            self._delete_session(user)
            self._log_auth_event("logout", payload.get("id"))
        except Exception as e:
            self.logger.error(f"Logout error: {str(e)}")

        return {"message": "ログアウトしました"}

    def delete_user(self, request: Request, user_id: str) -> Dict[str, Any]:
        """ユーザー削除"""
        user = self._get_user_by_id(user_id)
        if not user:
            raise NotFoundError("ユーザーが見つかりません")

        self._delete_user(user_id)
        self._log_auth_event("user_deleted", user_id)

        return {"message": "ユーザーを削除しました"}

    def update_password(self, request: Request, user_id: str) -> Dict[str, Any]:
        """パスワード更新"""
        try:
            data = request.json()
        except Exception:
            raise ValidationError("無効な JSON リクエストです")

        if "new_password" not in data:
            raise ValidationError("new_password は必須です")

        user = self._get_user_by_id(user_id)
        if not user:
            raise NotFoundError("ユーザーが見つかりません")

        # 現在のパスワード確認（オプション）
        if "current_password" in data:
            if not user.verify_password(data["current_password"]):
                raise AuthenticationError("現在のパスワードが正しくありません")

        try:
            user.update_attributes(password=data["new_password"])
            self._save_user(user)

            self._log_auth_event("password_updated", user_id)

            return {"message": "パスワードを更新しました"}
        except ValueError as e:
            raise ValidationError(str(e))

    def _extract_token(self, request: Request) -> Optional[str]:
        """リクエストからトークンを抽出"""
        auth_header = request.headers.get("Authorization") or request.headers.get("authorization")
        if not auth_header:
            return None

        if not auth_header.startswith("Bearer "):
            return None

        return auth_header[7:]

    def get_authenticated_user(self, request: Request) -> BaseUser:
        """認証済みユーザーを取得"""
        token = self._extract_token(request)
        if not token:
            raise AuthenticationError("認証トークンが見つかりません")

        # JWT トークンの検証
        payload = self._decode_jwt_token(token)

        # ユーザーオブジェクトを再構築
        user = self.user_model.__new__(self.user_model)
        # 必要な属性を直接設定
        for key, value in payload.items():
            if key not in ["iat", "exp"]:
                setattr(user, key, value)

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
                if self.user_model._is_role_permission_enabled():
                    user_role = getattr(user, "role", None)
                    if user_role not in required_roles:
                        raise AuthorizationError(f"必要なロール: {', '.join(required_roles)}")

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
