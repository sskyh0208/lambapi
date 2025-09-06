"""
Router を使用した API 実装例
ルーター機能を使用して API を構造化します。
"""

import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lambapi import API, Router, Response, create_lambda_handler


# ユーザー関連のルーター
user_router = Router(prefix="/users", tags=["users"])


@user_router.get("/")
def list_users(request):
    """ユーザー一覧取得"""
    return {"users": ["user1", "user2", "user3"]}


@user_router.get("/{user_id}")
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


@user_router.post("/")
def create_user(request):
    """ユーザー作成"""
    try:
        user_data = request.json()

        if not user_data.get("name"):
            return Response({"error": "Name is required"}, status_code=400)

        new_user = {
            "id": "generated-id-123",
            "name": user_data["name"],
            "email": user_data.get("email", ""),
            "created_at": "2024-01-01T00:00:00Z",
        }

        return Response({"message": "User created successfully", "user": new_user}, status_code=201)

    except Exception as e:
        return Response({"error": "Invalid JSON data", "detail": str(e)}, status_code=400)


@user_router.put("/{user_id}")
def update_user(user_id: str, request):
    """ユーザー更新"""
    user_data = request.json()

    return {"message": f"User {user_id} updated", "data": user_data}


@user_router.delete("/{user_id}")
def delete_user(user_id: str):
    """ユーザー削除"""
    return Response({"message": f"User {user_id} deleted"}, status_code=204)


# 商品関連のルーター
product_router = Router(prefix="/api/v1/products", tags=["products"])


@product_router.get("/{category}")
def get_products_by_category(category: str, limit: int = 10, offset: int = 0):
    """カテゴリ別商品取得"""
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
        "pagination": {"limit": limit, "offset": offset, "total": 100},
    }


# 認証関連のルーター
auth_router = Router(prefix="/api/v1/auth", tags=["auth"])


@auth_router.post("/login")
def login(request):
    """ログイン"""
    credentials = request.json()

    if credentials.get("username") == "admin" and credentials.get("password") == "password":

        return {
            "token": "dummy-jwt-token",
            "expires_in": 3600,
            "user": {"id": "admin-user", "username": "admin", "role": "administrator"},
        }
    else:
        return Response({"error": "Invalid credentials"}, status_code=401)


# 公開エンドポイント用のルーター
public_router = Router(prefix="", tags=["public"])


@public_router.get("/")
def hello_world(request):
    """基本的な Hello World"""
    msg = "Hello lambapi!!"
    print(msg)
    return {"message": msg}


@public_router.get("/health")
def health_check(request):
    """ヘルスチェック"""
    return {"status": "ok", "service": "lambapi"}


@public_router.get("/error-test")
def error_test(request):
    """エラーテスト用エンドポイント"""
    error_type = request.query_params.get("type", "general")

    if error_type == "not_found":
        return Response({"error": "Resource not found"}, status_code=404)
    elif error_type == "server_error":
        raise Exception("Intentional server error for testing")
    else:
        return {"message": "No error"}


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

    # ルーターを登録
    app.add_router(public_router)
    app.add_router(user_router)
    app.add_router(product_router)
    app.add_router(auth_router)

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

    # テストケース 2: ルーター使用（ユーザー取得）
    test_event_2 = {
        "httpMethod": "GET",
        "path": "/users/123",
        "queryStringParameters": {"include_details": "true"},
        "headers": {},
        "body": None,
    }

    print("\n=== Test 2: GET User with Router ===")
    result2 = lambda_handler(test_event_2, None)
    print(json.dumps(result2, indent=2, ensure_ascii=False))

    # テストケース 3: POST（ユーザー作成）
    test_event_3 = {
        "httpMethod": "POST",
        "path": "/users",
        "queryStringParameters": None,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"name": "John Doe", "email": "john@example.com"}),
    }

    print("\n=== Test 3: POST User with Router ===")
    result3 = lambda_handler(test_event_3, None)
    print(json.dumps(result3, indent=2, ensure_ascii=False))

    # テストケース 4: 商品取得（ネストしたルート）
    test_event_4 = {
        "httpMethod": "GET",
        "path": "/api/v1/products/electronics",
        "queryStringParameters": {"limit": "5", "offset": "0"},
        "headers": {},
        "body": None,
    }

    print("\n=== Test 4: GET Products with Router ===")
    result4 = lambda_handler(test_event_4, None)
    print(json.dumps(result4, indent=2, ensure_ascii=False))
