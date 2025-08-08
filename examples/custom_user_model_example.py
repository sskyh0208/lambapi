"""
カスタムユーザーモデルを使用した認証機能の例

BaseUser を継承してカスタムユーザーモデルを作成し、
デコレータで user 引数として受け取る方法を示します。
"""

import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Dict, Any
from lambapi import API, Response, create_lambda_handler, DynamoDBAuth, BaseUser


# カスタムユーザーモデルの定義（方法 1: コンストラクタで属性定義）
class CustomUser(BaseUser):
    """カスタムユーザーモデル（コンストラクタ方式）"""

    def __init__(self, data: Dict[str, Any], **kwargs):
        # 基底クラスの初期化（認証設定を継承）
        super().__init__(data, **kwargs)

        # カスタム属性をコンストラクタで定義
        self.full_name = (
            f"{self._data.get('first_name', '')} {self._data.get('last_name', '')}".strip()
        )
        self.display_name = self._data.get("display_name") or self.full_name or self.user_id
        self.is_admin = self._data.get("role") == "admin"
        self.permissions = self._data.get("permissions", [])

    def has_permission(self, permission: str) -> bool:
        """指定された権限を持っているかチェック"""
        return permission in self.permissions or self.is_admin

    def get_profile_data(self) -> dict:
        """プロフィール用のデータを返す（パスワードは除外）"""
        profile_data = self.to_dict()
        profile_data.pop("password", None)
        return profile_data


# カスタムユーザーモデルの定義（方法 2: _setup_custom_attributes を使用）
class AlternativeUser(BaseUser):
    """カスタムユーザーモデル（_setup_custom_attributes 方式）"""

    def _setup_custom_attributes(self):
        """カスタム属性の設定"""
        # カスタム属性を _setup_custom_attributes で定義
        self.full_name = (
            f"{self._data.get('first_name', '')} {self._data.get('last_name', '')}".strip()
        )
        self.display_name = self._data.get("display_name") or self.full_name or self.user_id
        self.is_admin = self._data.get("role") == "admin"
        self.permissions = self._data.get("permissions", [])

        # 複雑なロジックも可能
        self.access_level = self._calculate_access_level()

    def _calculate_access_level(self) -> int:
        """アクセスレベルを計算"""
        if self.is_admin:
            return 10
        elif "manager" in self._data.get("role", "").lower():
            return 5
        else:
            return 1

    def has_permission(self, permission: str) -> bool:
        """指定された権限を持っているかチェック"""
        return permission in self.permissions or self.is_admin


def create_app(event, context):
    """カスタムユーザーモデルを使用したアプリケーション"""
    app = API(event, context)

    # カスタムユーザーモデルを使用した認証システム
    auth = DynamoDBAuth(
        table_name="users",
        id_field="id",
        use_email=True,
        user_model=CustomUser,  # カスタムユーザーモデルを指定
    )

    app.include_auth(auth)

    # ===== パブリックエンドポイント =====

    @app.get("/")
    def public_root():
        return {"message": "Custom User Model API", "version": "1.0"}

    # ===== 新しいスタイルの認証（user 引数を使用） =====

    @app.get("/profile")
    @auth.require_auth
    def get_profile(request, user: CustomUser):
        """ユーザープロフィール取得（新スタイル）"""
        return {
            "message": "Profile retrieved successfully",
            "user": {
                "user_id": user.user_id,
                "display_name": user.display_name,
                "full_name": user.full_name,
                "email": user.email,
                "is_admin": user.is_admin,
                "permissions": user.permissions,
            },
        }

    @app.get("/dashboard")
    @auth.require_auth
    def get_dashboard(request, user: CustomUser):
        """ダッシュボード（新スタイル）"""
        welcome_message = f"Welcome {user.display_name}!"

        # 管理者の場合は追加情報を表示
        if user.is_admin:
            return {
                "message": welcome_message,
                "role": "Administrator",
                "admin_data": {"total_users": 150, "system_status": "healthy", "pending_tasks": 5},
            }
        else:
            return {
                "message": welcome_message,
                "role": "User",
                "user_data": {"tasks": 3, "notifications": 2},
            }

    @app.get("/admin/users")
    @auth.require_auth
    def admin_get_users(request, user: CustomUser):
        """管理者専用: ユーザー一覧"""
        if not user.is_admin:
            return Response({"error": "Admin access required"}, status_code=403)

        # 実際の実装では DynamoDB からユーザー一覧を取得
        return {
            "users": [
                {"id": "user1", "name": "User One", "email": "user1@example.com"},
                {"id": "user2", "name": "User Two", "email": "user2@example.com"},
            ],
            "total": 2,
        }

    @app.post("/documents/{doc_id}/access")
    @auth.require_auth
    def access_document(request, user: CustomUser, doc_id: str):
        """権限ベースのドキュメントアクセス"""
        required_permission = "document:read"

        if not user.has_permission(required_permission):
            return Response(
                {"error": f"Permission '{required_permission}' required"}, status_code=403
            )

        return {
            "message": f"Document {doc_id} accessed successfully",
            "accessed_by": user.display_name,
            "user_permissions": user.permissions,
        }

    # ===== 従来スタイルとの互換性 =====

    @app.get("/legacy/profile")
    @auth.require_auth
    def legacy_get_profile(request):
        """従来スタイル（request.user を使用）"""
        user_data = request.user  # 辞書形式
        return {
            "message": "Legacy profile endpoint",
            "user": user_data,
            "note": "This uses the legacy request.user approach",
        }

    # ===== エラーハンドリング =====

    @app.error_handler(Exception)
    def handle_auth_errors(error, request, context):
        error_type = str(type(error).__name__)

        if "Authentication" in error_type:
            return Response(
                {"error": "Authentication required", "message": str(error)}, status_code=401
            )
        elif "Authorization" in error_type or error_type == "AuthorizationError":
            return Response({"error": "Access denied", "message": str(error)}, status_code=403)
        else:
            return Response(
                {"error": "Internal server error", "message": str(error)}, status_code=500
            )

    return app


# Lambda 関数のエントリーポイント
lambda_handler = create_lambda_handler(create_app)


# ローカルテスト用コード
if __name__ == "__main__":
    print("=== カスタムユーザーモデル認証テスト ===\n")

    # テスト用のトークン（実際の実装では login エンドポイントから取得）
    sample_payload = {
        "user_id": "user123",
        "email": "john@example.com",
        "first_name": "John",
        "last_name": "Doe",
        "display_name": "Johnny",
        "role": "admin",
        "permissions": ["document:read", "document:write", "user:read"],
    }

    # トークン生成のシミュレーション
    from lambapi.auth import TokenManager

    token_manager = TokenManager("test-secret")
    sample_token = token_manager.generate_token(sample_payload)

    # テストケース 1: 新スタイルのプロフィール取得
    test_event_1 = {
        "httpMethod": "GET",
        "path": "/profile",
        "queryStringParameters": None,
        "headers": {"Content-Type": "application/json", "Authorization": f"Bearer {sample_token}"},
        "body": None,
    }

    print("Test 1: カスタムユーザーモデルでプロフィール取得")
    result1 = lambda_handler(test_event_1, None)
    print(json.dumps(result1, indent=2, ensure_ascii=False))
    print()

    # テストケース 2: 管理者ダッシュボード
    test_event_2 = {
        "httpMethod": "GET",
        "path": "/dashboard",
        "queryStringParameters": None,
        "headers": {"Content-Type": "application/json", "Authorization": f"Bearer {sample_token}"},
        "body": None,
    }

    print("Test 2: 管理者ダッシュボード")
    result2 = lambda_handler(test_event_2, None)
    print(json.dumps(result2, indent=2, ensure_ascii=False))
    print()

    # テストケース 3: 権限ベースのアクセス
    test_event_3 = {
        "httpMethod": "POST",
        "path": "/documents/doc123/access",
        "queryStringParameters": None,
        "headers": {"Content-Type": "application/json", "Authorization": f"Bearer {sample_token}"},
        "body": None,
    }

    print("Test 3: 権限ベースのドキュメントアクセス")
    result3 = lambda_handler(test_event_3, None)
    print(json.dumps(result3, indent=2, ensure_ascii=False))
    print()

    # テストケース 4: 従来スタイルとの互換性
    test_event_4 = {
        "httpMethod": "GET",
        "path": "/legacy/profile",
        "queryStringParameters": None,
        "headers": {"Content-Type": "application/json", "Authorization": f"Bearer {sample_token}"},
        "body": None,
    }

    print("Test 4: 従来スタイルとの互換性")
    result4 = lambda_handler(test_event_4, None)
    print(json.dumps(result4, indent=2, ensure_ascii=False))
    print()

    print("=== カスタムユーザーモデルの使用方法 ===")
    print(
        """
1. BaseUser を継承してカスタムユーザーモデルを作成（方法 1: コンストラクタ）:
   ```python
   class CustomUser(BaseUser):
       def __init__(self, data: Dict[str, Any], **kwargs):
           super().__init__(data, **kwargs)  # 認証設定を継承
           # カスタム属性をコンストラクタで定義
           self.full_name = f"{self.first_name} {self.last_name}"
           self.is_admin = self._data.get('role') == 'admin'
   ```

2. BaseUser を継承してカスタムユーザーモデルを作成（方法 2: _setup_custom_attributes）:
   ```python
   class CustomUser(BaseUser):
       def _setup_custom_attributes(self):
           # カスタム属性を _setup_custom_attributes で定義
           self.full_name = f"{self.first_name} {self.last_name}"
           self.is_admin = self._data.get('role') == 'admin'
           self.access_level = self._calculate_access_level()
   ```

3. DynamoDBAuth でカスタムモデルを指定:
   ```python
   auth = DynamoDBAuth("users", user_model=CustomUser)
   ```

4. デコレータで user 引数として受け取り:
   ```python
   @app.get("/profile")
   @auth.require_auth
   def get_profile(request, user: CustomUser):
       return {"name": user.full_name, "is_admin": user.is_admin}
   ```

5. 従来の request.user も引き続き利用可能:
   ```python
   @app.get("/legacy")
   @auth.require_auth
   def legacy_endpoint(request):
       user_data = request.user  # 辞書形式
       return {"user": user_data}
   ```

6. DynamoDB テーブル例:
   {
     "id": "user123",
     "password": "$2b$12$hashed_password...",
     "email": "john@example.com",
     "first_name": "John",
     "last_name": "Doe",
     "display_name": "Johnny",
     "role": "admin",
     "permissions": ["document:read", "document:write"],
     "created_at": 1633024800
   }
"""
    )
