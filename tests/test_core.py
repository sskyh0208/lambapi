"""
API コアクラスのテスト
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lambapi import API, Response, create_lambda_handler


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
        assert '"message": "Hello World"' in result["body"]

    def test_path_parameters(self):
        """パスパラメータのテスト"""
        event = self.create_test_event(path="/users/123")
        app = API(event, None)

        @app.get("/users/{user_id}")
        def get_user(user_id: str):
            return {"user_id": user_id}

        result = app.handle_request()

        assert result["statusCode"] == 200
        assert '"user_id": "123"' in result["body"]

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
        assert '"query": "python"' in body
        assert '"limit": 10' in body

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
        assert '"query": "default"' in body
        assert '"limit": 5' in body

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
        assert '"limit": 25' in body
        assert '"offset": 10' in body
        assert '"active": true' in body

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
        assert '"message": "Created"' in result["body"]
        assert '"name": "John"' in result["body"]

    def test_not_found(self):
        """404 エラーのテスト"""
        event = self.create_test_event(path="/nonexistent")
        app = API(event, None)

        @app.get("/")
        def hello():
            return {"message": "Hello"}

        result = app.handle_request()

        assert result["statusCode"] == 404
        assert '"error": "Not Found"' in result["body"]

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
