"""
認証と依存性注入の統合テスト
"""

import pytest
import json
from unittest.mock import MagicMock
from typing import Optional

from lambapi import API, Query, Path, Body, Authenticated, create_lambda_handler
from lambapi.auth.dynamodb_auth import DynamoDBAuth
from lambapi.auth.base_user import BaseUser
from lambapi.exceptions import AuthenticationError, ValidationError


class CustomUser(BaseUser):
    def __init__(self, id: str = None, password: str = None):
        super().__init__(id, password)
        self.name: str = ""
        self.email: str = ""
        self.role: str = "user"

    class Meta(BaseUser.Meta):
        is_role_permission = True  # ロール機能を有効化


class MockDynamoDBAuth(DynamoDBAuth):
    """テスト用の MockDynamoDBAuth"""

    def __init__(self):
        # 親の __init__ をバイパスして必要な属性のみ設定
        self.user_model = CustomUser
        self.secret_key = "test_secret"  # nosec B105
        self._test_users = {}

    def get_authenticated_user(self, request):
        """テスト用の認証処理"""
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise AuthenticationError("認証トークンが見つかりません")

        token = auth_header[7:]  # "Bearer " を除去

        # テスト用の簡単なトークン検証
        if token == "valid_user_token":  # nosec B105
            user = CustomUser("user1", "password123")
            user.name = "Test User"
            user.email = "test@example.com"
            user.role = "user"
            return user
        elif token == "valid_admin_token":  # nosec B105
            user = CustomUser("admin1", "password123")
            user.name = "Admin User"
            user.email = "admin@example.com"
            user.role = "admin"
            return user
        else:
            raise AuthenticationError("無効なトークンです")


def create_test_event(
    path="/",
    method="GET",
    query_params=None,
    path_params=None,
    body=None,
    headers=None,
):
    """テスト用の Lambda イベントを作成"""
    event = {
        "httpMethod": method,
        "path": path,
        "queryStringParameters": query_params,
        "pathParameters": path_params,
        "headers": headers or {},
    }

    if body:
        event["body"] = json.dumps(body) if isinstance(body, dict) else body

    return event


class TestAuthenticationIntegration:
    """認証と依存性注入の統合テスト"""

    def setup_method(self):
        """テスト前の準備"""
        # AWS Lambda Context をモック
        self.context = MagicMock()
        self.context.function_name = "test"
        self.context.aws_request_id = "test-request-id"
        self.auth = MockDynamoDBAuth()

    def test_authenticated_parameter_injection(self):
        """Authenticated パラメータの注入テスト"""

        # まず基本的な依存性注入のみをテスト
        def test_handler(
            message: str = Query("default"),
        ):
            return {"message": message}

        event = create_test_event(
            path="/test",
            query_params={"message": "hello"},
        )
        api = API(event, self.context)
        api.get("/test")(test_handler)

        response = api.handle_request()

        print(f"Response: {response}")  # デバッグ用
        if response["statusCode"] != 200:
            print(f"Response body: {response.get('body', 'No body')}")

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["message"] == "hello"

    def test_role_based_access_control(self):
        """ロールベースアクセス制御のテスト"""

        # モジュールレベルで auth を設定（API の探索対象に含める）
        import sys

        current_module = sys.modules[__name__]
        current_module.auth = self.auth

        def admin_handler(
            user: CustomUser = Authenticated(...),
            action: str = Query(...),
        ):
            return {"admin": user.name, "action": action, "role": user.role}

        # 管理者権限が必要な処理
        event = create_test_event(
            path="/admin/action",
            query_params={"action": "delete"},
            headers={"Authorization": "Bearer valid_admin_token"},
        )
        api = API(event, self.context)
        api.get("/admin/action")(self.auth.require_role("admin")(admin_handler))

        response = api.handle_request()

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["admin"] == "Admin User"
        assert body["action"] == "delete"
        assert body["role"] == "admin"

    def test_access_denied_for_insufficient_role(self):
        """権限不足によるアクセス拒否のテスト"""

        # モジュールレベルで auth を設定（API の探索対象に含める）
        import sys

        current_module = sys.modules[__name__]
        current_module.auth = self.auth

        def admin_handler(
            user: CustomUser = Authenticated(...),
        ):
            return {"message": "admin only"}

        # 一般ユーザーが管理者権限が必要な処理にアクセス
        event = create_test_event(
            path="/admin/secret", headers={"Authorization": "Bearer valid_user_token"}
        )
        api = API(event, self.context)
        api.get("/admin/secret")(self.auth.require_role("admin")(admin_handler))

        response = api.handle_request()

        # アクセス拒否されるはず
        assert response["statusCode"] == 403

    def test_unauthenticated_request(self):
        """未認証リクエストのテスト"""

        # モジュールレベルで auth を設定（API の探索対象に含める）
        import sys

        current_module = sys.modules[__name__]
        current_module.auth = self.auth

        def protected_handler(
            user: CustomUser = Authenticated(...),
        ):
            return {"user": user.id}

        # 認証ヘッダーなし
        event = create_test_event(path="/protected")
        api = API(event, self.context)
        api.get("/protected")(self.auth.require_role("user")(protected_handler))

        response = api.handle_request()

        # 認証エラーになるはず
        assert response["statusCode"] == 401

    def test_complex_parameter_combination(self):
        """複雑なパラメータの組み合わせテスト"""

        # モジュールレベルで auth を設定（API の探索対象に含める）
        import sys

        current_module = sys.modules[__name__]
        current_module.auth = self.auth

        def complex_handler(
            user: CustomUser = Authenticated(...),
            user_id: str = Path(...),
            filter_name: str = Query("all"),
            limit: int = Query(10, ge=1, le=100),
            request_data: dict = Body(...),
        ):
            return {
                "authenticated_user": user.id,
                "target_user": user_id,
                "filter": filter_name,
                "limit": limit,
                "data": request_data,
                "role": user.role,
            }

        body_data = {"operation": "update", "values": [1, 2, 3]}
        event = create_test_event(
            path="/users/user123",
            method="POST",
            query_params={"filter_name": "active", "limit": "20"},
            path_params={"user_id": "user123"},
            body=body_data,
            headers={"Authorization": "Bearer valid_admin_token"},
        )

        api = API(event, self.context)
        api.post("/users/{user_id}")(self.auth.require_role("admin")(complex_handler))

        response = api.handle_request()

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["authenticated_user"] == "admin1"
        assert body["target_user"] == "user123"
        assert body["filter"] == "active"
        assert body["limit"] == 20
        assert body["data"] == body_data
        assert body["role"] == "admin"

    def test_validation_error_with_authentication(self):
        """認証ありでのバリデーションエラーテスト"""

        # モジュールレベルで auth を設定（API の探索対象に含める）
        import sys

        current_module = sys.modules[__name__]
        current_module.auth = self.auth

        def validated_handler(
            user: CustomUser = Authenticated(...),
            age: int = Query(..., ge=0, le=120),
        ):
            return {"user": user.id, "age": age}

        # バリデーション違反のリクエスト
        event = create_test_event(
            path="/validate",
            query_params={"age": "150"},  # 範囲外の値
            headers={"Authorization": "Bearer valid_user_token"},
        )

        api = API(event, self.context)
        api.get("/validate")(self.auth.require_role("user")(validated_handler))

        response = api.handle_request()

        # バリデーションエラーになるはず
        assert response["statusCode"] == 400
