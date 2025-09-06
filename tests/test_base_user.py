"""
BaseUser クラスのテスト

基本的なユーザーモデルのテストを行います。
"""

import pytest
import datetime
from lambapi.auth import BaseUser


class CustomUser(BaseUser):
    """テスト用カスタムユーザー"""

    class Meta(BaseUser.Meta):
        table_name = "test_users"
        expiration = 3600
        is_role_permission = True
        enable_auth_logging = False

    def __init__(self, id=None, password=None, email="", role="user", name="Test User"):
        self.id = id
        self.password = password
        self.email = email
        self.role = role
        self.name = name
        self.is_admin = role == "admin"


class TestBaseUser:
    """BaseUser クラスのテスト"""

    def test_base_user_creation(self):
        """BaseUser の基本的な作成テスト"""
        user = BaseUser(id="test_user", password="Password123!")
        assert user.id == "test_user"
        assert (
            user.password == "Password123!"
        )  # BaseUser.__init__はpassのみなので生パスワードが保存される  # nosec B105

    def test_password_verification(self):
        """パスワード検証のテスト"""
        # BaseUser.__init__がpassのみになったため、ハッシュ化はauth.signup経由で行われる
        # ここではhash_passwordメソッドとverify_passwordメソッドをテスト
        user = BaseUser(id="test_user", password=BaseUser.hash_password("Password123!"))
        assert user.verify_password("Password123!") is True
        assert user.verify_password("wrong_password") is False

    def test_custom_user_creation(self):
        """カスタムユーザーの作成テスト"""
        user = CustomUser("custom_user", "Password123!", "test@example.com")
        assert user.id == "custom_user"
        assert user.email == "test@example.com"
        assert user.role == "user"
        assert user.name == "Test User"

    def test_to_dict(self):
        """辞書変換のテスト"""
        user = CustomUser("test_user", "Password123!", "test@example.com")
        user_dict = user.to_dict()

        assert "id" in user_dict
        assert "email" in user_dict
        assert "password" not in user_dict  # パスワードは除外される

    def test_to_token_payload(self):
        """トークンペイロード作成のテスト"""
        user = CustomUser("test_user", "Password123!", "test@example.com")
        payload = user.to_token_payload()

        assert "id" in payload
        assert "email" in payload
        assert "iat" in payload
        assert "exp" in payload
        assert "password" not in payload

    def test_password_validation_requirements(self):
        """パスワード要件のテスト"""
        user = BaseUser()

        # 短すぎるパスワード
        with pytest.raises(ValueError, match=r"パスワードは\d+文字以上である必要があります"):
            user.validate_password("123")

        # 数字要件を満たさないパスワード（デフォルトは数字必須）
        with pytest.raises(ValueError, match="パスワードには数字を含める必要があります"):
            user.validate_password("onlyletters")

    def test_custom_meta_settings(self):
        """カスタムメタ設定のテスト"""
        assert CustomUser.Meta.table_name == "test_users"
        assert CustomUser.Meta.is_role_permission is True

    def test_email_validation(self):
        """メールアドレスバリデーションのテスト"""
        # 有効なメールアドレス
        user = CustomUser(
            "test", "Password123!", "valid@example.com", role="user", name="Test User"
        )
        user.validate_email("valid@example.com")  # エラーが発生しないことを確認

        # 無効なメールアドレス
        with pytest.raises(ValueError, match="有効なメールアドレスを入力してください"):
            user.validate_email("invalid-email")


if __name__ == "__main__":
    print("BaseUser の基本テストを実行中...")

    try:
        # BaseUser のテスト
        print("✓ BaseUser 作成テスト")
        user = BaseUser()
        user.id = "test"
        user.password = user.hash_password("Password123!")
        assert user.verify_password("Password123!")
        print("✓ パスワード検証テスト")

        # CustomUser のテスト
        custom_user = CustomUser(
            "custom", "Password123!", "test@example.com", role="user", name="Test User"
        )
        assert custom_user.email == "test@example.com"
        print("✓ CustomUser 作成テスト")

        user_dict = custom_user.to_dict()
        assert "password" not in user_dict
        print("✓ 辞書変換テスト")

        payload = custom_user.to_token_payload()
        assert "iat" in payload and "exp" in payload
        print("✓ トークンペイロード作成テスト")

        print("\n✅ BaseUser テストが完了しました！")

    except Exception as e:
        print(f"\n❌ テスト失敗: {e}")
        raise
