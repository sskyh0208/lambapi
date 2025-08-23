"""
API 使用例
Lambda 関数でのモダンな API の実装例
"""

import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lambapi import API, Response, create_lambda_handler


# グローバルスコープでのルート定義（重要：パフォーマンス最適化のため）
def create_app(event, context):
    """アプリケーション作成関数"""
    app = API(event, context)

    # CORS 設定のミドルウェア例
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

    # ===== ルート定義 =====

    @app.get("/")
    def hello_world(request):
        """基本的な Hello World"""
        msg = "Hello Lambda!!"
        print(msg)
        return {"message": msg}

    @app.get("/health")
    def health_check(request):
        """ヘルスチェック"""
        return {"status": "ok", "service": "lambapi"}

    @app.get("/users/{user_id}")
    def get_user(user_id: str, include_details: bool = False):
        """ユーザー取得（パスパラメータ付き）"""
        user_data = {
            "user_id": user_id,
            "name": f"User {user_id}",
            "email": f"user{user_id}@example.com",
        }

        if include_details:
            user_data["details"] = {
                "created_at": "2024-01-01T00:00:00Z",
                "last_login": "2024-01-02T10:30:00Z",
            }

        return user_data

    @app.post("/users")
    def create_user(request):
        """ユーザー作成（JSON ボディ）"""
        try:
            user_data = request.json()

            # バリデーション例
            if not user_data.get("name"):
                return Response({"error": "Name is required"}, status_code=400)

            # 作成処理のシミュレーション
            new_user = {
                "id": "generated-id-123",
                "name": user_data["name"],
                "email": user_data.get("email", ""),
                "created_at": "2024-01-01T00:00:00Z",
            }

            return Response(
                {"message": "User created successfully", "user": new_user}, status_code=201
            )

        except Exception as e:
            return Response({"error": "Invalid JSON data", "detail": str(e)}, status_code=400)

    @app.put("/users/{user_id}")
    def update_user(user_id: str, request):
        """ユーザー更新"""
        user_data = request.json()

        return {"message": f"User {user_id} updated", "data": user_data}

    @app.delete("/users/{user_id}")
    def delete_user(user_id: str):
        """ユーザー削除"""
        return Response({"message": f"User {user_id} deleted"}, status_code=204)

    @app.get("/api/v1/products/{category}")
    def get_products_by_category(category: str, limit: int = 10, offset: int = 0):
        """カテゴリ別商品取得（ネストしたパス）"""

        # 商品データのシミュレーション
        products = [
            {
                "id": f"prod-{category}-{i}",
                "name": f"{category.title()} Product {i}",
                "price": 100 + i * 10,
                "category": category,
            }
            for i in range(offset + 1, offset + limit + 1)
        ]

        return {
            "category": category,
            "products": products,
            "pagination": {
                "limit": limit,
                "offset": offset,
                "total": 100,  # 実際のアプリでは DB から取得
            },
        }

    @app.post("/api/v1/auth/login")
    def login(request):
        """ログイン例"""
        credentials = request.json()

        # 簡単な認証チェック
        if credentials.get("username") == "admin" and credentials.get("password") == "password":

            return {
                "token": "dummy-jwt-token",
                "expires_in": 3600,
                "user": {"id": "admin-user", "username": "admin", "role": "administrator"},
            }
        else:
            return Response({"error": "Invalid credentials"}, status_code=401)

    # エラーハンドリングの例
    @app.get("/error-test")
    def error_test(request):
        """エラーテスト用エンドポイント"""
        error_type = request.query_params.get("type", "general")

        if error_type == "not_found":
            return Response({"error": "Resource not found"}, status_code=404)
        elif error_type == "server_error":
            raise Exception("Intentional server error for testing")
        else:
            return {"message": "No error"}

    return app


# Lambda 関数のエントリーポイント
lambda_handler = create_lambda_handler(create_app)


# ローカルテスト用コード
if __name__ == "__main__":
    # テストケース 1: 基本の GET
    test_event_1 = {
        "httpMethod": "GET",
        "path": "/",
        "queryStringParameters": None,
        "headers": {"Content-Type": "application/json"},
        "body": None,
    }

    print("=== Test 1: Basic GET ===")
    result1 = lambda_handler(test_event_1, None)
    print(json.dumps(result1, indent=2, ensure_ascii=False))

    # テストケース 2: パスパラメータ付き GET
    test_event_2 = {
        "httpMethod": "GET",
        "path": "/users/123",
        "queryStringParameters": {"details": "true"},
        "headers": {},
        "body": None,
    }

    print("\n=== Test 2: GET with path params ===")
    result2 = lambda_handler(test_event_2, None)
    print(json.dumps(result2, indent=2, ensure_ascii=False))

    # テストケース 3: POST（JSON）
    test_event_3 = {
        "httpMethod": "POST",
        "path": "/users",
        "queryStringParameters": None,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"name": "John Doe", "email": "john@example.com"}),
    }

    print("\n=== Test 3: POST with JSON ===")
    result3 = lambda_handler(test_event_3, None)
    print(json.dumps(result3, indent=2, ensure_ascii=False))

    # テストケース 4: 404 エラー
    test_event_4 = {
        "httpMethod": "GET",
        "path": "/nonexistent",
        "queryStringParameters": None,
        "headers": {},
        "body": None,
    }

    print("\n=== Test 4: 404 Error ===")
    result4 = lambda_handler(test_event_4, None)
    print(json.dumps(result4, indent=2, ensure_ascii=False))
