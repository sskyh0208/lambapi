"""
Lambda ECR デプロイ用のサンプルアプリケーション
大規模アプリケーション向け
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from lambapi import API, Response, create_lambda_handler
from lambapi.exceptions import ValidationError, NotFoundError

# 構造化ログ設定
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format=(
        json.dumps(
            {
                "timestamp": "%(asctime) s",
                "level": "%(levelname) s",
                "logger": "%(name) s",
                "message": "%(message) s",
            }
        )
        if os.getenv("LOG_FORMAT") == "json"
        else "%(asctime) s - %(name) s - %(levelname) s - %(message) s"
    ),
)
logger = logging.getLogger(__name__)

# グローバル変数（Lambda コンテナ再利用のため）
USERS_DB: Dict[str, Dict] = {}
PRODUCTS_DB: Dict[str, Dict] = {}


def init_sample_data():
    """サンプルデータの初期化（初回実行時のみ）"""
    # グローバル変数を初期化

    if not USERS_DB:
        USERS_DB.update(
            {
                "1": {
                    "id": "1",
                    "name": "Alice Johnson",
                    "email": "alice@example.com",
                    "age": 28,
                    "role": "admin",
                    "created_at": datetime.now().isoformat(),
                    "profile": {"department": "Engineering", "skills": ["Python", "AWS", "Docker"]},
                },
                "2": {
                    "id": "2",
                    "name": "Bob Smith",
                    "email": "bob@example.com",
                    "age": 32,
                    "role": "user",
                    "created_at": datetime.now().isoformat(),
                    "profile": {"department": "Marketing", "skills": ["Analytics", "SEO"]},
                },
            }
        )

    if not PRODUCTS_DB:
        PRODUCTS_DB.update(
            {
                "1": {
                    "id": "1",
                    "name": "Premium Widget",
                    "description": "High-quality widget for enterprise use",
                    "price": 299.99,
                    "category": "widgets",
                    "inventory": 150,
                    "created_at": datetime.now().isoformat(),
                },
                "2": {
                    "id": "2",
                    "name": "Basic Tool",
                    "description": "Essential tool for daily tasks",
                    "price": 49.99,
                    "category": "tools",
                    "inventory": 500,
                    "created_at": datetime.now().isoformat(),
                },
            }
        )

    logger.info(f"Initialized sample data: {len(USERS_DB)} users, {len(PRODUCTS_DB)} products")


def create_app(event, context):
    """lambapi アプリケーションを作成"""

    # サンプルデータの初期化
    init_sample_data()

    app = API(event, context)

    # 環境別 CORS 設定
    cors_origins = (
        ["*"]
        if os.getenv("ENVIRONMENT") == "development"
        else ["https://myapp.com", "https://www.myapp.com", "https://admin.myapp.com"]
    )

    app.enable_cors(
        origins=cors_origins,
        methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        headers=["Content-Type", "Authorization", "X-Api-Key"],
        allow_credentials=True,
        max_age=3600,
    )

    # ========== システム系エンドポイント ==========

    @app.get("/")
    def root():
        """ルートエンドポイント"""
        return {
            "service": "lambapi Advanced API",
            "version": "2.0.0",
            "environment": os.getenv("ENVIRONMENT", "development"),
            "deployment": "ECR Container",
            "function_name": context.function_name,
            "request_id": context.aws_request_id,
            "memory_limit": f"{context.memory_limit_in_mb}MB",
            "remaining_time": f"{context.get_remaining_time_in_millis()}ms",
        }

    @app.get("/health")
    def health_check():
        """詳細なヘルスチェック"""
        try:
            # 各種チェック
            checks = {
                "database": len(USERS_DB) > 0,  # 実際は DB 接続チェック
                "memory": context.get_remaining_time_in_millis() > 5000,
                "environment": os.getenv("ENVIRONMENT") is not None,
            }

            all_healthy = all(checks.values())

            return Response(
                {
                    "status": "healthy" if all_healthy else "degraded",
                    "timestamp": datetime.now().isoformat(),
                    "checks": checks,
                    "system": {
                        "memory_limit": f"{context.memory_limit_in_mb}MB",
                        "remaining_time": f"{context.get_remaining_time_in_millis()}ms",
                        "environment": os.getenv("ENVIRONMENT"),
                        "log_level": os.getenv("LOG_LEVEL", "INFO"),
                    },
                },
                status_code=200 if all_healthy else 503,
            )

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return Response(
                {"status": "unhealthy", "error": str(e), "timestamp": datetime.now().isoformat()},
                status_code=503,
            )

    @app.get("/metrics")
    def get_metrics():
        """アプリケーションメトリクス"""
        return {
            "users": {
                "total": len(USERS_DB),
                "by_role": {
                    "admin": len([u for u in USERS_DB.values() if u.get("role") == "admin"]),
                    "user": len([u for u in USERS_DB.values() if u.get("role") == "user"]),
                },
            },
            "products": {
                "total": len(PRODUCTS_DB),
                "total_inventory": sum(p.get("inventory", 0) for p in PRODUCTS_DB.values()),
                "by_category": {},
            },
            "system": {
                "uptime": "N/A",  # 実際はコンテナ起動時間
                "memory_usage": f"{context.memory_limit_in_mb}MB allocated",
            },
        }

    # ========== ユーザー管理 API ==========

    @app.get("/users")
    def get_users(
        limit: int = 20,
        offset: int = 0,
        search: str = "",
        role: str = "",
        sort_by: str = "name",
        sort_order: str = "asc",
    ):
        """高度なフィルタリング付きユーザー一覧"""
        users = list(USERS_DB.values())

        # フィルタリング
        if search:
            users = [
                user
                for user in users
                if search.lower() in user["name"].lower()
                or search.lower() in user["email"].lower()
                or search.lower() in user.get("profile", {}).get("department", "").lower()
            ]

        if role:
            users = [user for user in users if user.get("role") == role]

        # ソート
        reverse = sort_order.lower() == "desc"
        if sort_by == "name":
            users.sort(key=lambda u: u["name"], reverse=reverse)
        elif sort_by == "age":
            users.sort(key=lambda u: u["age"], reverse=reverse)
        elif sort_by == "created_at":
            users.sort(key=lambda u: u["created_at"], reverse=reverse)

        # ページネーション
        total = len(users)
        paginated_users = users[offset : offset + limit]

        logger.info(f"Retrieved {len(paginated_users)} users (total: {total})")

        return {
            "users": paginated_users,
            "pagination": {
                "total": total,
                "limit": limit,
                "offset": offset,
                "has_more": offset + limit < total,
                "next_offset": offset + limit if offset + limit < total else None,
            },
            "filters": {
                "search": search or None,
                "role": role or None,
                "sort_by": sort_by,
                "sort_order": sort_order,
            },
        }

    @app.get("/users/{user_id}")
    def get_user(user_id: str, include_profile: bool = True):
        """詳細なユーザー情報取得"""
        if user_id not in USERS_DB:
            logger.warning(f"User not found: {user_id}")
            raise NotFoundError("User", user_id)

        user = USERS_DB[user_id].copy()

        if not include_profile:
            user.pop("profile", None)

        logger.info(f"Retrieved user: {user_id}")

        return {
            "user": user,
            "metadata": {
                "retrieved_at": datetime.now().isoformat(),
                "include_profile": include_profile,
            },
        }

    @app.post("/users")
    def create_user(request):
        """高度なバリデーション付きユーザー作成"""
        data = request.json()

        # 詳細バリデーション
        errors = []

        if not data.get("name") or len(data["name"]) < 2:
            errors.append({"field": "name", "message": "Name must be at least 2 characters"})

        if not data.get("email") or "@" not in data["email"]:
            errors.append({"field": "email", "message": "Valid email is required"})

        if not isinstance(data.get("age"), int) or data["age"] < 0 or data["age"] > 150:
            errors.append({"field": "age", "message": "Age must be between 0 and 150"})

        if data.get("role") and data["role"] not in ["admin", "user", "moderator"]:
            errors.append({"field": "role", "message": "Role must be admin, user, or moderator"})

        if errors:
            raise ValidationError("Validation failed", field="multiple", details=errors)

        # メール重複チェック
        for existing_user in USERS_DB.values():
            if existing_user["email"].lower() == data["email"].lower():
                raise ValidationError("Email already exists", field="email", value=data["email"])

        # ユーザー作成
        import uuid

        user_id = str(uuid.uuid4())

        user = {
            "id": user_id,
            "name": data["name"],
            "email": data["email"],
            "age": data["age"],
            "role": data.get("role", "user"),
            "created_at": datetime.now().isoformat(),
            "profile": data.get("profile", {}),
        }

        USERS_DB[user_id] = user
        logger.info(f"Created user: {user_id} ({user['email']})")

        return Response(
            {
                "message": "User created successfully",
                "user": user,
                "links": {
                    "self": f"/users/{user_id}",
                    "update": f"/users/{user_id}",
                    "delete": f"/users/{user_id}",
                },
            },
            status_code=201,
        )

    # ========== 商品管理 API ==========

    @app.get("/products")
    def get_products(
        limit: int = 20,
        offset: int = 0,
        category: str = "",
        min_price: float = 0.0,
        max_price: float = 999999.0,
        in_stock: bool = None,
    ):
        """商品一覧取得"""
        products = list(PRODUCTS_DB.values())

        # フィルタリング
        if category:
            products = [p for p in products if p.get("category") == category]

        products = [p for p in products if min_price <= p.get("price", 0) <= max_price]

        if in_stock is not None:
            if in_stock:
                products = [p for p in products if p.get("inventory", 0) > 0]
            else:
                products = [p for p in products if p.get("inventory", 0) == 0]

        # ページネーション
        total = len(products)
        paginated_products = products[offset : offset + limit]

        return {
            "products": paginated_products,
            "pagination": {
                "total": total,
                "limit": limit,
                "offset": offset,
                "has_more": offset + limit < total,
            },
            "filters": {
                "category": category or None,
                "price_range": {"min": min_price, "max": max_price},
                "in_stock": in_stock,
            },
        }

    @app.get("/products/{product_id}")
    def get_product(product_id: str):
        """商品詳細取得"""
        if product_id not in PRODUCTS_DB:
            raise NotFoundError("Product", product_id)

        product = PRODUCTS_DB[product_id]

        return {
            "product": product,
            "availability": {
                "in_stock": product.get("inventory", 0) > 0,
                "inventory_level": product.get("inventory", 0),
                "status": (
                    "available"
                    if product.get("inventory", 0) > 10
                    else "low_stock" if product.get("inventory", 0) > 0 else "out_of_stock"
                ),
            },
        }

    # ========== バッチ操作 ==========

    @app.post("/users/batch")
    def batch_create_users(request):
        """ユーザーの一括作成"""
        data = request.json()
        users_data = data.get("users", [])

        if not users_data or len(users_data) > 100:
            raise ValidationError("Must provide 1-100 users for batch creation")

        results = {"created": [], "errors": [], "summary": {"success": 0, "failed": 0}}

        for i, user_data in enumerate(users_data):
            try:
                # 簡単なバリデーション
                if not user_data.get("name") or not user_data.get("email"):
                    raise ValueError("Name and email are required")

                # ユーザー作成
                import uuid

                user_id = str(uuid.uuid4())
                user = {
                    "id": user_id,
                    "name": user_data["name"],
                    "email": user_data["email"],
                    "age": user_data.get("age", 0),
                    "role": user_data.get("role", "user"),
                    "created_at": datetime.now().isoformat(),
                }

                USERS_DB[user_id] = user
                results["created"].append(user)
                results["summary"]["success"] += 1

            except Exception as e:
                results["errors"].append({"index": i, "data": user_data, "error": str(e)})
                results["summary"]["failed"] += 1

        status_code = 201 if results["summary"]["success"] > 0 else 400

        return Response(results, status_code=status_code)

    # ========== エラーハンドリング ==========

    @app.error_handler(ValidationError)
    def handle_validation_error(error, request, context):
        """バリデーションエラーの詳細処理"""
        logger.warning(f"Validation error: {error}")

        return Response(
            {
                "error": "VALIDATION_ERROR",
                "message": str(error),
                "details": getattr(error, "details", None),
                "field": getattr(error, "field", None),
                "value": getattr(error, "value", None),
                "request_id": context.aws_request_id,
                "timestamp": datetime.now().isoformat(),
            },
            status_code=400,
        )

    @app.error_handler(NotFoundError)
    def handle_not_found_error(error, request, context):
        """リソース未発見エラーの処理"""
        logger.info(f"Resource not found: {error}")

        return Response(
            {
                "error": "NOT_FOUND",
                "message": str(error),
                "request_id": context.aws_request_id,
                "timestamp": datetime.now().isoformat(),
            },
            status_code=404,
        )

    @app.default_error_handler
    def handle_general_error(error, request, context):
        """一般的なエラーの処理"""
        logger.error(f"Unhandled error: {error}", exc_info=True)

        # 本番環境では詳細なエラー情報を隠す
        if os.getenv("ENVIRONMENT") == "production":
            return Response(
                {
                    "error": "INTERNAL_ERROR",
                    "message": "An internal error occurred",
                    "request_id": context.aws_request_id,
                    "timestamp": datetime.now().isoformat(),
                },
                status_code=500,
            )
        else:
            return Response(
                {
                    "error": "INTERNAL_ERROR",
                    "message": str(error),
                    "type": type(error).__name__,
                    "request_id": context.aws_request_id,
                    "timestamp": datetime.now().isoformat(),
                },
                status_code=500,
            )

    return app


# Lambda ハンドラー
lambda_handler = create_lambda_handler(create_app)

# ローカルテスト用
if __name__ == "__main__":
    # テストイベント
    test_events = [
        {"httpMethod": "GET", "path": "/", "headers": {}, "body": None},
        {"httpMethod": "GET", "path": "/health", "headers": {}, "body": None},
        {
            "httpMethod": "GET",
            "path": "/users",
            "queryStringParameters": {"limit": "10", "role": "admin"},
            "headers": {},
            "body": None,
        },
        {
            "httpMethod": "GET",
            "path": "/products",
            "queryStringParameters": {"category": "widgets", "in_stock": "true"},
            "headers": {},
            "body": None,
        },
    ]

    # コンテキストモック
    context = type(
        "Context",
        (),
        {
            "aws_request_id": "test-request-id",
            "function_name": "test-lambapi-container",
            "memory_limit_in_mb": "512",
            "get_remaining_time_in_millis": lambda: 25000,
        },
    )()

    # テスト実行
    for i, event in enumerate(test_events, 1):
        print(f"\n{'=' * 60}")
        print(f"テスト {i}: {event['httpMethod']} {event['path']}")
        if event.get("queryStringParameters"):
            print(f"Query: {event['queryStringParameters']}")
        print("=" * 60)

        result = lambda_handler(event, context)
        print(f"ステータス: {result['statusCode']}")

        try:
            body = json.loads(result["body"])
            print(f"レスポンス: {json.dumps(body, indent=2, ensure_ascii=False)}")
        except (json.JSONDecodeError, KeyError):
            print(f"レスポンス: {result['body']}")
