"""
lambapi

モダンな AWS Lambda 用 API フレームワーク

使用例:
    from lambda_api import API, Response, create_lambda_handler

    def create_app(event, context):
        app = API(event, context)

        @app.get("/")
        def hello_world():
            return {"message": "Hello lambapi!"}

        return app

    lambda_handler = create_lambda_handler(create_app)
"""

from .core import API, Route
from .request import Request
from .response import Response
from .utils import create_lambda_handler
from .validation import validate_and_convert, convert_to_dict
from .router import Router
from .base_router import BaseRouterMixin
from .cors import CORSConfig, create_cors_config
from .dependencies import Query, Path, Body, Authenticated
from .exceptions import (
    APIError,
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
from .error_handlers import error_handler, default_error_handler, ErrorHandler
from .dev_tools import serve

# 認証機能（オプション）
try:
    from .auth import DynamoDBAuth

    _AUTH_AVAILABLE = True
except ImportError:
    _AUTH_AVAILABLE = False
    DynamoDBAuth = None  # type: ignore

__version__ = "0.2.17"
__author__ = "Your Name"
__email__ = "your.email@example.com"

__all__ = [
    "API",
    "Route",
    "Router",
    "BaseRouterMixin",
    "Request",
    "Response",
    "create_lambda_handler",
    "validate_and_convert",
    "convert_to_dict",
    "CORSConfig",
    "create_cors_config",
    "Query",
    "Path",
    "Body",
    "Authenticated",
    "APIError",
    "ValidationError",
    "NotFoundError",
    "AuthenticationError",
    "AuthorizationError",
    "ConflictError",
    "RateLimitError",
    "TimeoutError",
    "InternalServerError",
    "ServiceUnavailableError",
    "error_handler",
    "default_error_handler",
    "ErrorHandler",
    "serve",
]

# 認証機能が利用可能な場合のみ追加
if _AUTH_AVAILABLE:
    __all__.extend(["DynamoDBAuth"])
