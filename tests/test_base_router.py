"""
BaseRouterMixin のテスト

lambapi.base_router モジュールの各機能をテストします。
"""

import pytest
from lambapi.base_router import BaseRouterMixin
from lambapi.cors import create_cors_config


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

    def test_get_decorator_with_all_parameters(self):
        """GET デコレータの全パラメータテスト"""
        from dataclasses import dataclass

        @dataclass
        class RequestFormat:
            name: str

        @dataclass
        class ResponseFormat:
            id: int
            name: str

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
        call_args = router.calls[0]
        assert call_args[0] == "/users"
        assert call_args[1] == "GET"
        assert call_args[2] == get_users
        assert call_args[3] == cors_config

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
        def create_handler(request):
            return {"created": True}

        assert len(router.calls) == 1
        call_args = router.calls[0]
        assert call_args[0] == "/create"
        assert call_args[1] == "POST"
        assert call_args[2] == create_handler

    def test_put_decorator_basic(self):
        """PUT デコレータの基本テスト"""

        class MockRouter(BaseRouterMixin):
            def __init__(self):
                self.calls = []

            def _add_route(self, path, method, handler, cors=None):
                self.calls.append((path, method, handler, cors))
                return handler

        router = MockRouter()

        @router.put("/update")
        def update_handler(request):
            return {"updated": True}

        assert len(router.calls) == 1
        call_args = router.calls[0]
        assert call_args[0] == "/update"
        assert call_args[1] == "PUT"
        assert call_args[2] == update_handler

    def test_delete_decorator_basic(self):
        """DELETE デコレータの基本テスト"""

        class MockRouter(BaseRouterMixin):
            def __init__(self):
                self.calls = []

            def _add_route(self, path, method, handler, cors=None):
                self.calls.append((path, method, handler, cors))
                return handler

        router = MockRouter()

        @router.delete("/remove")
        def delete_handler():
            return {"deleted": True}

        assert len(router.calls) == 1
        call_args = router.calls[0]
        assert call_args[0] == "/remove"
        assert call_args[1] == "DELETE"
        assert call_args[2] == delete_handler

    def test_patch_decorator_basic(self):
        """PATCH デコレータの基本テスト"""

        class MockRouter(BaseRouterMixin):
            def __init__(self):
                self.calls = []

            def _add_route(self, path, method, handler, cors=None):
                self.calls.append((path, method, handler, cors))
                return handler

        router = MockRouter()

        @router.patch("/modify")
        def patch_handler(request):
            return {"patched": True}

        assert len(router.calls) == 1
        call_args = router.calls[0]
        assert call_args[0] == "/modify"
        assert call_args[1] == "PATCH"
        assert call_args[2] == patch_handler

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
        def post_handler(request):
            return {"method": "POST"}

        @router.put("/put")
        def put_handler(request):
            return {"method": "PUT"}

        @router.delete("/delete")
        def delete_handler():
            return {"method": "DELETE"}

        @router.patch("/patch")
        def patch_handler(request):
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

    def test_request_response_format_parameters(self):
        """リクエスト・レスポンス形式パラメータのテスト - request_format/response_format が削除されたため簡素化"""

        class MockRouter(BaseRouterMixin):
            def __init__(self):
                self.calls = []

            def _add_route(self, path, method, handler, cors=None):
                self.calls.append((path, method, handler, cors))
                return handler

        router = MockRouter()

        @router.post("/request-only")
        def handler1(request):
            return {}

        @router.get("/response-only")
        def handler2():
            return {}

        @router.put("/both")
        def handler3(request):
            return {}

        assert len(router.calls) == 3

    def test_path_parameter_variations(self):
        """パスパラメータのバリエーションテスト"""

        class MockRouter(BaseRouterMixin):
            def __init__(self):
                self.calls = []

            def _add_route(self, path, method, handler, cors=None):
                self.calls.append((path, method, handler, cors))
                return handler

        router = MockRouter()

        # デフォルトパス
        @router.get()
        def root_handler():
            return {}

        # 単純パス
        @router.get("/users")
        def users_handler():
            return {}

        # パラメータ付きパス
        @router.get("/users/{id}")
        def user_handler():
            return {}

        # 複雑なパス
        @router.get("/api/v1/users/{id}/posts/{post_id}")
        def complex_handler():
            return {}

        assert len(router.calls) == 4

        paths = [call[0] for call in router.calls]
        assert "/" in paths
        assert "/users" in paths
        assert "/users/{id}" in paths
        assert "/api/v1/users/{id}/posts/{post_id}" in paths

    def test_decorator_chaining(self):
        """デコレータチェーンのテスト"""

        class MockRouter(BaseRouterMixin):
            def __init__(self):
                self.calls = []

            def _add_route(self, path, method, handler, cors=None):
                self.calls.append((path, method, handler, cors))
                return handler

        router = MockRouter()

        # 同じハンドラーに複数のルートを追加
        def multi_method_handler():
            return {"message": "Supports multiple methods"}

        # 同じ関数を複数のメソッドで登録
        router.get("/resource")(multi_method_handler)
        router.post("/resource")(multi_method_handler)
        router.put("/resource")(multi_method_handler)

        assert len(router.calls) == 3

        # 全て同じハンドラー
        handlers = [call[2] for call in router.calls]
        assert all(handler is multi_method_handler for handler in handlers)

        # 異なるメソッド
        methods = [call[1] for call in router.calls]
        assert "GET" in methods
        assert "POST" in methods
        assert "PUT" in methods

    def test_inheritance_behavior(self):
        """継承動作のテスト"""

        class CustomRouter(BaseRouterMixin):
            def __init__(self):
                self.routes = []

            def _add_route(self, path, method, handler, cors=None):
                # カスタム実装
                route_info = {
                    "path": path,
                    "method": method,
                    "handler": handler,
                    "cors": cors,
                }
                self.routes.append(route_info)
                return handler

        router = CustomRouter()

        @router.get("/test")
        def test_handler():
            return {"test": True}

        assert len(router.routes) == 1
        route = router.routes[0]
        assert route["path"] == "/test"
        assert route["method"] == "GET"
        assert route["handler"] == test_handler

    def test_multiple_routers_independence(self):
        """複数ルーターの独立性テスト"""

        class MockRouter(BaseRouterMixin):
            def __init__(self):
                self.calls = []

            def _add_route(self, path, method, handler, cors=None):
                self.calls.append((path, method, handler, cors))
                return handler

        router1 = MockRouter()
        router2 = MockRouter()

        @router1.get("/router1")
        def handler1():
            return {"router": 1}

        @router2.get("/router2")
        def handler2():
            return {"router": 2}

        # 各ルーターが独立していることを確認
        assert len(router1.calls) == 1
        assert len(router2.calls) == 1
        assert router1.calls[0][0] == "/router1"
        assert router2.calls[0][0] == "/router2"

    def test_error_handling_in_add_route(self):
        """_add_route でのエラーハンドリングテスト"""

        class FailingRouter(BaseRouterMixin):
            def _add_route(self, path, method, handler, cors=None):
                raise RuntimeError("Route addition failed")

        router = FailingRouter()

        # _add_route でエラーが発生した場合、デコレータでもエラーになる
        with pytest.raises(RuntimeError, match="Route addition failed"):

            @router.get("/test")
            def test_handler():
                return {}

    def test_decorator_parameter_forwarding(self):
        """デコレータパラメータの転送テスト - request_format/response_format が削除されたため簡素化"""

        class ParameterCapturingRouter(BaseRouterMixin):
            def __init__(self):
                self.captured_params = {}

            def _add_route(self, path, method, handler, cors=None):
                self.captured_params = {
                    "path": path,
                    "method": method,
                    "handler": handler,
                    "cors": cors,
                }
                return handler

        router = ParameterCapturingRouter()
        cors_config = create_cors_config(origins=["https://test.com"])

        @router.post("/complex-endpoint", cors=cors_config)
        def complex_handler(request):
            return []

        params = router.captured_params
        assert params["path"] == "/complex-endpoint"
        assert params["method"] == "POST"
        assert params["handler"] == complex_handler
        assert params["cors"] == cors_config
