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
from .error_handlers import error_handler, default_error_handler
from .dev_tools import serve

__version__ = "0.1.4"
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
    "serve",
]
