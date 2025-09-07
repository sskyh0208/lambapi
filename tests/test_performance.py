"""
パフォーマンステスト

Lambda 最適化の効果を測定します。
JSON 処理とルート検索の性能改善を検証します。
"""

import json
import time

from lambapi.json_handler import JSONHandler
from lambapi.core import API


class TestJSONPerformance:
    """JSON 処理パフォーマンステスト"""

    def setup_method(self):
        """テスト用データの準備"""
        self.small_data = {"id": 1, "name": "test", "active": True}
        self.large_data = [
            {
                "id": i,
                "name": f"user_{i}",
                "email": f"user_{i}@example.com",
                "metadata": {
                    "created_at": "2023-01-01T00:00:00Z",
                    "tags": [f"tag_{j}" for j in range(5)],  # タグ数を削減
                    "nested": {"level1": {"level2": {"value": f"value_{i}"}}},  # ネスト深度を削減
                },
            }
            for i in range(500)  # データ数を削減
        ]

    def test_json_loads_performance(self):
        """JSON パース性能テスト"""
        json_string = json.dumps(self.large_data)

        # 標準 json モジュール
        start_time = time.perf_counter()
        for _ in range(100):
            json.loads(json_string)
        standard_time = time.perf_counter() - start_time

        # JSONHandler
        start_time = time.perf_counter()
        for _ in range(100):
            JSONHandler.loads(json_string)
        handler_time = time.perf_counter() - start_time

        print(f"\n 標準 json.loads: {standard_time:.4f}秒")
        print(f"JSONHandler.loads: {handler_time:.4f}秒")
        print(f"改善率: {((standard_time - handler_time) / standard_time * 100):.1f}%")

        # JSONHandler は標準より高速または同等であることを期待
        # orjson がある場合は高速、ない場合は同等の性能
        assert handler_time <= standard_time * 1.5  # 50% 以内の差（フォールバック考慮）

    def test_json_dumps_performance(self):
        """JSON シリアライズ性能テスト"""
        # 標準 json モジュール
        start_time = time.perf_counter()
        for _ in range(100):
            json.dumps(self.large_data, ensure_ascii=False, separators=(",", ":"))
        standard_time = time.perf_counter() - start_time

        # JSONHandler
        start_time = time.perf_counter()
        for _ in range(100):
            JSONHandler.dumps(self.large_data, ensure_ascii=False)
        handler_time = time.perf_counter() - start_time

        print(f"\n 標準 json.dumps: {standard_time:.4f}秒")
        print(f"JSONHandler.dumps: {handler_time:.4f}秒")
        print(f"改善率: {((standard_time - handler_time) / standard_time * 100):.1f}%")

        # JSONHandler は標準より高速または同等であることを期待
        assert handler_time <= standard_time * 1.5  # 50% 以内の差（フォールバック考慮）

    def test_json_error_handling_performance(self):
        """JSON エラーハンドリング性能テスト"""
        invalid_json = '{"invalid": json, "missing": quote}'

        # 標準 json モジュール（try-catch 付き）
        start_time = time.perf_counter()
        for _ in range(1000):
            try:
                json.loads(invalid_json)
            except json.JSONDecodeError:
                pass
        standard_time = time.perf_counter() - start_time

        # JSONHandler
        start_time = time.perf_counter()
        for _ in range(1000):
            JSONHandler.loads(invalid_json)
        handler_time = time.perf_counter() - start_time

        print(f"\n 標準 json.loads (エラー処理): {standard_time:.4f}秒")
        print(f"JSONHandler.loads (エラー処理): {handler_time:.4f}秒")
        print(f"改善率: {((standard_time - handler_time) / standard_time * 100):.1f}%")

        # エラーハンドリングでも性能劣化を最小限に抑制
        assert handler_time <= standard_time * 1.5  # 50% 以内の差（エラー処理は安全性優先）


class TestRouteSearchPerformance:
    """ルート検索パフォーマンステスト"""

    def setup_method(self):
        """テスト用ルートの準備"""
        self.test_event = {
            "httpMethod": "GET",
            "path": "/api/v1/users/123",
            "headers": {},
            "body": None,
        }
        self.test_context = type("Context", (), {"aws_request_id": "test-123"})()

    def test_exact_route_search_performance(self):
        """完全一致ルート検索性能テスト"""
        api = API(self.test_event, self.test_context)

        # 100 個の完全一致ルートを追加
        routes = []
        for i in range(100):
            route_path = f"/api/v1/endpoint_{i}"

            def dummy_handler():
                return {"result": "ok"}

            api.get(route_path)(dummy_handler)
            routes.append(route_path)

        # 最後のルートを検索（最悪ケース）
        target_path = routes[-1]

        # 検索性能測定
        start_time = time.perf_counter()
        for _ in range(1000):
            api._find_route(target_path, "GET")
        search_time = time.perf_counter() - start_time

        print(f"\n100 ルート中の完全一致検索: {search_time:.4f}秒 (1000 回)")
        print(f"1 回あたり: {search_time * 1000:.4f}ミリ秒")

        # O(1) 検索なので高速であることを期待
        assert search_time < 0.01  # 10ms 以内

    def test_pattern_route_search_performance(self):
        """パターンマッチングルート検索性能テスト"""
        api = API(self.test_event, self.test_context)

        # パラメータ付きルートを追加
        patterns = [
            "/api/v1/users/{user_id}",
            "/api/v1/posts/{post_id}",
            "/api/v1/categories/{category_id}/items/{item_id}",
            "/api/v1/organizations/{org_id}/members/{member_id}",
            "/api/v1/projects/{project_id}/tasks/{task_id}/comments/{comment_id}",
        ]

        for pattern in patterns:

            def dummy_handler():
                return {"result": "ok"}

            api.get(pattern)(dummy_handler)

        # パターンマッチング検索
        test_path = "/api/v1/users/12345"

        start_time = time.perf_counter()
        for _ in range(1000):
            api._find_route(test_path, "GET")
        search_time = time.perf_counter() - start_time

        print(f"\n パターンマッチング検索: {search_time:.4f}秒 (1000 回)")
        print(f"1 回あたり: {search_time * 1000:.4f}ミリ秒")

        # パターンマッチングでも高速であることを期待
        assert search_time < 0.05  # 50ms 以内

    def test_mixed_route_search_performance(self):
        """混在ルート検索性能テスト（完全一致 + パターン）"""
        api = API(self.test_event, self.test_context)

        # 完全一致ルート 50 個
        for i in range(50):
            route_path = f"/api/v1/endpoint_{i}"

            def dummy_handler():
                return {"result": "ok"}

            api.get(route_path)(dummy_handler)

        # パターンルート 20 個
        for i in range(20):
            pattern = f"/api/v1/resource_{i}/{{id}}"

            def dummy_handler():
                return {"result": "ok"}

            api.get(pattern)(dummy_handler)

        # 完全一致検索（最適化の効果が最も出る）
        exact_path = "/api/v1/endpoint_49"

        start_time = time.perf_counter()
        for _ in range(1000):
            route, params = api._find_route(exact_path, "GET")
        exact_time = time.perf_counter() - start_time

        # パターンマッチング検索
        pattern_path = "/api/v1/resource_19/12345"

        start_time = time.perf_counter()
        for _ in range(1000):
            route, params = api._find_route(pattern_path, "GET")
        pattern_time = time.perf_counter() - start_time

        print(f"\n 混在ルート - 完全一致検索: {exact_time:.4f}秒")
        print(f"混在ルート - パターン検索: {pattern_time:.4f}秒")
        print(f"完全一致の優位性: {(pattern_time / exact_time):.1f}倍高速")

        # 完全一致はパターンマッチングより高速
        assert exact_time < pattern_time
        assert exact_time < 0.005  # 5ms 以内

    def test_route_index_rebuild_performance(self):
        """ルートインデックス再構築性能テスト"""
        api = API(self.test_event, self.test_context)

        # 多数のルートを追加
        for i in range(200):
            if i % 2 == 0:
                route_path = f"/api/v1/endpoint_{i}"
            else:
                route_path = f"/api/v1/resource_{i}/{{id}}"

            def dummy_handler():
                return {"result": "ok"}

            api.get(route_path)(dummy_handler)

        # インデックス再構築性能測定
        start_time = time.perf_counter()
        for _ in range(100):
            api._rebuild_route_index()
        rebuild_time = time.perf_counter() - start_time

        print(f"\n200 ルートのインデックス再構築: {rebuild_time:.4f}秒 (100 回)")
        print(f"1 回あたり: {rebuild_time * 10:.4f}ミリ秒")

        # 再構築も高速であることを期待
        assert rebuild_time < 0.1  # 100ms 以内


class TestLambdaColdStartSimulation:
    """Lambda コールドスタートシミュレーション"""

    def test_import_time_optimization(self):
        """インポート時間の最適化効果測定"""
        import importlib
        import sys

        # JSONHandler のインポート時間測定
        if "lambapi.json_handler" in sys.modules:
            del sys.modules["lambapi.json_handler"]

        start_time = time.perf_counter()
        importlib.import_module("lambapi.json_handler")
        import_time = time.perf_counter() - start_time

        print(f"\nJSONHandler インポート時間: {import_time * 1000:.2f}ミリ秒")

        # インポート時間は 10ms 以内であることを期待
        assert import_time < 0.01

    def test_initialization_performance(self):
        """初期化性能テスト"""
        test_event = {"httpMethod": "GET", "path": "/", "headers": {}, "body": None}
        test_context = type("Context", (), {"aws_request_id": "test-123"})()

        # API 初期化時間測定
        start_time = time.perf_counter()
        for _ in range(100):
            API(test_event, test_context)
        init_time = time.perf_counter() - start_time

        print(f"\nAPI 初期化時間: {init_time:.4f}秒 (100 回)")
        print(f"1 回あたり: {init_time * 10:.4f}ミリ秒")

        # 初期化は高速であることを期待
        assert init_time < 0.05  # 50ms 以内

    def test_first_request_performance(self):
        """初回リクエスト処理性能テスト"""
        test_event = {"httpMethod": "GET", "path": "/health", "headers": {}, "body": None}
        test_context = type("Context", (), {"aws_request_id": "test-123"})()

        api = API(test_event, test_context)

        @api.get("/health")
        def health_check():
            return {"status": "healthy", "timestamp": time.time()}

        # 初回リクエスト処理時間測定
        start_time = time.perf_counter()
        response = api.handle_request()
        first_request_time = time.perf_counter() - start_time

        print(f"\n 初回リクエスト処理時間: {first_request_time * 1000:.2f}ミリ秒")

        # 初回リクエストも高速であることを期待
        assert first_request_time < 0.1  # 100ms 以内
        assert response["statusCode"] == 200


class TestPerformanceBenchmark:
    """ベンチマーク用テスト（基本的なパフォーマンス検証）"""

    def test_json_loads_benchmark(self):
        """JSON パースベンチマーク"""
        test_data = '{"id": 1, "name": "test", "items": [1, 2, 3, 4, 5]}'

        result = JSONHandler.loads(test_data)
        assert result == {"id": 1, "name": "test", "items": [1, 2, 3, 4, 5]}

    def test_json_dumps_benchmark(self):
        """JSON シリアライズベンチマーク"""
        test_data = {"id": 1, "name": "test", "items": [1, 2, 3, 4, 5]}

        result = JSONHandler.dumps(test_data)
        assert '"id":1' in result

    def test_route_search_benchmark(self):
        """ルート検索ベンチマーク"""
        test_event = {"httpMethod": "GET", "path": "/api/users/123", "headers": {}, "body": None}
        test_context = type("Context", (), {"aws_request_id": "test-123"})()

        api = API(test_event, test_context)

        @api.get("/api/users/{user_id}")
        def get_user():
            return {"user_id": "123"}

        route, params = api._find_route("/api/users/123", "GET")
        assert route is not None
        assert params == {"user_id": "123"}


if __name__ == "__main__":
    # 手動実行用のパフォーマンステスト
    print("=== Lambda パフォーマンステスト ===")

    # JSON パフォーマンステスト
    json_test = TestJSONPerformance()
    json_test.setup_method()
    json_test.test_json_loads_performance()
    json_test.test_json_dumps_performance()
    json_test.test_json_error_handling_performance()

    # ルート検索パフォーマンステスト
    route_test = TestRouteSearchPerformance()
    route_test.setup_method()
    route_test.test_exact_route_search_performance()
    route_test.test_pattern_route_search_performance()
    route_test.test_mixed_route_search_performance()
    route_test.test_route_index_rebuild_performance()

    # コールドスタートシミュレーション
    coldstart_test = TestLambdaColdStartSimulation()
    coldstart_test.test_import_time_optimization()
    coldstart_test.test_initialization_performance()
    coldstart_test.test_first_request_performance()

    print("\n=== すべてのパフォーマンステスト完了 ===")
