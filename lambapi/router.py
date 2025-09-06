"""
Router クラス

ルーター機能を提供します。
複数のルートをグループ化し、プレフィックスやタグを設定できます。
"""

from typing import Callable, Optional, List, Any, Union

from .core import Route
from .base_router import BaseRouterMixin
from .cors import CORSConfig


class Router(BaseRouterMixin):
    """ルータークラス"""

    def __init__(self, prefix: str = "", tags: Optional[List[str]] = None):
        """
        ルーターを初期化

        Args:
            prefix: すべてのルートに適用されるパスプレフィックス
            tags: ルートに適用されるタグのリスト
        """
        self.prefix = prefix.rstrip("/")  # 末尾のスラッシュを削除
        self.tags = tags or []
        self.routes: List[Route] = []

    def _add_route(
        self,
        path: str,
        method: str,
        handler: Callable,
        cors: Union[bool, CORSConfig, None] = None,
    ) -> Callable:
        """ルートを追加"""
        # プレフィックスを適用
        full_path = f"{self.prefix}{path}" if path != "/" else self.prefix or "/"
        route = Route(full_path, method, handler)
        self.routes.append(route)
        return handler

    def add_router(self, router: Any, prefix: str = "", tags: Optional[List[str]] = None) -> None:
        """他のルーターを統合"""
        if isinstance(router, Router):
            # プレフィックスやタグが指定されている場合は調整
            for route in router.routes:
                new_path = f"{prefix.rstrip('/')}{route.path}" if prefix else route.path
                # 自分のプレフィックスと統合されたプレフィックスを結合
                full_path = f"{self.prefix.rstrip('/')}{new_path}" if self.prefix else new_path
                new_route = Route(
                    full_path,
                    route.method,
                    route.handler,
                )
                self.routes.append(new_route)
