"""
依存性注入機能のサンプル
Query, Path, Body パラメータの依存性注入例
"""

import json
import sys
import os
from dataclasses import dataclass
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lambapi import API, Response, create_lambda_handler, Query, Path, Body


# リクエスト用データクラス
@dataclass
class CreateUserRequest:
    name: str
    email: str
    age: Optional[int] = None


# レスポンス用データクラス
@dataclass
class UserResponse:
    id: str
    name: str
    email: str
    age: Optional[int]
    created_at: str


@dataclass
class ErrorResponse:
    error: str
    detail: str


def create_app(event, context):
    """アプリケーション作成関数"""
    app = API(event, context)

    # CORS 設定のミドルウェア
    def cors_middleware(request, response):
        if isinstance(response, Response):
            response.headers.update(
                {
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                    "Access-Control-Allow-Headers": "Content-Type, Authorization",
                }
            )
        return response

    app.add_middleware(cors_middleware)

    # ===== 依存性注入を使ったルート定義 =====

    @app.post("/users")
    def create_user(user_data: CreateUserRequest = Body(...)):
        """ユーザー作成（依存性注入付き）"""
        # user_data は CreateUserRequest オブジェクトとして受け取れる
        print(f"受信データ: name={user_data.name}, email={user_data.email}, age={user_data.age}")

        # レスポンスデータを作成
        response_data = {
            "id": f"user_{hash(user_data.email) % 10000}",
            "name": user_data.name,
            "email": user_data.email,
            "age": user_data.age,
            "created_at": "2024-01-01T00:00:00Z",
        }

        return response_data

    @app.get("/users/{user_id}")
    def get_user(user_id: str = Path(...)):
        """ユーザー取得（パスパラメータ依存性注入）"""
        # サンプルユーザーデータ
        user_data = {
            "id": user_id,
            "name": f"User {user_id}",
            "email": f"user{user_id}@example.com",
            "age": 25,
            "created_at": "2024-01-01T00:00:00Z",
        }

        return user_data

    # 従来の形式も併用可能
    @app.get("/health")
    def health_check(request):
        """ヘルスチェック（従来形式）"""
        return {"status": "ok", "service": "lambapi"}

    @app.post("/users/legacy")
    def create_user_legacy(request):
        """ユーザー作成（従来形式）"""
        try:
            user_data = request.json()

            if not user_data.get("name"):
                return Response({"error": "Name is required"}, status_code=400)

            new_user = {
                "id": "legacy-user-123",
                "name": user_data["name"],
                "email": user_data.get("email", ""),
                "created_at": "2024-01-01T00:00:00Z",
            }

            return Response(
                {"message": "User created successfully", "user": new_user}, status_code=201
            )

        except Exception as e:
            return Response({"error": "Invalid JSON data", "detail": str(e)}, status_code=400)

    return app


# Lambda 関数のエントリーポイント
lambda_handler = create_lambda_handler(create_app)


# ローカルテスト用コード
if __name__ == "__main__":

    # テストケース 1: バリデーション付きユーザー作成（正常）
    test_event_1 = {
        "httpMethod": "POST",
        "path": "/users",
        "queryStringParameters": None,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"name": "John Doe", "email": "john@example.com", "age": 30}),
    }

    print("=== Test 1: 依存性注入付きユーザー作成（正常） ===")
    result1 = lambda_handler(test_event_1, None)
    print(json.dumps(result1, indent=2, ensure_ascii=False))

    # テストケース 2: 依存性注入付きユーザー作成（バリデーションエラー）
    test_event_2 = {
        "httpMethod": "POST",
        "path": "/users",
        "queryStringParameters": None,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(
            {
                "email": "john@example.com",
                "age": 30,
                # name が不足
            }
        ),
    }

    print("\n=== Test 2: バリデーションエラー（name 不足） ===")
    result2 = lambda_handler(test_event_2, None)
    print(json.dumps(result2, indent=2, ensure_ascii=False))

    # テストケース 3: パスパラメータ依存性注入付きユーザー取得
    test_event_3 = {
        "httpMethod": "GET",
        "path": "/users/123",
        "queryStringParameters": None,
        "headers": {},
        "body": None,
    }

    print("\n=== Test 3: パスパラメータ依存性注入付きユーザー取得 ===")
    result3 = lambda_handler(test_event_3, None)
    print(json.dumps(result3, indent=2, ensure_ascii=False))

    # テストケース 4: 従来形式のヘルスチェック
    test_event_4 = {
        "httpMethod": "GET",
        "path": "/health",
        "queryStringParameters": None,
        "headers": {},
        "body": None,
    }

    print("\n=== Test 4: 従来形式のヘルスチェック ===")
    result4 = lambda_handler(test_event_4, None)
    print(json.dumps(result4, indent=2, ensure_ascii=False))

    # テストケース 5: 型変換テスト（age を文字列で送信）
    test_event_5 = {
        "httpMethod": "POST",
        "path": "/users",
        "queryStringParameters": None,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(
            {"name": "Jane Smith", "email": "jane@example.com", "age": "25"}  # 文字列として送信
        ),
    }

    print("\n=== Test 5: 型変換テスト（age 文字列→int） ===")
    result5 = lambda_handler(test_event_5, None)
    print(json.dumps(result5, indent=2, ensure_ascii=False))
