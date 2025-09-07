"""
構造化エラーハンドリング

統一されたエラーレスポンス形式とカスタム例外クラスを提供します。
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass


@dataclass
class APIError(Exception):
    """API エラーの基底クラス"""

    message: str
    status_code: int = 500
    error_code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

    def __post_init__(self) -> None:
        """初期化後の処理"""
        if self.error_code is None:
            self.error_code = f"ERR_{self.status_code}"

        if self.details is None:
            self.details = {}

        # Exception の message を設定
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        result: Dict[str, Any] = {
            "error": self.error_code,
            "message": self.message,
            "status_code": self.status_code,
        }

        if self.details:
            result["details"] = self.details

        return result


class ValidationError(APIError):
    """バリデーションエラー"""

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Any = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        error_details = details or {}
        if field:
            error_details["field"] = field
        if value is not None:
            error_details["value"] = value

        super().__init__(
            message=message, status_code=400, error_code="VALIDATION_ERROR", details=error_details
        )


class NotFoundError(APIError):
    """リソース不存在エラー"""

    def __init__(
        self, resource: str, resource_id: Any = None, details: Optional[Dict[str, Any]] = None
    ):
        message = f"{resource} not found"
        if resource_id is not None:
            message += f" (ID: {resource_id})"

        error_details = details or {}
        error_details["resource"] = resource
        if resource_id is not None:
            error_details["id"] = resource_id

        super().__init__(
            message=message, status_code=404, error_code="NOT_FOUND", details=error_details
        )


class AuthenticationError(APIError):
    """認証エラー"""

    def __init__(
        self, message: str = "Authentication required", details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message, status_code=401, error_code="AUTH_REQUIRED", details=details
        )


class AuthorizationError(APIError):
    """認可エラー"""

    def __init__(
        self,
        message: str = "Access denied",
        resource: Optional[str] = None,
        action: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        error_details = details or {}
        if resource:
            error_details["resource"] = resource
        if action:
            error_details["action"] = action

        super().__init__(
            message=message, status_code=403, error_code="ACCESS_DENIED", details=error_details
        )


class ConflictError(APIError):
    """リソース競合エラー"""

    def __init__(
        self, message: str, resource: Optional[str] = None, details: Optional[Dict[str, Any]] = None
    ):
        error_details = details or {}
        if resource:
            error_details["resource"] = resource

        super().__init__(
            message=message, status_code=409, error_code="CONFLICT", details=error_details
        )


class RateLimitError(APIError):
    """レート制限エラー"""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        error_details = details or {}
        if retry_after:
            error_details["retry_after"] = retry_after

        super().__init__(
            message=message,
            status_code=429,
            error_code="RATE_LIMIT_EXCEEDED",
            details=error_details,
        )


class InternalServerError(APIError):
    """内部サーバーエラー"""

    def __init__(
        self, message: str = "Internal server error", details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message, status_code=500, error_code="INTERNAL_ERROR", details=details
        )


class ServiceUnavailableError(APIError):
    """サービス利用不可エラー"""

    def __init__(
        self,
        message: str = "Service temporarily unavailable",
        retry_after: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        error_details = details or {}
        if retry_after:
            error_details["retry_after"] = retry_after

        super().__init__(
            message=message,
            status_code=503,
            error_code="SERVICE_UNAVAILABLE",
            details=error_details,
        )


class TimeoutError(APIError):
    """タイムアウトエラー"""

    def __init__(
        self,
        message: str = "Request timeout",
        timeout_seconds: Optional[float] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        error_details = details or {}
        if timeout_seconds:
            error_details["timeout_seconds"] = timeout_seconds

        super().__init__(
            message=message, status_code=408, error_code="TIMEOUT", details=error_details
        )


# DynamoDBAuth専用の例外クラス
class AuthConfigError(APIError):
    """認証設定エラー"""

    def __init__(
        self,
        message: str,
        config_type: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        error_details = details or {}
        if config_type:
            error_details["config_type"] = config_type

        super().__init__(
            message=message, status_code=500, error_code="AUTH_CONFIG_ERROR", details=error_details
        )


class ModelValidationError(APIError):
    """モデルバリデーションエラー"""

    def __init__(
        self,
        message: str,
        model_name: Optional[str] = None,
        field_name: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        error_details = details or {}
        if model_name:
            error_details["model_name"] = model_name
        if field_name:
            error_details["field_name"] = field_name

        super().__init__(
            message=message,
            status_code=400,
            error_code="MODEL_VALIDATION_ERROR",
            details=error_details,
        )


class PasswordValidationError(ValidationError):
    """パスワードバリデーションエラー"""

    def __init__(
        self,
        message: str,
        requirement_type: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        error_details = details or {}
        if requirement_type:
            error_details["requirement_type"] = requirement_type

        super().__init__(message=message, field="password", details=error_details)


class FeatureDisabledError(APIError):
    """機能無効化エラー"""

    def __init__(
        self,
        message: str,
        feature_name: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        error_details = details or {}
        if feature_name:
            error_details["feature_name"] = feature_name

        super().__init__(
            message=message, status_code=400, error_code="FEATURE_DISABLED", details=error_details
        )


class RolePermissionError(APIError):
    """権限不足エラー"""

    def __init__(
        self,
        message: str,
        user_role: Optional[str] = None,
        required_roles: Optional[List[str]] = None,
        resource: Optional[str] = None,
        action: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        error_details = details or {}
        if user_role:
            error_details["user_role"] = user_role
        if required_roles:
            error_details["required_roles"] = required_roles
        if resource:
            error_details["resource"] = resource
        if action:
            error_details["action"] = action

        super().__init__(
            message=message, status_code=403, error_code="PERMISSION_DENIED", details=error_details
        )


# 便利な関数
def create_error_response(error: APIError, request_id: Optional[str] = None) -> Dict[str, Any]:
    """エラーレスポンスを作成"""
    response = error.to_dict()

    if request_id:
        response["request_id"] = request_id

    return response


def format_validation_errors(errors: List[ValidationError]) -> ValidationError:
    """複数のバリデーションエラーをまとめる"""
    if len(errors) == 1:
        return errors[0]

    error_details = {"errors": [err.to_dict() for err in errors], "count": len(errors)}

    return ValidationError(
        message=f"Multiple validation errors ({len(errors)} errors)", details=error_details
    )
