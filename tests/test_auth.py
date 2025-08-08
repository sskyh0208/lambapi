"""
DynamoDB 認証機能のテスト

DynamoDBAuth クラスと関連機能のテストケース
"""

import pytest
import json
import time
from unittest.mock import Mock, patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lambapi import (
    API,
    DynamoDBAuth,
    BaseUser,
    AuthenticationError,
    ValidationError,
    AuthorizationError,
)
from lambapi.request import Request
from lambapi.response import Response


class TestBaseUser:
    """BaseUser のテスト"""

    def test_initialization(self):
        """BaseUser 初期化のテスト"""
        data = {"user_id": "test123", "email": "test@example.com", "name": "Test User"}
        user = BaseUser(data)

        assert user.user_id == "test123"
        assert user.email == "test@example.com"
        assert user.name == "Test User"

    def test_user_id_property(self):
        """user_id プロパティのテスト"""
        # user_id フィールドがある場合
        data1 = {"user_id": "test123", "id": "test456"}
        user1 = BaseUser(data1)
        assert user1.user_id == "test123"

        # id フィールドのみの場合
        data2 = {"id": "test456"}
        user2 = BaseUser(data2)
        assert user2.user_id == "test456"

        # どちらもない場合（バリデーションエラー）
        data3 = {"name": "Test"}
        with pytest.raises(ValidationError):
            BaseUser(data3)

    def test_to_dict(self):
        """to_dict メソッドのテスト"""
        data = {"user_id": "test123", "email": "test@example.com"}
        user = BaseUser(data)

        result = user.to_dict()
        assert result == data
        assert result is not data  # コピーされていることを確認

    def test_repr(self):
        """__repr__ メソッドのテスト"""
        data = {"user_id": "test123"}
        user = BaseUser(data)

        assert "BaseUser(user_id=test123)" in repr(user)

    def test_validation_success(self):
        """バリデーション成功のテスト"""
        # user_id がある場合
        data1 = {"user_id": "test123"}
        user1 = BaseUser(data1)
        assert user1.user_id == "test123"

        # id がある場合
        data2 = {"id": "test456"}
        user2 = BaseUser(data2)
        assert user2.user_id == "test456"

    def test_validation_failure_no_id(self):
        """バリデーション失敗のテスト（ID なし）"""
        data = {"name": "Test User"}

        with pytest.raises(ValidationError, match="One of \\['user_id', 'id'\\] is required"):
            BaseUser(data)

    def test_validation_failure_empty_id(self):
        """バリデーション失敗のテスト（空の ID）"""
        data = {"user_id": "", "id": None}

        with pytest.raises(ValidationError, match="One of \\['user_id', 'id'\\] is required"):
            BaseUser(data)

    def test_validation_disabled(self):
        """バリデーション無効のテスト"""
        data = {"name": "Test User"}  # ID なし

        # validate=False の場合はエラーにならない
        user = BaseUser(data, validate=False)
        assert user.name == "Test User"
        assert user.user_id == ""  # プロパティはデフォルト値を返す

    def test_email_validation_success(self):
        """email バリデーション成功のテスト"""
        data = {"user_id": "test123", "email": "test@example.com"}

        # email が必須でない場合
        user1 = BaseUser(data, require_email=False)
        assert user1.email == "test@example.com"

        # email が必須の場合
        user2 = BaseUser(data, require_email=True)
        assert user2.email == "test@example.com"

    def test_email_validation_failure(self):
        """email バリデーション失敗のテスト"""
        data = {"user_id": "test123"}  # email なし

        with pytest.raises(ValidationError, match="email is required"):
            BaseUser(data, require_email=True)

    def test_email_validation_empty_email(self):
        """空の email でのバリデーション失敗テスト"""
        data = {"user_id": "test123", "email": ""}

        with pytest.raises(ValidationError, match="email is required"):
            BaseUser(data, require_email=True)

    def test_custom_validation_in_subclass(self):
        """継承クラスでのカスタムバリデーションテスト"""

        class CustomUser(BaseUser):
            def _validate_data(self):
                super()._validate_data()
                # 追加バリデーション
                if self._data.get("role") == "admin" and not self._data.get("admin_code"):
                    raise ValidationError("admin_code is required for admin users")

        # 通常ユーザーは OK
        user1 = CustomUser({"user_id": "test123", "role": "user"})
        assert user1.role == "user"

        # admin で admin_code がない場合はエラー
        with pytest.raises(ValidationError, match="admin_code is required for admin users"):
            CustomUser({"user_id": "admin123", "role": "admin"})

        # admin で admin_code がある場合は OK
        user3 = CustomUser({"user_id": "admin123", "role": "admin", "admin_code": "secret"})
        assert user3.role == "admin"


class TestTokenManager:
    """TokenManager のテスト"""

    def test_generate_token(self):
        """トークン生成のテスト"""
        from lambapi.auth import TokenManager

        manager = TokenManager("test-secret")
        payload = {"user_id": "test123", "email": "test@example.com"}

        token = manager.generate_token(payload, expires_in=3600)

        assert isinstance(token, str)
        assert len(token.split(".")) == 3  # JWT 形式

    def test_verify_valid_token(self):
        """有効なトークン検証のテスト"""
        from lambapi.auth import TokenManager

        manager = TokenManager("test-secret")
        payload = {"user_id": "test123", "email": "test@example.com"}

        token = manager.generate_token(payload, expires_in=3600)
        verified_payload = manager.verify_token(token)

        assert verified_payload["user_id"] == "test123"
        assert verified_payload["email"] == "test@example.com"
        assert "iat" in verified_payload
        assert "exp" in verified_payload

    def test_verify_invalid_token(self):
        """無効なトークン検証のテスト"""
        from lambapi.auth import TokenManager

        manager = TokenManager("test-secret")

        with pytest.raises(AuthenticationError):
            manager.verify_token("invalid.token.format")

    def test_verify_expired_token(self):
        """期限切れトークン検証のテスト"""
        from lambapi.auth import TokenManager

        manager = TokenManager("test-secret")
        payload = {"user_id": "test123"}

        # 過去の時刻で期限切れトークンを作成
        with patch("time.time", return_value=1000):
            token = manager.generate_token(payload, expires_in=1)

        # 現在時刻で検証（期限切れ）
        with pytest.raises(AuthenticationError, match="Token has expired"):
            manager.verify_token(token)


class TestDynamoDBAuth:
    """DynamoDBAuth のテスト"""

    @pytest.fixture
    def mock_dynamodb(self):
        """DynamoDB のモック"""
        with patch("lambapi.auth.boto3") as mock_boto3:
            mock_resource = Mock()
            mock_table = Mock()
            mock_boto3.resource.return_value = mock_resource
            mock_resource.Table.return_value = mock_table
            yield mock_table

    @pytest.fixture
    def auth_instance(self, mock_dynamodb):
        """DynamoDBAuth インスタンス"""
        with patch("lambapi.auth.bcrypt"):
            return DynamoDBAuth("test-table")

    def test_initialization(self):
        """初期化のテスト"""
        with patch("lambapi.auth.boto3"), patch("lambapi.auth.bcrypt"):
            auth = DynamoDBAuth(
                table_name="users", id_field="user_id", use_email=True, region_name="us-west-2"
            )

            assert auth.table_name == "users"
            assert auth.id_field == "user_id"
            assert auth.use_email is True
            assert auth.region_name == "us-west-2"
            assert auth.user_model == BaseUser

    def test_initialization_with_custom_user_model(self):
        """カスタムユーザーモデルでの初期化テスト"""

        class CustomUser(BaseUser):
            pass

        with patch("lambapi.auth.boto3"), patch("lambapi.auth.bcrypt"):
            auth = DynamoDBAuth("users", user_model=CustomUser)

            assert auth.user_model == CustomUser

    def test_initialization_without_dependencies(self):
        """依存関係なしでの初期化エラーテスト"""
        with patch("lambapi.auth.boto3", None):
            with pytest.raises(ImportError, match="boto3 is required"):
                DynamoDBAuth("test-table")

    def test_hash_password(self, auth_instance):
        """パスワードハッシュ化のテスト"""
        with patch("lambapi.auth.bcrypt") as mock_bcrypt:
            mock_bcrypt.gensalt.return_value = b"salt"
            mock_bcrypt.hashpw.return_value = b"hashed_password"

            result = auth_instance._hash_password("plaintext")

            assert result == "hashed_password"
            mock_bcrypt.hashpw.assert_called_once()

    def test_verify_password(self, auth_instance):
        """パスワード検証のテスト"""
        with patch("lambapi.auth.bcrypt") as mock_bcrypt:
            mock_bcrypt.checkpw.return_value = True

            result = auth_instance._verify_password("plaintext", "hashed")

            assert result is True
            mock_bcrypt.checkpw.assert_called_once()

    def test_sign_up_success(self, auth_instance, mock_dynamodb):
        """ユーザー登録成功のテスト"""
        with patch.object(auth_instance, "_hash_password", return_value="hashed_password"):
            with patch("time.time", return_value=1000):
                user_data = {"id": "test123", "password": "plaintext", "email": "test@example.com"}

                result = auth_instance.sign_up(user_data)

                assert result["message"] == "User created successfully"
                assert result["user"]["id"] == "test123"
                assert "password" not in result["user"]
                mock_dynamodb.put_item.assert_called_once()

    def test_sign_up_missing_fields(self, auth_instance):
        """ユーザー登録の必須フィールド不足テスト"""
        user_data = {"id": "test123"}  # password が不足

        with pytest.raises(ValidationError, match="password is required"):
            auth_instance.sign_up(user_data)

    def test_sign_up_duplicate_user(self, auth_instance, mock_dynamodb):
        """重複ユーザー登録のテスト"""

        # ConditionalCheckFailedException をモック
        class MockException(Exception):
            pass

        auth_instance.dynamodb.meta.client.exceptions.ConditionalCheckFailedException = (
            MockException
        )
        mock_dynamodb.put_item.side_effect = MockException("ConditionalCheckFailedException")

        user_data = {"id": "test123", "password": "plaintext"}

        with patch.object(auth_instance, "_hash_password", return_value="hashed"):
            with pytest.raises(ValidationError, match="already exists"):
                auth_instance.sign_up(user_data)

    def test_login_success(self, auth_instance, mock_dynamodb):
        """ログイン成功のテスト"""
        mock_user = {"id": "test123", "password": "hashed_password", "email": "test@example.com"}
        mock_dynamodb.get_item.return_value = {"Item": mock_user}

        with patch.object(auth_instance, "_verify_password", return_value=True):
            with patch.object(
                auth_instance.token_manager, "generate_token", return_value="test_token"
            ):
                result = auth_instance.login("test123", "plaintext")

                assert result["token"] == "test_token"
                assert result["user"]["id"] == "test123"
                assert "password" not in result["user"]
                assert result["expires_in"] == 3600

    def test_login_invalid_user(self, auth_instance, mock_dynamodb):
        """存在しないユーザーのログインテスト"""
        mock_dynamodb.get_item.return_value = {}  # ユーザーが存在しない

        with pytest.raises(AuthenticationError, match="Invalid credentials"):
            auth_instance.login("nonexistent", "password")

    def test_login_invalid_password(self, auth_instance, mock_dynamodb):
        """無効なパスワードでのログインテスト"""
        mock_user = {"id": "test123", "password": "hashed_password"}
        mock_dynamodb.get_item.return_value = {"Item": mock_user}

        with patch.object(auth_instance, "_verify_password", return_value=False):
            with pytest.raises(AuthenticationError, match="Invalid credentials"):
                auth_instance.login("test123", "wrong_password")

    def test_logout_success(self, auth_instance):
        """ログアウト成功のテスト"""
        with patch.object(
            auth_instance.token_manager, "verify_token", return_value={"user_id": "test123"}
        ):
            result = auth_instance.logout("valid_token")

            assert result["message"] == "Logged out successfully"
            assert "valid_token" in auth_instance.revoked_tokens

    def test_logout_invalid_token(self, auth_instance):
        """無効なトークンでのログアウトテスト"""
        with patch.object(
            auth_instance.token_manager,
            "verify_token",
            side_effect=AuthenticationError("Invalid token"),
        ):
            with pytest.raises(AuthenticationError, match="Invalid token"):
                auth_instance.logout("invalid_token")

    def test_verify_token_success(self, auth_instance):
        """トークン検証成功のテスト"""
        expected_payload = {"user_id": "test123", "email": "test@example.com"}

        with patch.object(
            auth_instance.token_manager, "verify_token", return_value=expected_payload
        ):
            result = auth_instance.verify_token("valid_token")

            assert result == expected_payload

    def test_verify_revoked_token(self, auth_instance):
        """無効化されたトークンの検証テスト"""
        auth_instance.revoked_tokens.add("revoked_token")

        with pytest.raises(AuthenticationError, match="Token has been revoked"):
            auth_instance.verify_token("revoked_token")

    def test_require_auth_decorator_success_legacy_style(self, auth_instance):
        """認証デコレータ成功のテスト（従来スタイル）"""
        mock_request = Mock(spec=Request)
        mock_request.headers = {"Authorization": "Bearer valid_token"}

        @auth_instance.require_auth
        def protected_func(request):
            return {"message": "success", "user": request.user}

        with patch.object(auth_instance, "verify_token", return_value={"user_id": "test123"}):
            result = protected_func(mock_request)

            assert result["message"] == "success"
            assert mock_request.user["user_id"] == "test123"

    def test_require_auth_decorator_success_new_style(self, auth_instance):
        """認証デコレータ成功のテスト（新スタイル: user 引数）"""
        mock_request = Mock(spec=Request)
        mock_request.headers = {"Authorization": "Bearer valid_token"}

        @auth_instance.require_auth
        def protected_func(request, user):
            return {"message": "success", "user_id": user.user_id}

        with patch.object(auth_instance, "verify_token", return_value={"user_id": "test123"}):
            result = protected_func(mock_request)

            assert result["message"] == "success"
            assert result["user_id"] == "test123"

    def test_require_auth_decorator_with_custom_user_model(self):
        """カスタムユーザーモデルでの認証デコレータテスト"""

        class CustomUser(BaseUser):
            def __init__(self, data, **kwargs):
                super().__init__(data, **kwargs)

            @property
            def display_name(self):
                return (
                    f"{self._data.get('first_name', '')} {self._data.get('last_name', '')}".strip()
                )

        with patch("lambapi.auth.boto3"), patch("lambapi.auth.bcrypt"):
            auth = DynamoDBAuth("test-table", user_model=CustomUser)

        mock_request = Mock(spec=Request)
        mock_request.headers = {"Authorization": "Bearer valid_token"}

        @auth.require_auth
        def protected_func(request, user: CustomUser):
            return {"display_name": user.display_name, "user_id": user.user_id}

        with patch.object(
            auth,
            "verify_token",
            return_value={"user_id": "test123", "first_name": "John", "last_name": "Doe"},
        ):
            result = protected_func(mock_request)

            assert result["user_id"] == "test123"
            assert result["display_name"] == "John Doe"

    def test_create_user_instance_validation_success(self):
        """_create_user_instance のバリデーション成功テスト"""
        with patch("lambapi.auth.boto3"), patch("lambapi.auth.bcrypt"):
            auth = DynamoDBAuth("test-table", use_email=True)

        # 有効なデータでユーザーインスタンス作成
        data = {"user_id": "test123", "email": "test@example.com"}
        user = auth._create_user_instance(data)

        assert user.user_id == "test123"
        assert user.email == "test@example.com"

    def test_create_user_instance_validation_failure(self):
        """_create_user_instance のバリデーション失敗テスト"""
        with patch("lambapi.auth.boto3"), patch("lambapi.auth.bcrypt"):
            auth = DynamoDBAuth("test-table", use_email=True)

        # email が必須だが存在しないデータ
        data = {"user_id": "test123"}

        with pytest.raises(AuthenticationError, match="Invalid user data: email is required"):
            auth._create_user_instance(data)

    def test_create_user_instance_with_custom_model(self):
        """カスタムユーザーモデルでの _create_user_instance テスト"""

        class CustomUser(BaseUser):
            def __init__(self, data, **kwargs):
                super().__init__(data, **kwargs)
                self.full_name = f"{data.get('first_name', '')} {data.get('last_name', '')}".strip()

        with patch("lambapi.auth.boto3"), patch("lambapi.auth.bcrypt"):
            auth = DynamoDBAuth("test-table", user_model=CustomUser, use_email=True)

        # 有効なデータでカスタムユーザーインスタンス作成
        data = {
            "user_id": "test123",
            "email": "test@example.com",
            "first_name": "John",
            "last_name": "Doe",
        }
        user = auth._create_user_instance(data)

        assert isinstance(user, CustomUser)
        assert user.user_id == "test123"
        assert user.full_name == "John Doe"

    def test_create_user_instance_custom_model_validation_failure(self):
        """カスタムユーザーモデルでのバリデーション失敗テスト"""

        class StrictCustomUser(BaseUser):
            def __init__(self, data, **kwargs):
                super().__init__(data, **kwargs)

            def _validate_data(self):
                super()._validate_data()
                if self._data.get("role") == "admin" and not self._data.get("admin_key"):
                    raise ValidationError("admin_key is required for admin users")

        with patch("lambapi.auth.boto3"), patch("lambapi.auth.bcrypt"):
            auth = DynamoDBAuth("test-table", user_model=StrictCustomUser)

        # admin だが admin_key がないデータ
        data = {"user_id": "admin123", "role": "admin"}

        with pytest.raises(
            AuthenticationError, match="Invalid user data: admin_key is required for admin users"
        ):
            auth._create_user_instance(data)

    def test_require_auth_decorator_missing_header(self, auth_instance):
        """認証デコレータ：ヘッダー不足テスト"""
        mock_request = Mock(spec=Request)
        mock_request.headers = {}

        @auth_instance.require_auth
        def protected_func(request):
            return {"message": "success"}

        with pytest.raises(AuthenticationError, match="Authorization header missing"):
            protected_func(mock_request)

    def test_require_auth_decorator_invalid_format(self, auth_instance):
        """認証デコレータ：無効な形式テスト"""
        mock_request = Mock(spec=Request)
        mock_request.headers = {"Authorization": "Invalid format"}

        @auth_instance.require_auth
        def protected_func(request):
            return {"message": "success"}

        with pytest.raises(AuthenticationError, match="Invalid authorization header format"):
            protected_func(mock_request)

    def test_get_auth_routes(self, auth_instance):
        """認証ルート取得のテスト"""
        routes = auth_instance.get_auth_routes()

        assert len(routes) == 3

        paths = [route.path for route in routes]
        methods = [route.method for route in routes]

        assert "/auth/signup" in paths
        assert "/auth/login" in paths
        assert "/auth/logout" in paths
        assert all(method == "POST" for method in methods)


class TestAPIIntegration:
    """API との統合テスト"""

    @pytest.fixture
    def mock_event(self):
        """テスト用 Lambda イベント"""
        return {
            "httpMethod": "GET",
            "path": "/test",
            "queryStringParameters": {},
            "headers": {"Content-Type": "application/json"},
            "body": None,
        }

    def test_include_auth(self, mock_event):
        """include_auth メソッドのテスト"""
        app = API(mock_event, None)

        with patch("lambapi.auth.boto3"), patch("lambapi.auth.bcrypt"):
            auth = DynamoDBAuth("test-table")

            # 認証システムを追加
            app.include_auth(auth)

            # 認証ルートが追加されているか確認
            paths = [route.path for route in app.routes]
            assert "/auth/signup" in paths
            assert "/auth/login" in paths
            assert "/auth/logout" in paths

    def test_protected_endpoint_integration(self, mock_event):
        """保護されたエンドポイントの統合テスト"""
        # 認証なしでのアクセス用イベント
        protected_event = {**mock_event, "path": "/protected", "headers": {}}

        app = API(protected_event, None)

        with patch("lambapi.auth.boto3"), patch("lambapi.auth.bcrypt"):
            auth = DynamoDBAuth("test-table")
            app.include_auth(auth)

            @app.get("/protected")
            @auth.require_auth
            def protected_endpoint(request):
                return {"message": "protected", "user_id": request.user["user_id"]}

            # 認証ヘッダーなしでのアクセス
            response = app.handle_request()
            assert response["statusCode"] == 401

    def test_auth_routes_functionality(self, mock_event):
        """認証ルートの機能テスト"""
        with patch("lambapi.auth.boto3"), patch("lambapi.auth.bcrypt"):
            auth = DynamoDBAuth("test-table")

            # signup ルートのテスト
            signup_event = {
                **mock_event,
                "httpMethod": "POST",
                "path": "/auth/signup",
                "body": json.dumps(
                    {"id": "test123", "password": "password123", "email": "test@example.com"}
                ),
            }

            app = API(signup_event, None)
            app.include_auth(auth)

            with patch.object(auth, "sign_up", return_value={"message": "User created"}):
                response = app.handle_request()
                assert response["statusCode"] == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
