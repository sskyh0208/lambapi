"""
構造化エラーハンドリングの使用例

この例では、統一されたエラーレスポンス形式とカスタム例外の使用方法を紹介します。
"""

import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lambapi import (
    API,
    Response,
    create_lambda_handler,
    ValidationError,
    NotFoundError,
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    RateLimitError,
    TimeoutError,
    InternalServerError,
    ServiceUnavailableError,
    error_handler,
    default_error_handler,
)


def create_app(event, context):
    """エラーハンドリング機能を使ったアプリケーション作成関数"""
    app = API(event, context)

    # CORS 設定
    app.enable_cors()

    # ===== 基本的なエラー例 =====

    @app.get("/users/{user_id}")
    def get_user(user_id: str):
        """ユーザー取得エンドポイント"""
        # バリデーション
        if not user_id.isdigit():
            raise ValidationError("User ID must be numeric", field="user_id", value=user_id)

        user_id_int = int(user_id)
        if user_id_int <= 0:
            raise ValidationError("User ID must be positive", field="user_id", value=user_id_int)

        # 存在チェック
        if user_id_int > 1000:
            raise NotFoundError("User", user_id_int)

        return {
            "id": user_id_int,
            "name": f"User {user_id_int}",
            "email": f"user{user_id_int}@example.com",
        }

    @app.post("/users")
    def create_user(request):
        """ユーザー作成エンドポイント"""
        try:
            user_data = request.json()
        except Exception:
            raise ValidationError("Invalid JSON format")

        # 必須フィールドチェック
        if not user_data.get("name"):
            raise ValidationError("Name is required", field="name")

        if not user_data.get("email"):
            raise ValidationError("Email is required", field="email")

        # メール形式チェック
        email = user_data["email"]
        if "@" not in email:
            raise ValidationError("Invalid email format", field="email", value=email)

        # 重複チェック（例）
        if email == "admin@example.com":
            raise ConflictError("Email already exists", resource="user", details={"email": email})

        return Response(
            {
                "message": "User created successfully",
                "user": {"id": 123, "name": user_data["name"], "email": email},
            },
            status_code=201,
        )

    # ===== 認証・認可エラー例 =====

    @app.get("/admin/dashboard")
    def admin_dashboard(request):
        """管理者ダッシュボード"""
        # 認証チェック
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            raise AuthenticationError("Authorization header required")

        if not auth_header.startswith("Bearer "):
            raise AuthenticationError("Bearer token required")

        token = auth_header[7:]  # "Bearer " を除去

        # トークン検証（例）
        if token != "valid-admin-token":  # nosec B105
            raise AuthenticationError("Invalid token")

        # 権限チェック（例）
        if token == "user-token":  # nosec B105
            raise AuthorizationError(
                "Admin privileges required", resource="dashboard", action="read"
            )

        return {
            "message": "Admin dashboard",
            "stats": {"users": 1000, "orders": 5000, "revenue": 100000},
        }

    # ===== レート制限エラー例 =====

    # 簡易レート制限カウンター（実際には Redis などを使用）
    _rate_limit_counter = {}

    @app.get("/api/data")
    def get_api_data(request):
        """レート制限付き API エンドポイント"""
        # クライアント識別（実際には IP アドレスや API キーを使用）
        client_id = request.headers.get("X-Client-ID", "anonymous")

        # レート制限チェック
        current_count = _rate_limit_counter.get(client_id, 0)
        if current_count >= 5:  # 5 回まで
            raise RateLimitError(
                "API rate limit exceeded", retry_after=60, details={"limit": 5, "window": 60}
            )

        _rate_limit_counter[client_id] = current_count + 1

        return {
            "data": "API response data",
            "remaining_requests": 5 - _rate_limit_counter[client_id],
        }

    # ===== タイムアウトエラー例 =====

    @app.get("/slow-operation")
    def slow_operation(request, context):
        """時間のかかる処理のシミュレーション"""
        import time

        # 残り時間チェック
        remaining_time = context.get_remaining_time_in_millis()
        if remaining_time < 5000:  # 5 秒未満の場合
            raise TimeoutError(
                "Insufficient time to complete operation",
                timeout_seconds=5.0,
                details={"remaining_time_ms": remaining_time},
            )

        # 実際の処理（シミュレーション）
        # time.sleep(2)  # 実際にはデータベースアクセスなど

        return {"message": "Operation completed", "duration": "2 seconds"}

    # ===== サービス利用不可エラー例 =====

    @app.get("/external-service")
    def external_service():
        """外部サービス連携"""
        # 外部サービスの状態チェック（例）
        service_available = False  # 実際にはヘルスチェック API を呼び出し

        if not service_available:
            raise ServiceUnavailableError(
                "External service temporarily unavailable",
                retry_after=300,
                details={"service": "payment-gateway"},
            )

        return {"message": "External service response"}

    # ===== 内部サーバーエラー例 =====

    @app.get("/database-operation")
    def database_operation():
        """データベース操作"""
        try:
            # データベース接続（例）
            database_connected = False  # 実際にはデータベース接続を試行
            if not database_connected:
                raise Exception("Database connection failed")

            return {"data": "Database query result"}

        except Exception as e:
            raise InternalServerError(
                "Database operation failed", details={"error": str(e), "operation": "SELECT"}
            )

    # ===== カスタムエラーハンドラー例 =====

    class BusinessLogicError(Exception):
        """ビジネスロジック関連のカスタムエラー"""

        def __init__(self, message: str, business_code: str):
            self.message = message
            self.business_code = business_code
            super().__init__(message)

    @app.error_handler(BusinessLogicError)
    def handle_business_error(error, request, context):
        """ビジネスロジックエラーのカスタムハンドラー"""
        return Response(
            {
                "error": "BUSINESS_LOGIC_ERROR",
                "message": error.message,
                "business_code": error.business_code,
                "request_id": context.aws_request_id,
                "timestamp": "2024-01-01T12:00:00Z",
            },
            status_code=422,
        )  # Unprocessable Entity

    @app.get("/business-operation")
    def business_operation():
        """ビジネスロジック処理"""
        # ビジネスルールチェック
        business_condition = False  # 例：在庫切れ、残高不足など

        if not business_condition:
            raise BusinessLogicError("Insufficient inventory", business_code="INV001")

        return {"message": "Business operation completed"}

    # ===== デフォルトエラーハンドラーのカスタマイズ =====

    @app.default_error_handler
    def custom_default_handler(error, request, context):
        """カスタムデフォルトエラーハンドラー"""
        return Response(
            {
                "error": "UNEXPECTED_ERROR",
                "message": "An unexpected error occurred",
                "error_type": type(error).__name__,
                "request_id": context.aws_request_id,
                "support_message": "Please contact support with this request ID",
            },
            status_code=500,
        )

    @app.get("/unexpected-error")
    def unexpected_error():
        """予期しないエラーの例"""
        # 予期しないエラー
        raise ValueError("This is an unexpected error")

    # ===== エラーテスト用エンドポイント =====

    @app.get("/error-demo/{error_type}")
    def error_demo(error_type: str):
        """エラーデモ用エンドポイント"""
        error_map = {
            "validation": lambda: ValidationError("Demo validation error", field="demo"),
            "not_found": lambda: NotFoundError("DemoResource", "123"),
            "auth": lambda: AuthenticationError("Demo auth error"),
            "forbidden": lambda: AuthorizationError("Demo authorization error"),
            "conflict": lambda: ConflictError("Demo conflict error"),
            "rate_limit": lambda: RateLimitError("Demo rate limit", retry_after=30),
            "timeout": lambda: TimeoutError("Demo timeout"),
            "internal": lambda: InternalServerError("Demo internal error"),
            "unavailable": lambda: ServiceUnavailableError("Demo service unavailable"),
        }

        if error_type not in error_map:
            raise ValidationError("Invalid error type", field="error_type", value=error_type)

        raise error_map[error_type]()

    return app


# Lambda 関数のエントリーポイント
lambda_handler = create_lambda_handler(create_app)


# ローカルテスト用コード
if __name__ == "__main__":
    print("=== 構造化エラーハンドリングのテスト ===\n")

    # テストケース 1: ValidationError
    test_event_1 = {
        "httpMethod": "GET",
        "path": "/users/abc",
        "queryStringParameters": None,
        "headers": {"Content-Type": "application/json"},
        "body": None,
    }

    print("1. ValidationError テスト:")
    result1 = lambda_handler(test_event_1, None)
    print(f"Status: {result1['statusCode']}")
    print(f"Response: {result1['body']}\n")

    # テストケース 2: NotFoundError
    test_event_2 = {
        "httpMethod": "GET",
        "path": "/users/9999",
        "queryStringParameters": None,
        "headers": {"Content-Type": "application/json"},
        "body": None,
    }

    print("2. NotFoundError テスト:")
    result2 = lambda_handler(test_event_2, None)
    print(f"Status: {result2['statusCode']}")
    print(f"Response: {result2['body']}\n")

    # テストケース 3: AuthenticationError
    test_event_3 = {
        "httpMethod": "GET",
        "path": "/admin/dashboard",
        "queryStringParameters": None,
        "headers": {"Content-Type": "application/json"},
        "body": None,
    }

    print("3. AuthenticationError テスト:")
    result3 = lambda_handler(test_event_3, None)
    print(f"Status: {result3['statusCode']}")
    print(f"Headers: {result3['headers']}")
    print(f"Response: {result3['body']}\n")

    # テストケース 4: ConflictError
    test_event_4 = {
        "httpMethod": "POST",
        "path": "/users",
        "queryStringParameters": None,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"name": "Admin User", "email": "admin@example.com"}),
    }

    print("4. ConflictError テスト:")
    result4 = lambda_handler(test_event_4, None)
    print(f"Status: {result4['statusCode']}")
    print(f"Response: {result4['body']}\n")

    # テストケース 5: RateLimitError
    test_event_5 = {
        "httpMethod": "GET",
        "path": "/api/data",
        "queryStringParameters": None,
        "headers": {"Content-Type": "application/json", "X-Client-ID": "test-client"},
        "body": None,
    }

    print("5. RateLimitError テスト (6 回呼び出し):")
    for i in range(6):
        result5 = lambda_handler(test_event_5, None)
        print(f"Call {i + 1}: Status {result5['statusCode']}")
        if result5["statusCode"] == 429:
            print(f"Rate limited: {result5['body']}")
            break
    print()

    # テストケース 6: カスタムエラーハンドラー
    test_event_6 = {
        "httpMethod": "GET",
        "path": "/business-operation",
        "queryStringParameters": None,
        "headers": {"Content-Type": "application/json"},
        "body": None,
    }

    print("6. カスタムエラーハンドラー テスト:")
    result6 = lambda_handler(test_event_6, None)
    print(f"Status: {result6['statusCode']}")
    print(f"Response: {result6['body']}\n")

    # テストケース 7: エラーデモ
    error_types = ["validation", "not_found", "auth", "rate_limit"]
    print("7. エラーデモ:")
    for error_type in error_types:
        test_event = {
            "httpMethod": "GET",
            "path": f"/error-demo/{error_type}",
            "queryStringParameters": None,
            "headers": {"Content-Type": "application/json"},
            "body": None,
        }
        result = lambda_handler(test_event, None)
        print(f"  {error_type}: Status {result['statusCode']}")

    print("\n=== エラーハンドリングテスト完了 ===")
    print("\\n 特徴:")
    print("✅ 統一されたエラーレスポンス形式")
    print("✅ 適切な HTTP ステータスコード")
    print("✅ 詳細なエラー情報（フィールド、値など）")
    print("✅ リクエスト ID による追跡")
    print("✅ カスタムエラーハンドラー対応")
    print("✅ CORS ヘッダー自動追加")
