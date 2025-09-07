"""
API コアクラスのテスト
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lambapi import API, Response


class TestAPI:
    """API クラスのテスト"""

    def create_test_event(self, method="GET", path="/", query_params=None, body=None):
        """テスト用のイベントを作成"""
        return {
            "httpMethod": method,
            "path": path,
            "queryStringParameters": query_params,
            "headers": {"Content-Type": "application/json"},
            "body": body,
        }

    def test_basic_get_route(self):
        """基本的な GET ルートのテスト"""
        event = self.create_test_event()
        app = API(event, None)

        @app.get("/")
        def hello():
            return {"message": "Hello World"}

        result = app.handle_request()

        assert result["statusCode"] == 200
        assert '"message":"Hello World"' in result["body"]

    def test_path_parameters(self):
        """パスパラメータのテスト"""
        event = self.create_test_event(path="/users/123")
        app = API(event, None)

        @app.get("/users/{user_id}")
        def get_user(user_id: str):
            return {"user_id": user_id}

        result = app.handle_request()

        assert result["statusCode"] == 200
        assert '"user_id":"123"' in result["body"]

    def test_query_parameters(self):
        """クエリパラメータのテスト"""
        event = self.create_test_event(path="/search", query_params={"q": "python", "limit": "10"})
        app = API(event, None)

        @app.get("/search")
        def search(q: str = "", limit: int = 5):
            return {"query": q, "limit": limit}

        result = app.handle_request()

        assert result["statusCode"] == 200
        body = result["body"]
        assert '"query":"python"' in body
        assert '"limit":10' in body

    def test_query_parameters_default_values(self):
        """クエリパラメータのデフォルト値テスト"""
        event = self.create_test_event(path="/search")
        app = API(event, None)

        @app.get("/search")
        def search(q: str = "default", limit: int = 5):
            return {"query": q, "limit": limit}

        result = app.handle_request()

        assert result["statusCode"] == 200
        body = result["body"]
        assert '"query":"default"' in body
        assert '"limit":5' in body

    def test_type_conversion(self):
        """型変換のテスト"""
        event = self.create_test_event(
            path="/items", query_params={"limit": "25", "offset": "10", "active": "true"}
        )
        app = API(event, None)

        @app.get("/items")
        def get_items(limit: int = 10, offset: int = 0, active: bool = False):
            return {
                "limit": limit,
                "offset": offset,
                "active": active,
                "types": {
                    "limit": type(limit).__name__,
                    "offset": type(offset).__name__,
                    "active": type(active).__name__,
                },
            }

        result = app.handle_request()

        assert result["statusCode"] == 200
        body = result["body"]
        assert '"limit":25' in body
        assert '"offset":10' in body
        assert '"active":true' in body

    def test_post_request(self):
        """POST リクエストのテスト"""
        import json

        body_data = {"name": "John", "age": 30}
        event = self.create_test_event(method="POST", path="/users", body=json.dumps(body_data))
        app = API(event, None)

        @app.post("/users")
        def create_user(request):
            user_data = request.json()
            return Response({"message": "Created", "user": user_data}, status_code=201)

        result = app.handle_request()

        assert result["statusCode"] == 201
        assert '"message":"Created"' in result["body"]
        assert '"name":"John"' in result["body"]

    def test_not_found(self):
        """404 エラーのテスト"""
        event = self.create_test_event(path="/nonexistent")
        app = API(event, None)

        @app.get("/")
        def hello():
            return {"message": "Hello"}

        result = app.handle_request()

        assert result["statusCode"] == 404
        assert '"error":"Not Found"' in result["body"]

    def test_middleware(self):
        """ミドルウェアのテスト"""
        event = self.create_test_event()
        app = API(event, None)

        def test_middleware(request, response):
            if isinstance(response, Response):
                response.headers["X-Test"] = "middleware-applied"
            return response

        app.add_middleware(test_middleware)

        @app.get("/")
        def hello():
            return Response({"message": "Hello"})

        result = app.handle_request()

        assert result["statusCode"] == 200
        assert result["headers"]["X-Test"] == "middleware-applied"

    def test_cors_basic(self):
        """基本的な CORS 設定のテスト"""
        event = self.create_test_event()
        app = API(event, None)

        app.enable_cors()

        @app.get("/")
        def hello():
            return {"message": "Hello"}

        result = app.handle_request()

        assert result["statusCode"] == 200
        assert "Access-Control-Allow-Origin" in result["headers"]

    def test_cors_options_request(self):
        """CORS プリフライトリクエスト (OPTIONS) のテスト"""
        event = self.create_test_event(method="OPTIONS", path="/")
        event["headers"]["Origin"] = "https://example.com"
        app = API(event, None)

        app.enable_cors(origins=["https://example.com"])

        @app.get("/")
        def hello():
            return {"message": "Hello"}

        result = app.handle_request()

        assert result["statusCode"] == 200
        assert result["headers"]["Access-Control-Allow-Origin"] == "https://example.com"
        assert "Access-Control-Allow-Methods" in result["headers"]

    def test_multiple_middleware(self):
        """複数ミドルウェアのテスト"""
        event = self.create_test_event()
        app = API(event, None)

        def middleware1(request, response):
            if isinstance(response, Response):
                response.headers["X-Middleware-1"] = "applied"
            return response

        def middleware2(request, response):
            if isinstance(response, Response):
                response.headers["X-Middleware-2"] = "applied"
            return response

        app.add_middleware(middleware1)
        app.add_middleware(middleware2)

        @app.get("/")
        def hello():
            return Response({"message": "Hello"})

        result = app.handle_request()

        assert result["statusCode"] == 200
        assert result["headers"]["X-Middleware-1"] == "applied"
        assert result["headers"]["X-Middleware-2"] == "applied"

    def test_error_in_handler(self):
        """ハンドラー内でエラーが発生した場合のテスト"""
        event = self.create_test_event()
        app = API(event, None)

        @app.get("/")
        def error_handler():
            raise ValueError("Test error")

        result = app.handle_request()

        assert result["statusCode"] == 500
        assert "error" in result["body"]

    def test_complex_path_parameters(self):
        """複雑なパスパラメータのテスト"""
        event = self.create_test_event(path="/users/123/posts/456")
        app = API(event, None)

        @app.get("/users/{user_id}/posts/{post_id}")
        def get_user_post(user_id: str, post_id: str):
            return {"user_id": user_id, "post_id": post_id}

        result = app.handle_request()

        assert result["statusCode"] == 200
        assert '"user_id":"123"' in result["body"]
        assert '"post_id":"456"' in result["body"]

    def test_mixed_parameters(self):
        """パスパラメータとクエリパラメータの混在テスト"""
        event = self.create_test_event(
            path="/users/123/posts", query_params={"limit": "10", "sort": "date"}
        )
        app = API(event, None)

        @app.get("/users/{user_id}/posts")
        def get_user_posts(user_id: str, limit: int = 5, sort: str = "id"):
            return {"user_id": user_id, "limit": limit, "sort": sort}

        result = app.handle_request()

        assert result["statusCode"] == 200
        body = result["body"]
        assert '"user_id":"123"' in body
        assert '"limit":10' in body
        assert '"sort":"date"' in body

    def test_request_object_access(self):
        """Request オブジェクトアクセスのテスト"""
        import json

        body_data = {"test": "data"}
        event = self.create_test_event(
            method="POST", path="/test", query_params={"param": "value"}, body=json.dumps(body_data)
        )
        event["headers"]["Custom-Header"] = "custom-value"
        app = API(event, None)

        @app.post("/test")
        def test_request(request):
            return {
                "method": request.method,
                "path": request.path,
                "query_params": request.query_params,
                "headers": dict(request.headers),
                "json_data": request.json(),
                "body": request.body,
            }

        result = app.handle_request()

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["method"] == "POST"
        assert body["path"] == "/test"
        assert body["query_params"]["param"] == "value"
        assert body["headers"]["Custom-Header"] == "custom-value"
        assert body["json_data"] == body_data

    def test_response_object_creation(self):
        """Response オブジェクト作成のテスト"""
        event = self.create_test_event()
        app = API(event, None)

        @app.get("/")
        def custom_response():
            return Response(
                {"message": "Custom response"},
                status_code=201,
                headers={"X-Custom": "header-value"},
            )

        result = app.handle_request()

        assert result["statusCode"] == 201
        assert result["headers"]["X-Custom"] == "header-value"
        assert '"message":"Custom response"' in result["body"]

    def test_different_http_methods(self):
        """異なる HTTP メソッドのテスト"""
        methods_and_paths = [
            ("GET", "/get-test"),
            ("POST", "/post-test"),
            ("PUT", "/put-test"),
            ("DELETE", "/delete-test"),
            ("PATCH", "/patch-test"),
        ]

        for method, path in methods_and_paths:
            event = self.create_test_event(method=method, path=path)
            app = API(event, None)

            if method == "GET":

                @app.get(path)
                def handler():
                    return {"method": method}

            elif method == "POST":

                @app.post(path)
                def handler(request):
                    return {"method": method}

            elif method == "PUT":

                @app.put(path)
                def handler(request):
                    return {"method": method}

            elif method == "DELETE":

                @app.delete(path)
                def handler():
                    return {"method": method}

            elif method == "PATCH":

                @app.patch(path)
                def handler(request):
                    return {"method": method}

            result = app.handle_request()
            assert result["statusCode"] == 200
            assert f'"method":"{method}"' in result["body"]

    def test_type_conversion_edge_cases(self):
        """型変換のエッジケースのテスト"""
        test_cases = [
            # int conversion edge cases
            ({"num": "-5"}, "int", -5),
            ({"num": "0"}, "int", 0),
            ({"num": "invalid"}, "int", 0),  # fallback to 0
            # float conversion
            ({"num": "3.14"}, "float", 3.14),
            ({"num": "-2.5"}, "float", -2.5),
            ({"num": "invalid"}, "float", 0.0),  # fallback to 0.0
            # bool conversion
            ({"flag": "TRUE"}, "bool", True),
            ({"flag": "false"}, "bool", False),
            ({"flag": "yes"}, "bool", True),
            ({"flag": "on"}, "bool", True),
            ({"flag": "anything"}, "bool", False),
        ]

        for query_params, param_type, expected in test_cases:
            event = self.create_test_event(path="/test", query_params=query_params)
            app = API(event, None)

            if param_type == "int":

                @app.get("/test")
                def handler(num: int = 999):
                    return {"value": num, "type": type(num).__name__}

            elif param_type == "float":

                @app.get("/test")
                def handler(num: float = 999.0):
                    return {"value": num, "type": type(num).__name__}

            elif param_type == "bool":

                @app.get("/test")
                def handler(flag: bool = False):
                    return {"value": flag, "type": type(flag).__name__}

            result = app.handle_request()
            assert result["statusCode"] == 200
            body = result["body"]
            assert f'"value":{str(expected).lower()}' in body

    def test_empty_query_parameters(self):
        """空のクエリパラメータのテスト"""
        event = self.create_test_event(path="/test", query_params={})
        app = API(event, None)

        @app.get("/test")
        def handler(param: str = "default"):
            return {"param": param}

        result = app.handle_request()
        assert result["statusCode"] == 200
        assert '"param":"default"' in result["body"]

    def test_none_query_parameters(self):
        """None のクエリパラメータのテスト"""
        event = self.create_test_event(path="/test")
        event["queryStringParameters"] = None
        app = API(event, None)

        @app.get("/test")
        def handler(param: str = "default"):
            return {"param": param}

        result = app.handle_request()
        assert result["statusCode"] == 200
        assert '"param":"default"' in result["body"]

    def test_middleware_exception_handling(self):
        """ミドルウェアで例外が発生した場合のテスト"""
        event = self.create_test_event()
        app = API(event, None)

        def failing_middleware(request, response):
            raise RuntimeError("Middleware error")

        app.add_middleware(failing_middleware)

        @app.get("/")
        def hello():
            return {"message": "Hello"}

        result = app.handle_request()
        assert result["statusCode"] == 500
        assert "error" in result["body"]

    def test_route_not_matching_method(self):
        """ルートは存在するがメソッドが一致しない場合のテスト"""
        event = self.create_test_event(method="POST", path="/")
        app = API(event, None)

        @app.get("/")  # GET only
        def hello():
            return {"message": "Hello"}

        result = app.handle_request()
        assert result["statusCode"] == 404

    def test_json_response_encoding(self):
        """JSON レスポンスエンコーディングのテスト"""
        event = self.create_test_event()
        app = API(event, None)

        @app.get("/")
        def unicode_response():
            return {"message": "こんにちは", "emoji": "🚀", "number": 42}

        result = app.handle_request()
        assert result["statusCode"] == 200
        assert (
            "こんにちは" in result["body"]
            or "\\u3053\\u3093\\u306b\\u3061\\u306f" in result["body"]
        )
        assert "🚀" in result["body"] or "\\ud83d\\ude80" in result["body"]


if __name__ == "__main__":
    # pytest がない環境でも実行できるように直接テストを実行
    test_class = TestAPI()

    tests = [
        test_class.test_basic_get_route,
        test_class.test_path_parameters,
        test_class.test_query_parameters,
        test_class.test_query_parameters_default_values,
        test_class.test_type_conversion,
        test_class.test_post_request,
        test_class.test_not_found,
        test_class.test_middleware,
    ]

    print("Running Lambda API tests...")

    for i, test in enumerate(tests, 1):
        try:
            test()
            print(f"✓ Test {i}: {test.__name__} - PASSED")
        except Exception as e:
            print(f"✗ Test {i}: {test.__name__} - FAILED: {e}")

    print("All tests completed!")
