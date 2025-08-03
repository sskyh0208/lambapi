"""
Base Router クラス

HTTP メソッドデコレータの共通実装を提供します。
"""

from typing import Callable, Optional, Type, Union, Any
from .cors import CORSConfig


class BaseRouterMixin:
    """HTTP メソッドデコレータの共通実装"""

    def _add_route(
        self,
        path: str,
        method: str,
        handler: Callable[..., Any],
        request_format: Optional[Type[Any]] = None,
        response_format: Optional[Type[Any]] = None,
        cors: Union[bool, CORSConfig, None] = None,
    ) -> Any:
        """サブクラスで実装する必要があるメソッド"""
        raise NotImplementedError("Subclasses must implement _add_route method")

    def get(
        self,
        path: str = "/",
        request_format: Optional[Type[Any]] = None,
        response_format: Optional[Type[Any]] = None,
        cors: Union[bool, CORSConfig, None] = None,
    ) -> Callable[[Callable[..., Any]], Any]:
        """GET エンドポイントのデコレータ"""

        def decorator(handler: Callable[..., Any]) -> Any:
            return self._add_route(path, "GET", handler, request_format, response_format, cors)

        return decorator

    def post(
        self,
        path: str = "/",
        request_format: Optional[Type[Any]] = None,
        response_format: Optional[Type[Any]] = None,
        cors: Union[bool, CORSConfig, None] = None,
    ) -> Callable[[Callable[..., Any]], Any]:
        """POST エンドポイントのデコレータ"""

        def decorator(handler: Callable[..., Any]) -> Any:
            return self._add_route(path, "POST", handler, request_format, response_format, cors)

        return decorator

    def put(
        self,
        path: str = "/",
        request_format: Optional[Type[Any]] = None,
        response_format: Optional[Type[Any]] = None,
        cors: Union[bool, CORSConfig, None] = None,
    ) -> Callable[[Callable[..., Any]], Any]:
        """PUT エンドポイントのデコレータ"""

        def decorator(handler: Callable[..., Any]) -> Any:
            return self._add_route(path, "PUT", handler, request_format, response_format, cors)

        return decorator

    def delete(
        self,
        path: str = "/",
        request_format: Optional[Type[Any]] = None,
        response_format: Optional[Type[Any]] = None,
        cors: Union[bool, CORSConfig, None] = None,
    ) -> Callable[[Callable[..., Any]], Any]:
        """DELETE エンドポイントのデコレータ"""

        def decorator(handler: Callable[..., Any]) -> Any:
            return self._add_route(path, "DELETE", handler, request_format, response_format, cors)

        return decorator

    def patch(
        self,
        path: str = "/",
        request_format: Optional[Type[Any]] = None,
        response_format: Optional[Type[Any]] = None,
        cors: Union[bool, CORSConfig, None] = None,
    ) -> Callable[[Callable[..., Any]], Any]:
        """PATCH エンドポイントのデコレータ"""

        def decorator(handler: Callable[..., Any]) -> Any:
            return self._add_route(path, "PATCH", handler, request_format, response_format, cors)

        return decorator
