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
        is_role_permission = True
        enable_auth_logging = False
        endpoint_url = "http://localhost:8000"

    def __init__(self, id, password, email, name, role="user"):
        self.id = id
        self.password = password
        self.email = email
        self.name = name
        self.role = role
        self.is_admin = role == "admin"


class TestBaseUser:
    """BaseUser クラスのテスト"""

    def test_base_user_creation(self):
        """BaseUser の基本的な作成テスト"""
        user = BaseUser()
        # BaseUser.__init__はpassのみなので属性は手動設定
        user.id = "test_user"
        user.password = "Password123!"
        assert user.id == "test_user"
        assert (
            user.password == "Password123!"
        )  # 生パスワードがそのまま保存される  # 生パスワードがそのまま保存される  # ハッシュ化されているか  # nosec B105

    def test_password_verification(self):
        """パスワード検証のテスト（signup後のハッシュ化パスワードで検証）"""
        # BaseUser.__init__がpassのみになったため、このテストは無効
        # パスワード検証はauth.signupを通してテストする
        pass

    def test_custom_user_creation(self):
        """カスタムユーザーの作成テスト"""
        user = CustomUser("custom_user", "Password123!", "test@example.com", "Test User")
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

    def test_custom_token_fields(self):
        """カスタムトークンフィールドのテスト"""

        # カスタムユーザーでtoken_include_fieldsを指定
        class CustomTokenUser(BaseUser):
            class Meta(BaseUser.Meta):
                token_include_fields = ["id", "name", "role"]

        user = CustomTokenUser()
        user.id = "test_user"
        user.name = "Test User"
        user.email = "test@example.com"
        user.role = "admin"

        payload = user.to_token_payload()

        # 指定されたフィールドのみ含まれる
        assert "id" in payload
        assert "name" in payload
        assert "role" in payload
        assert "email" not in payload  # 指定されていない
        assert "password" not in payload  # 常に除外
        # JWT標準フィールドは含まれる
        assert "iat" in payload
        assert "exp" in payload

    def test_token_fields_validation(self):
        """トークンフィールドバリデーションのテスト"""
        user = BaseUser()
        user.id = "test"
        user.password = "pass"

        # passwordを含めようとするとエラー
        with pytest.raises(
            ValueError, match="password フィールドはトークンに含めることができません"
        ):
            user._validate_token_fields(["id", "password"])

        # 文字列でない要素があるとエラー
        with pytest.raises(
            ValueError, match="token_include_fields の要素は文字列である必要があります"
        ):
            user._validate_token_fields(["id", 123])

        # リスト以外だとエラー
        with pytest.raises(
            ValueError, match="token_include_fields はリスト形式である必要があります"
        ):
            user._validate_token_fields("invalid")

    def test_validate_password_public(self):
        """公開されたvalidate_passwordメソッドのテスト"""
        user = BaseUser()

        # 短すぎるパスワード
        with pytest.raises(ValueError, match="パスワードは8文字以上である必要があります"):
            user.validate_password("short")

        # 有効なパスワード
        user.validate_password("ValidPassword123")  # エラーが発生しないことを確認

    def test_decode_token_payload(self):
        """トークンデコードのテスト"""
        user = BaseUser()
        user.id = "test_user"
        user.name = "Test User"

        # テスト用の秘密鍵
        secret_key = "test_secret_key"

        # 現在時刻を使用してトークン生成
        import jwt

        now = datetime.datetime.now()
        payload = {
            "id": "test_user",
            "name": "Test User",
            "iat": int(now.timestamp()),
            "exp": int((now + datetime.timedelta(hours=1)).timestamp()),
        }
        token = jwt.encode(payload, secret_key, algorithm="HS256")

        # デコード
        decoded = BaseUser.decode_token_payload(token, secret_key)

        assert decoded["id"] == "test_user"
        assert decoded["name"] == "Test User"
        assert "iat" in decoded
        assert "exp" in decoded


def _dynamodb_available():
    """DynamoDB ローカルが利用可能かチェック"""
    try:
        import boto3

        dynamodb = boto3.resource("dynamodb", endpoint_url="http://localhost:8000")
        # 簡単な接続テスト
        dynamodb.meta.client.list_tables()
        return True
    except Exception:
        return False


@pytest.mark.skipif(not BOTO3_AVAILABLE, reason="boto3 not available")
@pytest.mark.skipif(not _dynamodb_available(), reason="DynamoDB not available")
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
        # BaseUserオブジェクトを作成（生パスワードを渡す）
        user = CustomUser(
            id="new_user",
            password="Password123!",  # 生パスワード
            email="new@example.com",
            name="New User",
            role="user",
        )

        result = self.auth.signup(user)

        # BaseUserオブジェクトが返される
        assert isinstance(result, BaseUser)
        assert result.id == "new_user"
        # パスワードがハッシュ化されているか確認
        assert result.password != "Password123!"  # 生パスワードと異なる  # 生パスワードと異なる

    def test_signup_duplicate_user(self):
        """重複ユーザー登録のテスト"""
        # 最初にユーザーを作成（生パスワードを渡す）
        user1 = CustomUser(
            id="existing_user",
            password="Password123!",  # 生パスワード
            email="existing@example.com",
            name="Existing User",
            role="user",
        )
        self.auth.signup(user1)

        # 同じIDでユーザー作成を試みる
        user2 = CustomUser(
            id="existing_user",  # 同じID
            password="Password456!",  # 生パスワード
            email="different@example.com",
            name="Different User",
            role="user",
        )

        with pytest.raises(ConflictError):
            self.auth.signup(user2)

    def test_login_success(self):
        """ログイン成功のテスト"""
        # まずユーザーを作成（生パスワードを渡す）
        user = CustomUser(
            id="test_user",
            password="Password123!",  # 生パスワード
            email="test@example.com",
            name="Test User",
            role="user",
        )
        self.auth.signup(user)

        # ログイン（生パスワードを渡す）
        login_user = BaseUser()
        login_user.id = "test_user"
        result = self.auth.login(login_user, "Password123!")  # 生パスワード

        # トークンが返される
        assert isinstance(result, str)
        assert len(result) > 0  # トークンが空でない

    def test_login_invalid_credentials(self):
        """ログイン失敗のテスト"""
        user = BaseUser()
        user.id = "nonexistent_user"

        with pytest.raises(AuthenticationError):
            self.auth.login(user, "Password123!")

    def test_logout(self):
        """ログアウトのテスト"""
        # まずユーザーを作成してログイン（生パスワードを渡す）
        user = CustomUser(
            id="logout_test_user",
            password="Password123!",  # 生パスワード
            email="logout@example.com",
            name="Logout User",
            role="user",
        )
        self.auth.signup(user)

        # ログイン（生パスワードを渡す）
        login_user = BaseUser()
        login_user.id = "logout_test_user"
        token = self.auth.login(login_user, "Password123!")  # 生パスワード

        # ログアウトリクエストモック（既存のlogoutメソッドを使用）
        mock_event = {"headers": {"Authorization": f"Bearer {token}"}}
        logout_request = Request(mock_event)

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
