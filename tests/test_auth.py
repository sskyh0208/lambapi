"""
DynamoDBAuth統合テスト

新しいPynamoDB対応DynamoDBAuthの統合テスト
"""

import pytest
import json
import os
from unittest.mock import patch

from moto import mock_aws
from pynamodb.models import Model
from pynamodb.attributes import (
    UnicodeAttribute,
    BooleanAttribute,
    UTCDateTimeAttribute,
    NumberAttribute,
)
from lambapi.exceptions import (
    AuthConfigError,
    ModelValidationError,
    PasswordValidationError,
    FeatureDisabledError,
    AuthenticationError,
    ConflictError,
    ValidationError,
)
from pynamodb.indexes import GlobalSecondaryIndex, AllProjection

from lambapi import API, Authenticated, create_lambda_handler
from lambapi.auth.dynamodb_auth import DynamoDBAuth


class EmailIndex(GlobalSecondaryIndex):
    """メールアドレスでの検索用GSI"""

    class Meta:
        index_name = "email-index"
        projection = AllProjection()
        read_capacity_units = 1
        write_capacity_units = 1

    email = UnicodeAttribute(hash_key=True)


class TestUser(Model):
    """テスト用ユーザーモデル"""

    class Meta:
        table_name = "test-users"
        region = "us-east-1"

    id = UnicodeAttribute(hash_key=True)
    password = UnicodeAttribute()
    email = UnicodeAttribute()
    email_index = EmailIndex()
    name = UnicodeAttribute()
    role = UnicodeAttribute(default="user")
    is_active = BooleanAttribute(default=True)


class TestUserSession(Model):
    """テスト用ユーザーセッションモデル"""

    class Meta:
        table_name = "test-user-sessions"
        region = "us-east-1"

    id = UnicodeAttribute(hash_key=True)
    user_id = UnicodeAttribute()
    token = UnicodeAttribute()
    expires_at = NumberAttribute()
    from datetime import datetime

    created_at = UTCDateTimeAttribute(default=datetime.now)


class MockDynamoDBAuth(DynamoDBAuth):
    """テスト用のモックDynamoDBAuth"""

    def __init__(self, **kwargs):
        # テスト用のデフォルト設定
        defaults = {
            "user_model": TestUser,
            "session_model": TestUserSession,
            "secret_key": "test_secret_key_for_testing",
            "expiration": 3600,
            "is_email_login": True,
            "is_role_permission": True,
            "token_include_fields": ["id", "email", "name", "role"],
            "password_min_length": 8,
            "password_require_digit": False,
        }
        defaults.update(kwargs)
        super().__init__(**defaults)
        self._init_save_mock_user()

    def _init_save_mock_user(self):
        """テスト用のユーザー保存（モック）"""
        if not TestUser.exists():
            TestUser.create_table(wait=True)
        if not TestUserSession.exists():
            TestUserSession.create_table(wait=True)

        user = TestUser(
            id="testuser",
            password=self._hash_password("Password123"),
            email="test@example.com",
            name="Test User",
            role="user",
        )
        user.save()

        admin = TestUser(
            id="admin",
            password=self._hash_password("AdminPass123"),
            email="admin@example.com",
            name="Admin User",
            role="admin",
        )
        admin.save()

    def get_user_by_id(self, user_id):
        """テスト用のユーザー取得（モック）"""
        if user_id == "testuser":
            return TestUser.get("testuser", consistent_read=True)
        elif user_id == "admin":
            return TestUser.get("admin", consistent_read=True)
        return None


class TestDynamoDBAuthConstructor:
    """DynamoDBAuthコンストラクタのテスト"""

    def test_basic_constructor(self):
        """基本的なコンストラクタのテスト"""
        auth = DynamoDBAuth(
            user_model=TestUser,
            session_model=TestUserSession,
            secret_key="test_secret",
        )

        assert auth.user_model == TestUser
        assert auth.secret_key == "test_secret"
        assert auth.expiration == 3600
        assert auth.is_email_login is False
        assert auth.password_min_length == 8

    def test_constructor_with_all_params(self):
        """全パラメータ指定のテスト"""
        auth = DynamoDBAuth(
            user_model=TestUser,
            session_model=TestUserSession,
            secret_key="test_secret",
            expiration=7200,
            is_email_login=True,
            is_role_permission=True,
            token_include_fields=["id", "name"],
            password_min_length=10,
            password_require_uppercase=True,
        )

        assert auth.expiration == 7200
        assert auth.is_email_login is True
        assert auth.token_include_fields == ["id", "name"]
        assert auth.password_min_length == 10
        assert auth.password_require_uppercase is True

    def test_constructor_validation_errors(self):
        """コンストラクタのバリデーションエラー"""
        # 無効なuser_model
        with pytest.raises(AuthConfigError, match="must be a PynamoDB Model"):
            DynamoDBAuth(user_model=str, session_model=TestUserSession, secret_key="test")

        # email_login=True but no email index
        class NoIndexUser(Model):
            class Meta:
                table_name = "no-index"

            id = UnicodeAttribute(hash_key=True)

        with pytest.raises(AuthConfigError, match="requires a GlobalSecondaryIndex"):
            DynamoDBAuth(
                user_model=NoIndexUser,
                session_model=TestUserSession,
                secret_key="test",
                is_email_login=True,
            )

        # 無効なtoken_include_fields
        with pytest.raises(
            ModelValidationError, match="password フィールドはトークンに含めることができません"
        ):
            DynamoDBAuth(
                user_model=TestUser,
                session_model=TestUserSession,
                secret_key="test",
                token_include_fields=["id", "password"],
            )


class TestPasswordValidation:
    """パスワードバリデーションのテスト"""

    def test_password_validation_basic(self):
        """基本的なパスワードバリデーション"""
        auth = DynamoDBAuth(user_model=TestUser, session_model=TestUserSession, secret_key="test")

        # 正常なパスワード
        auth.validate_password("password123")

        # 短すぎるパスワード
        with pytest.raises(PasswordValidationError, match="8文字以上"):
            auth.validate_password("short")

    def test_password_requirements(self):
        """パスワード要件のテスト"""
        auth = DynamoDBAuth(
            user_model=TestUser,
            session_model=TestUserSession,
            secret_key="test",
            password_require_uppercase=True,
            password_require_lowercase=True,
            password_require_digit=True,
            password_require_special=True,
        )

        # 全要件を満たすパスワード
        auth.validate_password("Password123!")

        # 大文字不足
        with pytest.raises(PasswordValidationError, match="大文字を含める"):
            auth.validate_password("password123!")

        # 小文字不足
        with pytest.raises(PasswordValidationError, match="小文字を含める"):
            auth.validate_password("PASSWORD123!")

        # 数字不足
        with pytest.raises(PasswordValidationError, match="数字を含める"):
            auth.validate_password("Password!")

        # 特殊文字不足
        with pytest.raises(PasswordValidationError, match="特殊文字を含める"):
            auth.validate_password("Password123")


@mock_aws
class TestUserOperations:
    """ユーザー操作のテスト"""

    def setup_method(self, method):
        """テストセットアップ（ユーザーテーブルを毎回初期化）"""
        os.environ["AWS_ACCESS_KEY_ID"] = "testing"
        os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
        os.environ["AWS_SECURITY_TOKEN"] = "testing"
        os.environ["AWS_SESSION_TOKEN"] = "testing"
        self.auth = MockDynamoDBAuth()

    def test_signup_success(self):
        """ユーザー登録成功のテスト"""
        user = TestUser(
            id="newuser", password="Password123", email="new@example.com", name="New User"
        )
        token = self.auth.signup(user)
        assert isinstance(token, str)
        assert len(token) > 0

    def test_signup_conflict(self):
        """既存ユーザーでの登録エラー"""
        # 先に登録
        user = TestUser(
            id="existing",
            password="Password123",
            email="existing@example.com",
            name="Existing User",
        )
        self.auth.signup(user)
        # 同じIDで再登録
        with pytest.raises(ConflictError, match="ユーザーIDは既に存在します"):
            self.auth.signup(user)

    def test_signup_email_validation_disabled(self):
        """email_loginが無効時はemailバリデーションなし"""
        # email_login=Falseの認証インスタンスを明示的に作成
        auth_without_email = MockDynamoDBAuth(is_email_login=False)

        # email_login=Falseの場合でも、PynamoDBモデルの制約上emailは必須
        # しかし、バリデーション処理では空文字やダミー値を受け入れる
        user = TestUser(
            id="nomail", password="Password123", email="dummy@example.com", name="No Mail User"
        )
        token = auth_without_email.signup(user)
        assert isinstance(token, str)

    def test_signup_email_validation_enabled_success(self):
        """email_login有効時の正常なemailでの登録"""
        # email_login=Trueの認証インスタンスを作成
        auth_with_email = MockDynamoDBAuth(is_email_login=True)

        user = TestUser(
            id="mailuser", password="Password123", email="valid@example.com", name="Mail User"
        )
        token = auth_with_email.signup(user)
        assert isinstance(token, str)

    def test_signup_email_validation_enabled_missing_email(self):
        """email_login有効時にemailが欠如している場合のエラー"""
        auth_with_email = MockDynamoDBAuth(is_email_login=True)

        user = TestUser(id="nomailuser", password="Password123", name="No Mail User")
        with pytest.raises(ValidationError, match="email は必須です"):
            auth_with_email.signup(user)

    def test_signup_email_validation_enabled_empty_email(self):
        """email_login有効時にemailが空の場合のエラー"""
        auth_with_email = MockDynamoDBAuth(is_email_login=True)

        user = TestUser(
            id="emptymailuser", password="Password123", email="", name="Empty Mail User"
        )
        with pytest.raises(ValidationError, match="email は必須です"):
            auth_with_email.signup(user)

    def test_signup_invalid_email_format(self):
        """無効なメール形式でのエラー"""
        auth_with_email = MockDynamoDBAuth(is_email_login=True)

        invalid_emails = [
            "invalid-email",
            "@example.com",
            "user@",
            "user..name@example.com",
            "user@.com",
            "user@example",
            "user name@example.com",
        ]

        for i, invalid_email in enumerate(invalid_emails):
            user = TestUser(
                id=f"user_{i}",  # IDを単純化
                password="Password123",
                email=invalid_email,
                name="Test User",
            )
            with pytest.raises(ValidationError, match="有効なメールアドレスを入力してください"):
                auth_with_email.signup(user)

    def test_signup_email_too_long(self):
        """メールアドレスが長すぎる場合のエラー"""
        auth_with_email = MockDynamoDBAuth(is_email_login=True)

        # 254文字を超えるメールアドレス
        long_email = "a" * 250 + "@example.com"
        user = TestUser(
            id="longemailuser", password="Password123", email=long_email, name="Long Email User"
        )
        with pytest.raises(
            ValidationError, match="メールアドレスは254文字以内である必要があります"
        ):
            auth_with_email.signup(user)

    def test_signup_email_local_part_too_long(self):
        """メールアドレスのローカル部が長すぎる場合のエラー"""
        auth_with_email = MockDynamoDBAuth(is_email_login=True)

        # ローカル部が64文字を超えるメールアドレス
        long_local_email = "a" * 65 + "@example.com"
        user = TestUser(
            id="longlocaluser",
            password="Password123",
            email=long_local_email,
            name="Long Local User",
        )
        with pytest.raises(
            ValidationError, match="メールアドレスのローカル部は64文字以内である必要があります"
        ):
            auth_with_email.signup(user)

    def test_login_success(self):
        """ログイン成功のテスト"""
        token = self.auth.login("testuser", "Password123")

        assert isinstance(token, str)
        assert len(token) > 0

    def test_login_invalid_user(self):
        """存在しないユーザーでのログインエラー"""
        with pytest.raises(AuthenticationError, match="認証に失敗しました"):
            self.auth.login("nonexistent", "password")

    def test_login_invalid_password(self):
        """間違ったパスワードでのログインエラー"""
        with pytest.raises(AuthenticationError, match="認証に失敗しました"):
            self.auth.login("testuser", "wrongpassword")


@mock_aws
class TestEmailLogin:
    """emailログインのテスト"""

    def setup_method(self, method):
        """テストセットアップ"""
        os.environ["AWS_ACCESS_KEY_ID"] = "testing"
        os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
        os.environ["AWS_SECURITY_TOKEN"] = "testing"
        os.environ["AWS_SESSION_TOKEN"] = "testing"
        self.auth = MockDynamoDBAuth()

    @patch.object(EmailIndex, "query")
    def test_email_login_success(self, mock_query):
        """emailログイン成功のテスト"""
        # モックユーザー作成
        user = TestUser()
        user.id = "testuser"
        user.password = self.auth._hash_password("Password123")
        user.email = "test@example.com"

        mock_query.return_value = [user]

        token = self.auth.email_login("test@example.com", "Password123")

        assert isinstance(token, str)
        assert len(token) > 0

    @patch.object(EmailIndex, "query")
    def test_email_login_user_not_found(self, mock_query):
        """存在しないemailでのログインエラー"""
        mock_query.return_value = []

        with pytest.raises(AuthenticationError, match="認証に失敗しました"):
            self.auth.email_login("nonexistent@example.com", "password")

    def test_email_login_disabled(self):
        """emailログインが無効な場合のエラー"""
        auth = DynamoDBAuth(
            user_model=TestUser,
            session_model=TestUserSession,
            secret_key="test",
            is_email_login=False,
        )

        auth = MockDynamoDBAuth(is_email_login=False)
        with pytest.raises(FeatureDisabledError, match="Emailログインは無効化されています"):
            auth.email_login("test@example.com", "password")


@mock_aws
class TestTokenGeneration:
    """トークン生成のテスト"""

    def setup_method(self, method):
        """テストセットアップ"""
        os.environ["AWS_ACCESS_KEY_ID"] = "testing"
        os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
        os.environ["AWS_SECURITY_TOKEN"] = "testing"
        os.environ["AWS_SESSION_TOKEN"] = "testing"
        self.auth = MockDynamoDBAuth()

    def test_token_payload_with_include_fields(self):
        """token_include_fieldsを使ったペイロード生成"""
        user = TestUser()
        user.id = "testuser"
        user.email = "test@example.com"
        user.name = "Test User"
        user.role = "user"

        payload = self.auth._create_token_payload(user)

        # 指定されたフィールドが含まれていることを確認
        assert "id" in payload
        assert "email" in payload
        assert "name" in payload
        assert "role" in payload

        # passwordは含まれていないことを確認
        assert "password" not in payload

        # JWT標準フィールドが含まれていることを確認
        assert "iat" in payload
        assert "exp" in payload


@mock_aws
class TestIntegrationWithAPI:
    """API統合のテスト"""

    def setup_method(self, method):
        """テストセットアップ"""
        os.environ["AWS_ACCESS_KEY_ID"] = "testing"
        os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
        os.environ["AWS_SECURITY_TOKEN"] = "testing"
        os.environ["AWS_SESSION_TOKEN"] = "testing"
        self.auth = MockDynamoDBAuth()
        event = {}
        context = {}
        self.api = API(event, context)
        self.api.auth = self.auth

        # ルート登録は必ずここで
        @self.api.post("/test")
        def test_endpoint(user: Authenticated):
            return {"user_id": user.id}

    def test_authenticated_endpoint(self):
        """認証が必要なエンドポイントのテスト"""
        token = self.auth.login("testuser", "Password123")

        def make_api(event, context):
            api = API(event, context)
            auth = self.auth

            @api.post("/test")
            @auth.require_role("user")
            def test_endpoint(user: Authenticated):
                return {"user_id": user.id}

            return api

        handler = create_lambda_handler(make_api)
        event = {
            "httpMethod": "POST",
            "path": "/test",
            "headers": {"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            "body": "{}",
        }
        response = handler(event, {})
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["user_id"] == "testuser"

    def test_unauthenticated_request(self):
        """認証なしでの認証必須エンドポイントアクセス"""

        def make_api(event, context):
            api = API(event, context)
            auth = self.auth

            @api.post("/test")
            @auth.require_role("user")
            def test_endpoint(user: Authenticated):
                return {"user_id": user.id}

            return api

        handler = create_lambda_handler(make_api)
        event = {
            "httpMethod": "POST",
            "path": "/test",
            "headers": {"Content-Type": "application/json"},
            "body": "{}",
        }
        response = handler(event, {})
        assert response["statusCode"] == 401


@mock_aws
class TestRolePermissions:
    """ロール権限のテスト"""

    def setup_method(self, method):
        """テストセットアップ"""
        os.environ["AWS_ACCESS_KEY_ID"] = "testing"
        os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
        os.environ["AWS_SECURITY_TOKEN"] = "testing"
        os.environ["AWS_SESSION_TOKEN"] = "testing"
        self.auth = MockDynamoDBAuth()
        event = {}
        context = {}
        self.api = API(event, context)
        self.api.auth = self.auth

    def test_role_required_endpoint_success(self):
        """ロール権限が必要なエンドポイント（成功）"""
        token = self.auth.login("admin", "AdminPass123")

        def make_api(event, context):
            api = API(event, context)
            api.auth = self.auth

            @api.post("/admin")
            @self.auth.require_role("admin")
            def admin_endpoint(user: Authenticated):
                return {"message": "admin access"}

            return api

        handler = create_lambda_handler(make_api)
        event = {
            "httpMethod": "POST",
            "path": "/admin",
            "headers": {"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            "body": "{}",
        }
        response = handler(event, {})
        assert response["statusCode"] == 200

    def test_role_required_endpoint_forbidden(self):
        """ロール権限が不足している場合のエラー"""
        token = self.auth.login("testuser", "Password123")

        def make_api(event, context):
            api = API(event, context)
            api.auth = self.auth

            @api.post("/admin")
            @self.auth.require_role("admin")
            def admin_endpoint(user: Authenticated):
                return {"message": "admin access"}

            return api

        handler = create_lambda_handler(make_api)
        event = {
            "httpMethod": "POST",
            "path": "/admin",
            "headers": {"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            "body": "{}",
        }
        response = handler(event, {})
        assert response["statusCode"] == 403


if __name__ == "__main__":
    pytest.main([__file__])
