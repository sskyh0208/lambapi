"""
ルーター機能のテスト

lambapi.router モジュールの各機能をテストします。
"""

from lambapi.router import Router
from lambapi.cors import create_cors_config


class TestRouter:
    """Router クラスのテスト"""

    def test_router_initialization(self):
        """ルーター初期化のテスト"""
        # デフォルト初期化
        router = Router()
        assert router.prefix == ""
        assert router.tags == []
        assert router.routes == []

    def test_router_initialization_with_prefix(self):
        """プレフィックス付きルーター初期化のテスト"""
        router = Router(prefix="/api/v1")
        assert router.prefix == "/api/v1"
        assert router.tags == []

    def test_router_initialization_with_prefix_trailing_slash(self):
        """末尾スラッシュ付きプレフィックスのテスト"""
        router = Router(prefix="/api/v1/")
        assert router.prefix == "/api/v1"  # 末尾スラッシュが削除される

    def test_router_initialization_with_tags(self):
        """タグ付きルーター初期化のテスト"""
        tags = ["api", "v1", "users"]
        router = Router(tags=tags)
        assert router.prefix == ""
        assert router.tags == tags

    def test_router_initialization_with_prefix_and_tags(self):
        """プレフィックスとタグ付きルーター初期化のテスト"""
        router = Router(prefix="/api/v1", tags=["api", "users"])
        assert router.prefix == "/api/v1"
        assert router.tags == ["api", "users"]

    def test_add_get_route(self):
        """GET ルート追加のテスト"""
        router = Router()

        @router.get("/users")
        def get_users():
            return {"users": []}

        assert len(router.routes) == 1
        route = router.routes[0]
        assert route.path == "/users"
        assert route.method == "GET"
        assert route.handler == get_users

    def test_add_post_route(self):
        """POST ルート追加のテスト"""
        router = Router()

        @router.post("/users")
        def create_user(request):
            return {"created": True}

        assert len(router.routes) == 1
        route = router.routes[0]
        assert route.path == "/users"
        assert route.method == "POST"
        assert route.handler == create_user

    def test_add_multiple_routes(self):
        """複数ルート追加のテスト"""
        router = Router()

        @router.get("/users")
        def get_users():
            return {"users": []}

        @router.post("/users")
        def create_user(request):
            return {"created": True}

        @router.put("/users/{id}")
        def update_user(request, id: str):
            return {"updated": True, "id": id}

        @router.delete("/users/{id}")
        def delete_user(id: str):
            return {"deleted": True, "id": id}

        @router.patch("/users/{id}")
        def patch_user(request, id: str):
            return {"patched": True, "id": id}

        assert len(router.routes) == 5
        methods = [route.method for route in router.routes]
        assert "GET" in methods
        assert "POST" in methods
        assert "PUT" in methods
        assert "DELETE" in methods
        assert "PATCH" in methods

    def test_add_route_with_prefix(self):
        """プレフィックス付きルート追加のテスト"""
        router = Router(prefix="/api/v1")

        @router.get("/users")
        def get_users():
            return {"users": []}

        assert len(router.routes) == 1
        route = router.routes[0]
        assert route.path == "/api/v1/users"
        assert route.method == "GET"

    def test_add_root_route_with_prefix(self):
        """プレフィックス付きルートルート追加のテスト"""
        router = Router(prefix="/api/v1")

        @router.get("/")
        def get_root():
            return {"message": "API v1"}

        assert len(router.routes) == 1
        route = router.routes[0]
        assert route.path == "/api/v1"
        assert route.method == "GET"

    def test_add_route_no_prefix_root(self):
        """プレフィックスなしルートルート追加のテスト"""
        router = Router()

        @router.get("/")
        def get_root():
            return {"message": "Root"}

        assert len(router.routes) == 1
        route = router.routes[0]
        assert route.path == "/"
        assert route.method == "GET"

    def test_add_router_basic(self):
        """基本的なルーター統合のテスト"""
        # 子ルーター
        child_router = Router()

        @child_router.get("/items")
        def get_items():
            return {"items": []}

        @child_router.post("/items")
        def create_item(request):
            return {"created": True}

        # 親ルーター
        parent_router = Router()
        parent_router.add_router(child_router)

        assert len(parent_router.routes) == 2
        paths = [route.path for route in parent_router.routes]
        assert "/items" in paths

    def test_add_router_with_prefix(self):
        """プレフィックス付きルーター統合のテスト"""
        # 子ルーター
        child_router = Router()

        @child_router.get("/items")
        def get_items():
            return {"items": []}

        # 親ルーター
        parent_router = Router()
        parent_router.add_router(child_router, prefix="/api")

        assert len(parent_router.routes) == 1
        route = parent_router.routes[0]
        assert route.path == "/api/items"

    def test_add_router_with_parent_prefix(self):
        """親ルーターのプレフィックス付き統合のテスト"""
        # 子ルーター
        child_router = Router()

        @child_router.get("/items")
        def get_items():
            return {"items": []}

        # 親ルーター（プレフィックス付き）
        parent_router = Router(prefix="/api/v1")
        parent_router.add_router(child_router)

        assert len(parent_router.routes) == 1
        route = parent_router.routes[0]
        assert route.path == "/api/v1/items"

    def test_add_router_with_both_prefixes(self):
        """両方のプレフィックス付きルーター統合のテスト"""
        # 子ルーター（プレフィックス付き）
        child_router = Router(prefix="/users")

        @child_router.get("/profile")
        def get_profile():
            return {"profile": {}}

        # 親ルーター（プレフィックス付き）
        parent_router = Router(prefix="/api/v1")
        parent_router.add_router(child_router, prefix="/admin")

        assert len(parent_router.routes) == 1
        route = parent_router.routes[0]
        assert route.path == "/api/v1/admin/users/profile"

    def test_add_router_nested(self):
        """ネストしたルーター統合のテスト"""
        # 最下位ルーター
        items_router = Router()

        @items_router.get("/")
        def get_items():
            return {"items": []}

        @items_router.get("/{id}")
        def get_item(id: str):
            return {"item": {"id": id}}

        # 中間ルーター
        api_router = Router(prefix="/api")
        api_router.add_router(items_router, prefix="/items")

        # 最上位ルーター
        main_router = Router(prefix="/v1")
        main_router.add_router(api_router)

        assert len(main_router.routes) == 2
        paths = [route.path for route in main_router.routes]
        assert "/v1/api/items/" in paths
        assert "/v1/api/items/{id}" in paths

    def test_include_multiple_routers(self):
        """複数ルーター統合のテスト"""
        # ユーザールーター
        users_router = Router()

        @users_router.get("/")
        def get_users():
            return {"users": []}

        @users_router.post("/")
        def create_user(request):
            return {"created": True}

        # アイテムルーター
        items_router = Router()

        @items_router.get("/")
        def get_items():
            return {"items": []}

        # メインルーター
        main_router = Router(prefix="/api")
        main_router.add_router(users_router, prefix="/users")
        main_router.add_router(items_router, prefix="/items")

        assert len(main_router.routes) == 3
        paths = [route.path for route in main_router.routes]
        assert "/api/users/" in paths
        assert "/api/items/" in paths

    def test_router_with_cors(self):
        """CORS 設定付きルーターのテスト"""
        cors_config = create_cors_config(origins=["https://example.com"], methods=["GET", "POST"])

        router = Router()

        @router.get("/test", cors=cors_config)
        def get_test():
            return {"test": True}

        assert len(router.routes) == 1
        # CORS 設定は Route オブジェクトには直接保存されない
        # (実際の実装では API クラスで処理される)

    def test_router_route_conflict_handling(self):
        """ルート衝突の処理テスト"""
        router = Router()

        @router.get("/test")
        def handler1():
            return {"handler": 1}

        @router.get("/test")  # 同じパスとメソッド
        def handler2():
            return {"handler": 2}

        # 両方のルートが追加される（後で追加されたものが優先される）
        assert len(router.routes) == 2
        assert router.routes[0].handler == handler1
        assert router.routes[1].handler == handler2

    def test_router_with_request_response_formats(self):
        """リクエスト・レスポンス形式指定のテスト - request_format/response_format が削除されたため簡素化"""
        router = Router()

        @router.post("/users")
        def create_user(request):
            return {"created": True}

        assert len(router.routes) == 1

    def test_empty_router_include(self):
        """空のルーター統合のテスト"""
        empty_router = Router()
        main_router = Router()

        main_router.add_router(empty_router)

        assert len(main_router.routes) == 0

    def test_router_path_normalization(self):
        """パス正規化のテスト"""
        test_cases = [
            ("/api/v1/", "/users", "/api/v1/users"),  # 末尾スラッシュ削除
            ("/api/v1", "/users", "/api/v1/users"),  # 通常
            ("", "/users", "/users"),  # プレフィックスなし
            ("/api/v1", "/", "/api/v1"),  # ルートパス
            ("", "/", "/"),  # ルートパスのみ
        ]

        for prefix, path, expected in test_cases:
            router = Router(prefix=prefix)

            @router.get(path)
            def handler():
                return {}

            assert len(router.routes) == 1
            assert router.routes[0].path == expected
            router.routes.clear()  # 次のテストのためにクリア

    def test_router_method_decorators(self):
        """各 HTTP メソッドデコレーターのテスト"""
        router = Router()

        # 各メソッドをテスト
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

        assert len(router.routes) == 5

        methods = {route.method: route.path for route in router.routes}
        assert methods["GET"] == "/get"
        assert methods["POST"] == "/post"
        assert methods["PUT"] == "/put"
        assert methods["DELETE"] == "/delete"
        assert methods["PATCH"] == "/patch"

    def test_router_include_non_router_object(self):
        """非ルーターオブジェクトの統合テスト"""
        router = Router()

        # 非ルーターオブジェクト
        class NonRouter:
            def __init__(self):
                self.routes = []

        non_router = NonRouter()

        # add_router は Router インスタンスのみを処理
        router.add_router(non_router)

        assert len(router.routes) == 0

    def test_router_complex_path_patterns(self):
        """複雑なパスパターンのテスト"""
        router = Router(prefix="/api/v1")

        @router.get("/users/{user_id}")
        def get_user(user_id: str):
            return {"user_id": user_id}

        @router.get("/users/{user_id}/posts/{post_id}")
        def get_user_post(user_id: str, post_id: str):
            return {"user_id": user_id, "post_id": post_id}

        @router.get("/categories/{category}/items/{item_id}")
        def get_category_item(category: str, item_id: str):
            return {"category": category, "item_id": item_id}

        assert len(router.routes) == 3
        paths = [route.path for route in router.routes]
        assert "/api/v1/users/{user_id}" in paths
        assert "/api/v1/users/{user_id}/posts/{post_id}" in paths
        assert "/api/v1/categories/{category}/items/{item_id}" in paths

    def test_router_preservation_of_handler_functions(self):
        """ハンドラー関数の保持テスト"""
        router = Router()

        def original_handler():
            return {"test": "original"}

        # デコレーターが元の関数を返すことを確認
        decorated_handler = router.get("/test")(original_handler)

        assert decorated_handler is original_handler
        assert len(router.routes) == 1
        assert router.routes[0].handler is original_handler

    def test_router_tags_functionality(self):
        """タグ機能のテスト"""
        router = Router(tags=["api", "v1", "users"])

        @router.get("/users")
        def get_users():
            return {"users": []}

        # タグは Router レベルで保持される
        assert router.tags == ["api", "v1", "users"]
        # 実際のタグ処理は上位の API クラスで行われる

    def test_router_include_with_tags(self):
        """タグ付きルーター統合のテスト"""
        child_router = Router(tags=["child", "api"])

        @child_router.get("/items")
        def get_items():
            return {"items": []}

        parent_router = Router(tags=["parent"])
        parent_router.add_router(child_router, tags=["included"])

        # ルートは正しく統合される
        assert len(parent_router.routes) == 1
        assert parent_router.routes[0].path == "/items"

        # タグの統合は現在の実装では行われない
        # (将来の拡張で実装可能)
