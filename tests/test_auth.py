"""
認証機能のテスト

DynamoDB 認証機能の基本的なテストを行います。
"""

import pytest
import json
import datetime
from lambapi.auth import BaseUser, DynamoDBAuth
from lambapi import Request
from lambapi.exceptions import ValidationError, AuthenticationError, ConflictError

# boto3 は動的インポート
try:
    import boto3

    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False


class CustomUser(BaseUser):
    """テスト用カスタムユーザー"""

    class Meta(BaseUser.Meta):
        table_name = "test_users"
        expiration = 3600
        is_email_login = True
        is_role_permission = True
        enable_auth_logging = False
        id_type = "custom"
        endpoint_url = "http://localhost:8000"

    def __init__(self, id, password, name, email, role="user"):
        # 先に BaseUser を初期化
        super().__init__(id, password)
        # その後でカスタム属性を設定
        self.email = email
        self.role = role
        self.name = name
        self.is_admin = role == "admin"


class TestBaseUser:
    """BaseUser クラスのテスト"""

    def test_base_user_creation(self):
        """BaseUser の基本的な作成テスト"""
        user = BaseUser("test_user", "Password123!")
        assert user.id == "test_user"
        assert user.password is not None
        assert user.password != "Password123!"  # ハッシュ化されているか  # nosec B105

    def test_password_verification(self):
        """パスワード検証のテスト"""
        user = BaseUser("test_user", "Password123!")
        assert user.verify_password("Password123!") is True
        assert user.verify_password("wrong_password") is False

    def test_custom_user_creation(self):
        """カスタムユーザーの作成テスト"""
        user = CustomUser("custom_user", "Password123!", "Test User", "test@example.com")
        assert user.id == "custom_user"
        assert user.email == "test@example.com"
        assert user.role == "user"
        assert user.name == "Test User"

    def test_to_dict(self):
        """辞書変換のテスト"""
        user = CustomUser("test_user", "Password123!", "Test User", "test@example.com")
        user_dict = user.to_dict()

        assert "id" in user_dict
        assert "email" in user_dict
        assert "password" not in user_dict  # パスワードは除外される

    def test_to_token_payload(self):
        """トークンペイロード作成のテスト"""
        user = CustomUser("test_user", "Password123!", "Test User", "test@example.com")
        payload = user.to_token_payload()

        assert "id" in payload
        assert "email" in payload
        assert "iat" in payload
        assert "exp" in payload
        assert "password" not in payload


@pytest.mark.skipif(not BOTO3_AVAILABLE, reason="boto3 not available")
class TestDynamoDBAuth:
    """DynamoDBAuth クラスのテスト"""

    def test_secret_key_required(self):
        """secret_key が必要であることのテスト"""
        # secret_key を指定しない場合、ValueError が発生することを確認
        with pytest.raises(ValueError, match="Secret key is required"):
            DynamoDBAuth(CustomUser)

    def test_explicit_secret_key(self):
        """明示的 secret_key 指定のテスト"""
        auth = DynamoDBAuth(CustomUser, secret_key="explicit_key")  # nosec B106
        assert auth.secret_key == "explicit_key"  # nosec B105

    def test_environment_variable_secret_key(self):
        """環境変数 secret_key のテスト"""
        import os

        os.environ["LAMBAPI_SECRET_KEY"] = "env_key"  # nosec B105
        try:
            auth = DynamoDBAuth(CustomUser)
            assert auth.secret_key == "env_key"  # nosec B105
        finally:
            # 環境変数をクリア
            os.environ.pop("LAMBAPI_SECRET_KEY", None)

    def setup_method(self):
        """テストセットアップ"""
        # 実際の DynamoDB ローカルを使用（テスト用 secret_key 指定）
        self.auth = DynamoDBAuth(CustomUser, secret_key="test_secret_key")  # nosec B106

        # テスト用テーブルを作成
        self._create_test_table()

        # テーブルをクリア
        self._clear_table()

    def _create_test_table(self):
        """テスト用テーブルを作成"""
        try:
            # テーブルが既に存在するかチェック
            self.auth.table.table_status
        except Exception:
            # テーブルが存在しない場合は作成
            dynamodb = boto3.resource("dynamodb", endpoint_url="http://localhost:8000")
            table = dynamodb.create_table(
                TableName="test_users",
                KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
                AttributeDefinitions=[
                    {"AttributeName": "id", "AttributeType": "S"},
                    {"AttributeName": "email", "AttributeType": "S"},
                ],
                BillingMode="PAY_PER_REQUEST",
                GlobalSecondaryIndexes=[
                    {
                        "IndexName": "email-index",
                        "KeySchema": [{"AttributeName": "email", "KeyType": "HASH"}],
                        "Projection": {"ProjectionType": "ALL"},
                    }
                ],
            )
            # テーブルが利用可能になるまで待機
            table.wait_until_exists()

    def _clear_table(self):
        """テーブルのデータをクリア"""
        try:
            # 全アイテムをスキャンして削除
            response = self.auth.table.scan()
            for item in response.get("Items", []):
                self.auth.table.delete_item(Key={"id": item["id"]})
        except Exception:
            pass  # nosec B110

    def teardown_method(self):
        """テスト後処理"""
        self._clear_table()

    def test_auth_initialization(self):
        """認証システムの初期化テスト"""
        assert self.auth.user_model == CustomUser
        assert self.auth.table_name == "test_users"
        assert self.auth.secret_key == "test_secret_key"  # nosec B105
        assert self.auth.expiration == 3600

    def test_signup_success(self):
        """ユーザー登録成功のテスト"""
        # リクエストモック
        mock_event = {
            "body": json.dumps(
                {
                    "id": "new_user",
                    "password": "Password123!",
                    "email": "new@example.com",
                    "name": "New User",
                    "role": "user",
                }
            )
        }
        request = Request(mock_event)

        result = self.auth.signup(request)

        assert result["message"] == "ユーザー登録が完了しました"
        assert result["user_id"] == "new_user"

        # ユーザーが DynamoDB に実際に保存されたかチェック
        user = self.auth._get_user_by_id("new_user")
        assert user is not None
        assert user.email == "new@example.com"

    def test_signup_duplicate_user(self):
        """重複ユーザー登録のテスト"""
        # 最初にユーザーを作成
        first_event = {
            "body": json.dumps(
                {
                    "id": "existing_user",
                    "password": "Password123!",
                    "email": "existing@example.com",
                    "name": "Existing User",
                    "role": "user",
                }
            )
        }
        request1 = Request(first_event)
        self.auth.signup(request1)

        # 同じ ID で再度登録を試行
        mock_event = {
            "body": json.dumps(
                {
                    "id": "existing_user",
                    "password": "Password123!",
                    "email": "test@example.com",
                    "name": "Test User",
                    "role": "user",
                }
            )
        }
        request2 = Request(mock_event)

        with pytest.raises(ConflictError):
            self.auth.signup(request2)

    def test_login_success(self):
        """ログイン成功のテスト"""
        # まずユーザーを作成
        signup_event = {
            "body": json.dumps(
                {
                    "id": "test_user",
                    "password": "Password123!",
                    "email": "test@example.com",
                    "name": "Test User",
                    "role": "user",
                }
            )
        }
        signup_request = Request(signup_event)
        self.auth.signup(signup_request)

        # ログインをテスト
        login_event = {"body": json.dumps({"id": "test_user", "password": "Password123!"})}
        login_request = Request(login_event)

        result = self.auth.login(login_request)

        assert result["message"] == "ログインしました"
        assert "token" in result
        assert "user" in result
        assert result["user"]["id"] == "test_user"

    def test_login_invalid_credentials(self):
        """ログイン失敗のテスト"""
        mock_event = {"body": json.dumps({"id": "nonexistent_user", "password": "Password123!"})}
        request = Request(mock_event)

        with pytest.raises(AuthenticationError):
            self.auth.login(request)

    def test_logout(self):
        """ログアウトのテスト"""
        # まずユーザーを作成してログイン
        signup_event = {
            "body": json.dumps(
                {
                    "id": "logout_test_user",
                    "password": "Password123!",
                    "email": "logout@example.com",
                    "name": "Logout User",
                    "role": "user",
                }
            )
        }
        signup_request = Request(signup_event)
        self.auth.signup(signup_request)

        # ログイン
        login_event = {"body": json.dumps({"id": "logout_test_user", "password": "Password123!"})}
        login_request = Request(login_event)
        login_result = self.auth.login(login_request)
        token = login_result["token"]

        # ログアウトをテスト
        logout_event = {"headers": {"Authorization": f"Bearer {token}"}}
        logout_request = Request(logout_event)

        result = self.auth.logout(logout_request)

        assert result["message"] == "ログアウトしました"


if __name__ == "__main__":
    # 簡単なテスト実行
    print("認証機能の基本テストを実行中...")

    try:
        # BaseUser のテスト
        print("✓ BaseUser 作成テスト")
        user = BaseUser("test", "Password123!")
        assert user.verify_password("Password123!")
        print("✓ パスワード検証テスト")

        # CustomUser のテスト
        custom_user = CustomUser("custom", "Password123!", "Test User", "test@example.com")
        assert custom_user.email == "test@example.com"
        print("✓ CustomUser 作成テスト")

        user_dict = custom_user.to_dict()
        assert "password" not in user_dict
        print("✓ 辞書変換テスト")

        payload = custom_user.to_token_payload()
        assert "iat" in payload and "exp" in payload
        print("✓ トークンペイロード作成テスト")

        print("\n✅ 基本テストが完了しました！")

    except Exception as e:
        print(f"\n❌ テスト失敗: {e}")
        raise
