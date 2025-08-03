"""
Lambda ZIP デプロイ用のサンプルアプリケーション
"""

import os
import logging
from lambapi import API, Response, create_lambda_handler
from lambapi.exceptions import ValidationError, NotFoundError

# ログ設定
logging.basicConfig(
    level=logging.INFO, format="%(asctime) s - %(name) s - %(levelname) s - %(message) s"
)
logger = logging.getLogger(__name__)

# インメモリデータストア（本番では DynamoDB などを使用）
USERS_DB = {}


def create_app(event, context):
    app = API(event, context)

    # CORS 設定
    app.enable_cors(
        origins=["*"] if os.getenv("ENVIRONMENT") == "development" else ["https://myapp.com"],
        methods=["GET", "POST", "PUT", "DELETE"],
        headers=["Content-Type", "Authorization"],
    )

    @app.get("/")
    def root():
        """ルートエンドポイント"""
        return {
            "message": "Hello from Lambda!",
            "version": "1.0.0",
            "environment": os.getenv("ENVIRONMENT", "development"),
            "function_name": context.function_name,
            "request_id": context.aws_request_id,
        }

    @app.get("/health")
    def health_check():
        """ヘルスチェック"""
        return {
            "status": "healthy",
            "timestamp": "2025-01-01T00:00:00Z",
            "memory_limit": context.memory_limit_in_mb,
            "remaining_time": context.get_remaining_time_in_millis(),
        }

    @app.get("/users")
    def get_users(limit: int = 10, search: str = ""):
        """ユーザー一覧取得"""
        users = list(USERS_DB.values())

        # 検索フィルター
        if search:
            users = [
                user
                for user in users
                if search.lower() in user["name"].lower() or search.lower() in user["email"].lower()
            ]

        # リミット適用
        users = users[:limit]

        logger.info(f"Retrieved {len(users)} users")

        return {
            "users": users,
            "total": len(users),
            "limit": limit,
            "search": search if search else None,
        }

    @app.get("/users/{user_id}")
    def get_user(user_id: str):
        """特定ユーザー取得"""
        if user_id not in USERS_DB:
            logger.warning(f"User not found: {user_id}")
            raise NotFoundError("User", user_id)

        user = USERS_DB[user_id]
        logger.info(f"Retrieved user: {user_id}")

        return {"user": user}

    @app.post("/users")
    def create_user(request):
        """新しいユーザー作成"""
        data = request.json()

        # バリデーション
        if not data.get("name"):
            raise ValidationError("Name is required", field="name")
        if not data.get("email"):
            raise ValidationError("Email is required", field="email")
        if not isinstance(data.get("age"), int) or data["age"] < 0:
            raise ValidationError("Age must be a positive integer", field="age")

        # メール重複チェック
        for existing_user in USERS_DB.values():
            if existing_user["email"] == data["email"]:
                raise ValidationError("Email already exists", field="email", value=data["email"])

        # ユーザー作成
        import uuid

        user_id = str(uuid.uuid4())
        user = {
            "id": user_id,
            "name": data["name"],
            "email": data["email"],
            "age": data["age"],
            "created_at": "2025-01-01T00:00:00Z",
        }

        USERS_DB[user_id] = user
        logger.info(f"Created user: {user_id}")

        return Response({"message": "User created successfully", "user": user}, status_code=201)

    @app.put("/users/{user_id}")
    def update_user(user_id: str, request):
        """ユーザー更新"""
        if user_id not in USERS_DB:
            raise NotFoundError("User", user_id)

        data = request.json()
        user = USERS_DB[user_id]

        # 更新可能なフィールドのみ処理
        if "name" in data and data["name"]:
            user["name"] = data["name"]
        if "email" in data and data["email"]:
            # メール重複チェック（自分以外）
            for uid, existing_user in USERS_DB.items():
                if uid != user_id and existing_user["email"] == data["email"]:
                    raise ValidationError("Email already exists", field="email")
            user["email"] = data["email"]
        if "age" in data and isinstance(data["age"], int) and data["age"] >= 0:
            user["age"] = data["age"]

        user["updated_at"] = "2025-01-01T00:00:00Z"
        logger.info(f"Updated user: {user_id}")

        return {"message": "User updated successfully", "user": user}

    @app.delete("/users/{user_id}")
    def delete_user(user_id: str):
        """ユーザー削除"""
        if user_id not in USERS_DB:
            raise NotFoundError("User", user_id)

        user = USERS_DB.pop(user_id)
        logger.info(f"Deleted user: {user_id}")

        return {"message": f"User {user['name']} deleted successfully", "deleted_user_id": user_id}

    # エラーハンドリング
    @app.default_error_handler
    def handle_error(error, request, context):
        logger.error(f"Unhandled error: {error}", exc_info=True)

        return Response(
            {
                "error": "Internal server error",
                "message": "An unexpected error occurred",
                "request_id": context.aws_request_id,
            },
            status_code=500,
        )

    return app


# Lambda ハンドラー
lambda_handler = create_lambda_handler(create_app)

# ローカルテスト用
if __name__ == "__main__":
    import json

    # サンプルデータ
    USERS_DB["1"] = {
        "id": "1",
        "name": "Alice",
        "email": "alice@example.com",
        "age": 25,
        "created_at": "2025-01-01T00:00:00Z",
    }
    USERS_DB["2"] = {
        "id": "2",
        "name": "Bob",
        "email": "bob@example.com",
        "age": 30,
        "created_at": "2025-01-01T00:00:00Z",
    }

    # テストイベント
    test_events = [
        {"httpMethod": "GET", "path": "/", "headers": {}, "body": None},
        {
            "httpMethod": "GET",
            "path": "/users",
            "queryStringParameters": {"limit": "5"},
            "headers": {},
            "body": None,
        },
        {"httpMethod": "GET", "path": "/users/1", "headers": {}, "body": None},
    ]

    # コンテキストモック
    context = type(
        "Context",
        (),
        {
            "aws_request_id": "test-request-id",
            "function_name": "test-function",
            "memory_limit_in_mb": "256",
            "get_remaining_time_in_millis": lambda: 30000,
        },
    )()

    # テスト実行
    for i, event in enumerate(test_events, 1):
        print(f"\n=== テスト {i}: {event['httpMethod']} {event['path']} ===")
        result = lambda_handler(event, context)
        print(f"ステータス: {result['statusCode']}")
        print(f"レスポンス: {result['body']}")
