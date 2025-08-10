"""
BaseRouterMixin のテスト

lambapi.base_router モジュールの各機能をテストします。
"""

import pytest
from typing import Optional, Type, Union, Any
from unittest.mock import Mock
from lambapi.base_router import BaseRouterMixin
from lambapi.cors import CORSConfig, create_cors_config


class TestBaseRouterMixin:
    """BaseRouterMixin クラスのテスト"""

    def test_base_router_mixin_abstract_method(self):
        """抽象メソッド _add_route の実装要求テスト"""
        mixin = BaseRouterMixin()

        with pytest.raises(
            NotImplementedError, match="Subclasses must implement _add_route method"
        ):
            mixin._add_route("/test", "GET", lambda: None)

    def test_get_decorator_basic(self):
        """GET デコレータの基本テスト"""

        # モック実装クラス
        class MockRouter(BaseRouterMixin):
            def __init__(self):
                self.calls = []

            def _add_route(self, path, method, handler, cors=None):
                self.calls.append((path, method, handler, cors))
                return handler

        router = MockRouter()

        @router.get("/test")
        def test_handler():
            return {"test": True}

        assert len(router.calls) == 1
        call_args = router.calls[0]
        assert call_args[0] == "/test"  # path
        assert call_args[1] == "GET"  # method
        assert call_args[2] == test_handler  # handler
        assert call_args[3] is None  # cors

    def test_get_decorator_with_default_path(self):
        """GET デコレータのデフォルトパステスト"""

        class MockRouter(BaseRouterMixin):
            def __init__(self):
                self.calls = []

            def _add_route(self, path, method, handler, cors=None):
                self.calls.append((path, method, handler, cors))
                return handler

        router = MockRouter()

        @router.get()  # パス指定なし
        def root_handler():
            return {"root": True}

        assert len(router.calls) == 1
        assert router.calls[0][0] == "/"  # デフォルトパス

    def test_get_decorator_with_cors_parameter(self):
        """GET デコレータの CORS パラメータテスト"""
        cors_config = create_cors_config(origins=["https://example.com"])

        class MockRouter(BaseRouterMixin):
            def __init__(self):
                self.calls = []

            def _add_route(self, path, method, handler, cors=None):
                self.calls.append((path, method, handler, cors))
                return handler

        router = MockRouter()

        @router.get("/users", cors=cors_config)
        def get_users():
            return {"users": []}

        assert len(router.calls) == 1
        call = router.calls[0]
        assert call[0] == "/users"  # path
        assert call[1] == "GET"  # method
        assert call[2] == get_users  # handler
        assert call[3] == cors_config  # cors

    def test_post_decorator_basic(self):
        """POST デコレータの基本テスト"""

        class MockRouter(BaseRouterMixin):
            def __init__(self):
                self.calls = []

            def _add_route(self, path, method, handler, cors=None):
                self.calls.append((path, method, handler, cors))
                return handler

        router = MockRouter()

        @router.post("/create")
        def create_handler():
            return {"created": True}

        assert len(router.calls) == 1
        call_args = router.calls[0]
        assert call_args[0] == "/create"
        assert call_args[1] == "POST"
        assert call_args[2] == create_handler

    def test_all_http_methods(self):
        """全 HTTP メソッドのテスト"""

        class MockRouter(BaseRouterMixin):
            def __init__(self):
                self.calls = []

            def _add_route(self, path, method, handler, cors=None):
                self.calls.append((path, method, handler, cors))
                return handler

        router = MockRouter()

        @router.get("/get")
        def get_handler():
            return {"method": "GET"}

        @router.post("/post")
        def post_handler():
            return {"method": "POST"}

        @router.put("/put")
        def put_handler():
            return {"method": "PUT"}

        @router.delete("/delete")
        def delete_handler():
            return {"method": "DELETE"}

        @router.patch("/patch")
        def patch_handler():
            return {"method": "PATCH"}

        assert len(router.calls) == 5

        methods = [call[1] for call in router.calls]
        paths = [call[0] for call in router.calls]
        handlers = [call[2] for call in router.calls]

        assert "GET" in methods
        assert "POST" in methods
        assert "PUT" in methods
        assert "DELETE" in methods
        assert "PATCH" in methods

        assert "/get" in paths
        assert "/post" in paths
        assert "/put" in paths
        assert "/delete" in paths
        assert "/patch" in paths

        assert get_handler in handlers
        assert post_handler in handlers
        assert put_handler in handlers
        assert delete_handler in handlers
        assert patch_handler in handlers

    def test_cors_parameter_variations(self):
        """CORS パラメータのバリエーションテスト"""

        class MockRouter(BaseRouterMixin):
            def __init__(self):
                self.calls = []

            def _add_route(self, path, method, handler, cors=None):
                self.calls.append((path, method, handler, cors))
                return handler

        router = MockRouter()
        cors_config = create_cors_config(origins=["*"])

        # cors=True
        @router.get("/cors-true", cors=True)
        def handler1():
            return {}

        # cors=False
        @router.get("/cors-false", cors=False)
        def handler2():
            return {}

        # cors=CORSConfig
        @router.get("/cors-config", cors=cors_config)
        def handler3():
            return {}

        # cors=None (デフォルト)
        @router.get("/cors-none")
        def handler4():
            return {}

        assert len(router.calls) == 4

        cors_values = [call[3] for call in router.calls]
        assert True in cors_values
        assert False in cors_values
        assert cors_config in cors_values
        assert None in cors_values

    def test_decorator_returns_original_function(self):
        """デコレータが元の関数を返すことをテスト"""

        class MockRouter(BaseRouterMixin):
            def _add_route(self, path, method, handler, cors=None):
                return handler  # 元の関数を返す

        router = MockRouter()

        def original_handler():
            return {"test": True}

        # デコレータが元の関数を返すことを確認
        decorated = router.get("/test")(original_handler)
        assert decorated is original_handler
