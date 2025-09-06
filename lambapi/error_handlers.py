"""
エラーハンドラーシステム

カスタム例外に対するエラーハンドラーの登録と実行を管理します。
"""

from typing import Dict, Type, Callable, Any, Optional
from .exceptions import APIError, create_error_response
from .response import Response
from .request import Request


# エラーハンドラーの型定義
ErrorHandlerFunc = Callable[[Exception, Request, Any], Response]
DefaultErrorHandlerFunc = Callable[[Exception, Request, Any], Response]


class ErrorHandlerRegistry:
    """エラーハンドラーの登録・管理クラス"""

    def __init__(self) -> None:
        self._handlers: Dict[Type[Exception], ErrorHandlerFunc] = {}
        self._default_handler: Optional[DefaultErrorHandlerFunc] = None

    def register(self, exception_type: Type[Exception], handler: ErrorHandlerFunc) -> None:
        """エラーハンドラーを登録"""
        self._handlers[exception_type] = handler

    def set_default_handler(self, handler: DefaultErrorHandlerFunc) -> None:
        """デフォルトエラーハンドラーを設定"""
        self._default_handler = handler

    def handle_error(self, error: Exception, request: Request, context: Any) -> Response:
        """エラーを適切なハンドラーで処理"""
        # 登録されたハンドラーを検索
        for exception_type, handler in self._handlers.items():
            if isinstance(error, exception_type):
                return handler(error, request, context)

        # APIError の場合は自動処理
        if isinstance(error, APIError):
            return self._handle_api_error(error, request, context)

        # デフォルトハンドラーがある場合
        if self._default_handler:
            return self._default_handler(error, request, context)

        # 最終的なフォールバック
        return self._handle_unknown_error(error, request, context)

    def _handle_api_error(self, error: APIError, request: Request, context: Any) -> Response:
        """APIError の自動処理"""
        request_id = context.aws_request_id if context else None
        error_response = create_error_response(error, request_id)

        return Response(
            error_response,
            status_code=error.status_code,
            headers={"Content-Type": "application/json"},
        )

    def _handle_unknown_error(
        self, error: Exception, request: Optional[Request], context: Any
    ) -> Response:
        """未知のエラーの処理"""
        request_id = context.aws_request_id if context else None

        error_response = {
            "error": "INTERNAL_ERROR",
            "message": "An unexpected error occurred",
            "status_code": 500,
        }

        if request_id:
            error_response["request_id"] = request_id

        return Response(
            error_response, status_code=500, headers={"Content-Type": "application/json"}
        )


class ErrorHandler:
    """エラーハンドラークラス（デコレータ用）"""

    def __init__(self) -> None:
        self._registry = ErrorHandlerRegistry()

    def catch(self, exception_type: Type[Exception]) -> Callable:
        """エラーハンドラーデコレータ"""

        def decorator(handler_func: Callable) -> Callable:
            self._registry.register(exception_type, handler_func)
            return handler_func

        return decorator

    def default(self, handler_func: Callable) -> Callable:
        """デフォルトエラーハンドラーデコレータ"""
        self._registry.set_default_handler(handler_func)
        return handler_func

    def handle_error(self, error: Exception, request: Request, context: Any) -> Response:
        """エラーを処理"""
        return self._registry.handle_error(error, request, context)


# グローバルなエラーハンドラーレジストリ
_global_registry = ErrorHandlerRegistry()


def error_handler(
    exception_type: Type[Exception],
) -> Callable[[ErrorHandlerFunc], ErrorHandlerFunc]:
    """エラーハンドラーデコレータ"""

    def decorator(handler_func: ErrorHandlerFunc) -> ErrorHandlerFunc:
        _global_registry.register(exception_type, handler_func)
        return handler_func

    return decorator


def default_error_handler(handler_func: DefaultErrorHandlerFunc) -> DefaultErrorHandlerFunc:
    """デフォルトエラーハンドラーデコレータ"""
    _global_registry.set_default_handler(handler_func)
    return handler_func


def get_global_registry() -> ErrorHandlerRegistry:
    """グローバルエラーハンドラーレジストリを取得"""
    return _global_registry


# 便利なデフォルトハンドラー
def create_default_handlers() -> None:
    """デフォルトのエラーハンドラーを作成"""
    from .exceptions import (
        ValidationError,
        NotFoundError,
        AuthenticationError,
        RateLimitError,
        ServiceUnavailableError,
    )

    @error_handler(ValidationError)
    def handle_validation_error(error: Exception, request: Request, context: Any) -> Response:
        """バリデーションエラーハンドラー"""
        if isinstance(error, ValidationError):
            validation_error = error
        else:
            validation_error = ValidationError("Invalid validation error")

        request_id = context.aws_request_id if context else None

        response_data: Dict[str, Any] = {
            "error": validation_error.error_code,
            "message": validation_error.message,
            "status_code": validation_error.status_code,
        }

        # フィールド情報があれば追加
        if validation_error.details and "field" in validation_error.details:
            response_data["field"] = validation_error.details["field"]

        # バリデーション値があれば追加（センシティブでない場合のみ）
        if validation_error.details and "value" in validation_error.details:
            field_name = validation_error.details.get("field")
            if field_name and not _is_sensitive_field(str(field_name)):
                response_data["value"] = validation_error.details["value"]

        if validation_error.details:
            response_data["details"] = validation_error.details

        if request_id:
            response_data["request_id"] = request_id

        return Response(response_data, status_code=validation_error.status_code)

    @error_handler(NotFoundError)
    def handle_not_found_error(error: Exception, request: Request, context: Any) -> Response:
        """Not Found エラーハンドラー"""
        if isinstance(error, NotFoundError):
            not_found_error = error
        else:
            not_found_error = NotFoundError("Resource not found")

        request_id = context.aws_request_id if context else None

        response_data: Dict[str, Any] = {
            "error": not_found_error.error_code,
            "message": not_found_error.message,
            "status_code": not_found_error.status_code,
        }

        if not_found_error.details:
            response_data["details"] = not_found_error.details

        if request_id:
            response_data["request_id"] = request_id

        return Response(response_data, status_code=not_found_error.status_code)

    @error_handler(AuthenticationError)
    def handle_auth_error(error: Exception, request: Request, context: Any) -> Response:
        """認証エラーハンドラー"""
        if isinstance(error, AuthenticationError):
            auth_error = error
        else:
            auth_error = AuthenticationError("Authentication failed")

        request_id = context.aws_request_id if context else None

        response_data: Dict[str, Any] = {
            "error": auth_error.error_code,
            "message": auth_error.message,
            "status_code": auth_error.status_code,
        }

        if request_id:
            response_data["request_id"] = request_id

        # WWW-Authenticate ヘッダーを追加
        headers = {"Content-Type": "application/json", "WWW-Authenticate": "Bearer"}

        return Response(response_data, status_code=auth_error.status_code, headers=headers)

    @error_handler(RateLimitError)
    def handle_rate_limit_error(error: Exception, request: Request, context: Any) -> Response:
        """レート制限エラーハンドラー"""
        if isinstance(error, RateLimitError):
            rate_limit_error = error
        else:
            rate_limit_error = RateLimitError("Rate limit exceeded")

        request_id = context.aws_request_id if context else None

        response_data: Dict[str, Any] = {
            "error": rate_limit_error.error_code,
            "message": rate_limit_error.message,
            "status_code": rate_limit_error.status_code,
        }

        if request_id:
            response_data["request_id"] = request_id

        # Retry-After ヘッダーを追加
        headers = {"Content-Type": "application/json"}
        if rate_limit_error.details and "retry_after" in rate_limit_error.details:
            headers["Retry-After"] = str(rate_limit_error.details["retry_after"])

        return Response(response_data, status_code=rate_limit_error.status_code, headers=headers)

    @error_handler(ServiceUnavailableError)
    def handle_service_unavailable_error(
        error: Exception, request: Request, context: Any
    ) -> Response:
        """サービス利用不可エラーハンドラー"""
        if isinstance(error, ServiceUnavailableError):
            service_error = error
        else:
            service_error = ServiceUnavailableError("Service unavailable")

        request_id = context.aws_request_id if context else None

        response_data: Dict[str, Any] = {
            "error": service_error.error_code,
            "message": service_error.message,
            "status_code": service_error.status_code,
        }

        if request_id:
            response_data["request_id"] = request_id

        # Retry-After ヘッダーを追加
        headers = {"Content-Type": "application/json"}
        if service_error.details and "retry_after" in service_error.details:
            headers["Retry-After"] = str(service_error.details["retry_after"])

        return Response(response_data, status_code=service_error.status_code, headers=headers)

    @default_error_handler
    def handle_unknown_error(error: Exception, request: Request, context: Any) -> Response:
        """未知のエラーのデフォルトハンドラー"""
        request_id = context.aws_request_id if context else None

        # デバッグ情報（本番環境では削除することを推奨）
        error_details = {"type": type(error).__name__, "message": str(error)}

        response_data = {
            "error": "INTERNAL_ERROR",
            "message": "An unexpected error occurred",
            "status_code": 500,
            "details": error_details,
        }

        if request_id:
            response_data["request_id"] = request_id

        return Response(response_data, status_code=500)


def _is_sensitive_field(field_name: str) -> bool:
    """センシティブなフィールドかどうかを判定"""
    if not field_name:
        return False

    sensitive_fields = {
        "password",
        "passwd",
        "pwd",
        "secret",
        "token",
        "key",
        "authorization",
        "auth",
        "credential",
        "cred",
        "api_key",
        "access_token",
        "refresh_token",
        "session",
        "cookie",
    }

    field_lower = field_name.lower()
    return any(sensitive in field_lower for sensitive in sensitive_fields)


# 初期化時にデフォルトハンドラーを設定
create_default_handlers()
