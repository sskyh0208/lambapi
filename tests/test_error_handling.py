"""
エラーハンドリング機能のテスト
"""

import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lambapi import (
    API,
    Response,
    ValidationError,
    NotFoundError,
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    RateLimitError,
    TimeoutError,
    InternalServerError,
    ServiceUnavailableError,
)


class TestErrorHandling:
    """エラーハンドリング機能のテスト"""

    def create_test_event(self, method="GET", path="/", query_params=None, body=None, headers=None):
        """テスト用のイベントを作成"""
        default_headers = {"Content-Type": "application/json"}
        if headers:
            default_headers.update(headers)

        return {
            "httpMethod": method,
            "path": path,
            "queryStringParameters": query_params,
            "headers": default_headers,
            "body": body,
        }

    def create_test_context(self):
        """テスト用のコンテキストを作成"""

        class MockContext:
            aws_request_id = "test-request-123"
            function_name = "test-function"

        return MockContext()

    def test_validation_error(self):
        """ValidationError のテスト"""
        event = self.create_test_event(path="/users", method="POST")
        context = self.create_test_context()
        app = API(event, context)

        @app.post("/users")
        def create_user():
            raise ValidationError("Email is required", field="email", value="")

        result = app.handle_request()

        assert result["statusCode"] == 400
        body = json.loads(result["body"])
        assert body["error"] == "VALIDATION_ERROR"
        assert body["message"] == "Email is required"
        assert body["field"] == "email"
        assert body["request_id"] == "test-request-123"

    def test_not_found_error(self):
        """NotFoundError のテスト"""
        event = self.create_test_event(path="/users/123")
        context = self.create_test_context()
        app = API(event, context)

        @app.get("/users/{user_id}")
        def get_user(user_id: str):
            raise NotFoundError("User", user_id)

        result = app.handle_request()

        assert result["statusCode"] == 404
        body = json.loads(result["body"])
        assert body["error"] == "NOT_FOUND"
        assert body["message"] == "User not found (ID: 123)"
        assert body["details"]["resource"] == "User"
        assert body["details"]["id"] == "123"

    def test_authentication_error(self):
        """AuthenticationError のテスト"""
        event = self.create_test_event(path="/admin")
        context = self.create_test_context()
        app = API(event, context)

        @app.get("/admin")
        def admin_panel():
            raise AuthenticationError("Token required")

        result = app.handle_request()

        assert result["statusCode"] == 401
        assert result["headers"]["WWW-Authenticate"] == "Bearer"
        body = json.loads(result["body"])
        assert body["error"] == "AUTH_REQUIRED"
        assert body["message"] == "Token required"

    def test_authorization_error(self):
        """AuthorizationError のテスト"""
        event = self.create_test_event(path="/admin/users")
        context = self.create_test_context()
        app = API(event, context)

        @app.get("/admin/users")
        def admin_users():
            raise AuthorizationError("Admin privileges required", resource="users", action="read")

        result = app.handle_request()

        assert result["statusCode"] == 403
        body = json.loads(result["body"])
        assert body["error"] == "ACCESS_DENIED"
        assert body["message"] == "Admin privileges required"
        assert body["details"]["resource"] == "users"
        assert body["details"]["action"] == "read"

    def test_conflict_error(self):
        """ConflictError のテスト"""
        event = self.create_test_event(path="/users", method="POST")
        context = self.create_test_context()
        app = API(event, context)

        @app.post("/users")
        def create_user():
            raise ConflictError("Email already exists", resource="user")

        result = app.handle_request()

        assert result["statusCode"] == 409
        body = json.loads(result["body"])
        assert body["error"] == "CONFLICT"
        assert body["message"] == "Email already exists"
        assert body["details"]["resource"] == "user"

    def test_rate_limit_error(self):
        """RateLimitError のテスト"""
        event = self.create_test_event(path="/api/data")
        context = self.create_test_context()
        app = API(event, context)

        @app.get("/api/data")
        def get_data():
            raise RateLimitError("Too many requests", retry_after=60)

        result = app.handle_request()

        assert result["statusCode"] == 429
        assert result["headers"]["Retry-After"] == "60"
        body = json.loads(result["body"])
        assert body["error"] == "RATE_LIMIT_EXCEEDED"
        assert body["message"] == "Too many requests"

    def test_timeout_error(self):
        """TimeoutError のテスト"""
        event = self.create_test_event(path="/slow-operation")
        context = self.create_test_context()
        app = API(event, context)

        @app.get("/slow-operation")
        def slow_operation():
            raise TimeoutError("Operation timed out", timeout_seconds=30.0)

        result = app.handle_request()

        assert result["statusCode"] == 408
        body = json.loads(result["body"])
        assert body["error"] == "TIMEOUT"
        assert body["message"] == "Operation timed out"
        assert body["details"]["timeout_seconds"] == 30.0

    def test_internal_server_error(self):
        """InternalServerError のテスト"""
        event = self.create_test_event(path="/error")
        context = self.create_test_context()
        app = API(event, context)

        @app.get("/error")
        def error_endpoint():
            raise InternalServerError("Database connection failed")

        result = app.handle_request()

        assert result["statusCode"] == 500
        body = json.loads(result["body"])
        assert body["error"] == "INTERNAL_ERROR"
        assert body["message"] == "Database connection failed"

    def test_service_unavailable_error(self):
        """ServiceUnavailableError のテスト"""
        event = self.create_test_event(path="/service")
        context = self.create_test_context()
        app = API(event, context)

        @app.get("/service")
        def service_endpoint():
            raise ServiceUnavailableError("Service maintenance", retry_after=300)

        result = app.handle_request()

        assert result["statusCode"] == 503
        assert result["headers"]["Retry-After"] == "300"
        body = json.loads(result["body"])
        assert body["error"] == "SERVICE_UNAVAILABLE"
        assert body["message"] == "Service maintenance"

    def test_custom_error_handler(self):
        """カスタムエラーハンドラーのテスト"""
        event = self.create_test_event(path="/custom-error")
        context = self.create_test_context()
        app = API(event, context)

        class CustomError(Exception):
            pass

        from lambapi import ErrorHandler

        custom_error_handler = ErrorHandler()

        @custom_error_handler.catch(CustomError)
        def handle_custom_error(error, request, context):
            return Response(
                {
                    "error": "CUSTOM_ERROR",
                    "message": "This is a custom error",
                    "custom_field": "custom_value",
                },
                status_code=418,
            )  # I'm a teapot

        app.add_error_handler(custom_error_handler)

        @app.get("/custom-error")
        def custom_error_endpoint():
            raise CustomError("Custom error message")

        result = app.handle_request()

        assert result["statusCode"] == 418
        body = json.loads(result["body"])
        assert body["error"] == "CUSTOM_ERROR"
        assert body["message"] == "This is a custom error"
        assert body["custom_field"] == "custom_value"

    def test_default_error_handler(self):
        """デフォルトエラーハンドラーのテスト"""
        event = self.create_test_event(path="/unknown-error")
        context = self.create_test_context()
        app = API(event, context)

        @app.get("/unknown-error")
        def unknown_error_endpoint():
            raise ValueError("Unknown error type")

        result = app.handle_request()

        assert result["statusCode"] == 500
        body = json.loads(result["body"])
        assert body["error"] == "INTERNAL_ERROR"
        assert body["message"] == "An unexpected error occurred"
        assert "ValueError" in body["details"]["type"]

    def test_error_with_cors(self):
        """CORS 有効時のエラーハンドリングテスト"""
        event = self.create_test_event(
            path="/error-with-cors", headers={"Origin": "https://example.com"}
        )
        context = self.create_test_context()
        app = API(event, context)

        app.enable_cors(origins="https://example.com")

        @app.get("/error-with-cors")
        def error_with_cors():
            raise ValidationError("Test error with CORS")

        result = app.handle_request()

        assert result["statusCode"] == 400
        assert result["headers"]["Access-Control-Allow-Origin"] == "https://example.com"
        body = json.loads(result["body"])
        assert body["error"] == "VALIDATION_ERROR"

    def test_multiple_validation_errors(self):
        """複数のバリデーションエラーのテスト"""
        from lambapi.exceptions import format_validation_errors

        errors = [
            ValidationError("Name is required", field="name"),
            ValidationError("Email is required", field="email"),
            ValidationError("Age must be positive", field="age", value=-1),
        ]

        combined_error = format_validation_errors(errors)

        assert combined_error.message == "Multiple validation errors (3 errors)"
        assert combined_error.details["count"] == 3
        assert len(combined_error.details["errors"]) == 3


if __name__ == "__main__":
    # pytest がない環境でも実行できるように直接テストを実行
    test_class = TestErrorHandling()

    tests = [
        test_class.test_validation_error,
        test_class.test_not_found_error,
        test_class.test_authentication_error,
        test_class.test_authorization_error,
        test_class.test_conflict_error,
        test_class.test_rate_limit_error,
        test_class.test_timeout_error,
        test_class.test_internal_server_error,
        test_class.test_service_unavailable_error,
        test_class.test_custom_error_handler,
        test_class.test_default_error_handler,
        test_class.test_error_with_cors,
        test_class.test_multiple_validation_errors,
    ]

    print("Running Error Handling tests...")

    for i, test in enumerate(tests, 1):
        try:
            test()
            print(f"✓ Test {i}: {test.__name__} - PASSED")
        except Exception as e:
            print(f"✗ Test {i}: {test.__name__} - FAILED: {e}")

    print("All Error Handling tests completed!")
