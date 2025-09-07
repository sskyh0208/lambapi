"""
CORS 機能のテスト
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lambapi import API, create_cors_config


class TestCORS:
    """CORS 機能のテスト"""

    def create_test_event(self, method="GET", path="/", query_params=None, body=None, headers=None):
        """テスト用のイベントを作成"""
        default_headers = {"Content-Type": "application/json"}
        if headers:
            default_headers.update(headers)

        return {
            "httpMethod": method,
            "path": path,
            "queryStringParameters": query_params,
            "headers": default_headers,
            "body": body,
        }

    def test_cors_config_creation(self):
        """CORS 設定の作成テスト"""
        # デフォルト設定
        config = create_cors_config()
        assert config.origins == "*"
        assert "GET" in config.methods
        assert "POST" in config.methods
        assert "Content-Type" in config.headers

        # カスタム設定
        config = create_cors_config(
            origins=["https://example.com"],
            methods=["GET", "POST"],
            headers=["Content-Type", "Authorization"],
            allow_credentials=True,
            max_age=3600,
        )
        assert config.origins == ["https://example.com"]
        assert config.methods == ["GET", "POST"]
        assert config.allow_credentials is True
        assert config.max_age == 3600

    def test_cors_headers_generation(self):
        """CORS ヘッダー生成のテスト"""
        config = create_cors_config(
            origins=["https://example.com", "https://test.com"],
            methods=["GET", "POST"],
            headers=["Content-Type", "Authorization"],
            allow_credentials=True,
            max_age=3600,
        )

        # 許可されたオリジンのテスト
        headers = config.get_cors_headers("https://example.com")
        assert headers["Access-Control-Allow-Origin"] == "https://example.com"
        assert headers["Access-Control-Allow-Methods"] == "GET, POST"
        assert headers["Access-Control-Allow-Headers"] == "Content-Type, Authorization"
        assert headers["Access-Control-Allow-Credentials"] == "true"
        assert headers["Access-Control-Max-Age"] == "3600"

        # 許可されていないオリジンのテスト
        headers = config.get_cors_headers("https://unauthorized.com")
        assert headers["Access-Control-Allow-Origin"] == "https://example.com"  # 最初のオリジン

    def test_global_cors_enable(self):
        """グローバル CORS 有効化のテスト"""
        event = self.create_test_event(headers={"Origin": "https://example.com"})
        app = API(event, None)

        # CORS を有効化
        app.enable_cors(origins="https://example.com")

        @app.get("/")
        def hello():
            return {"message": "Hello"}

        result = app.handle_request()

        assert result["statusCode"] == 200
        assert result["headers"]["Access-Control-Allow-Origin"] == "https://example.com"
        assert "Access-Control-Allow-Methods" in result["headers"]
        assert "Access-Control-Allow-Headers" in result["headers"]

    def test_options_preflight_handling(self):
        """OPTIONS プリフライトリクエストの自動処理テスト"""
        event = self.create_test_event(
            method="OPTIONS", path="/users", headers={"Origin": "https://example.com"}
        )
        app = API(event, None)

        # CORS を有効化
        app.enable_cors(origins="https://example.com")

        @app.get("/users")
        def get_users():
            return {"users": []}

        result = app.handle_request()

        assert result["statusCode"] == 200
        assert result["headers"]["Access-Control-Allow-Origin"] == "https://example.com"
        assert (
            result["headers"]["Access-Control-Allow-Methods"]
            == "GET, POST, PUT, DELETE, PATCH, OPTIONS"
        )
        assert result["body"] == ""  # OPTIONS レスポンスは空

    def test_route_level_cors(self):
        """ルートレベル CORS 設定のテスト"""
        event = self.create_test_event(headers={"Origin": "https://example.com"})
        app = API(event, None)

        # 個別ルートに CORS 設定
        @app.get("/", cors=True)
        def hello():
            return {"message": "Hello"}

        @app.get("/no-cors")
        def no_cors():
            return {"message": "No CORS"}

        result = app.handle_request()

        assert result["statusCode"] == 200
        assert "Access-Control-Allow-Origin" in result["headers"]

    def test_route_level_custom_cors(self):
        """ルートレベル カスタム CORS 設定のテスト"""
        event = self.create_test_event(path="/custom", headers={"Origin": "https://custom.com"})
        app = API(event, None)

        # カスタム CORS 設定
        custom_cors = create_cors_config(
            origins=["https://custom.com"], methods=["GET"], allow_credentials=True
        )

        @app.get("/custom", cors=custom_cors)
        def custom_endpoint():
            return {"message": "Custom CORS"}

        result = app.handle_request()

        assert result["statusCode"] == 200
        assert result["headers"]["Access-Control-Allow-Origin"] == "https://custom.com"
        assert result["headers"]["Access-Control-Allow-Methods"] == "GET"
        assert result["headers"]["Access-Control-Allow-Credentials"] == "true"

    def test_cors_with_error_responses(self):
        """エラーレスポンスでの CORS ヘッダーテスト"""
        event = self.create_test_event(
            path="/nonexistent", headers={"Origin": "https://example.com"}
        )
        app = API(event, None)

        app.enable_cors(origins="https://example.com")

        @app.get("/")
        def hello():
            return {"message": "Hello"}

        result = app.handle_request()

        assert result["statusCode"] == 404
        assert result["headers"]["Access-Control-Allow-Origin"] == "https://example.com"

    def test_cors_priority(self):
        """CORS 設定の優先度テスト（ルートレベル > グローバル）"""
        event = self.create_test_event(headers={"Origin": "https://example.com"})
        app = API(event, None)

        # グローバル CORS 設定
        app.enable_cors(origins="https://global.com")

        # ルートレベル CORS 設定（こちらが優先される）
        route_cors = create_cors_config(origins=["https://route.com"])

        @app.get("/", cors=route_cors)
        def hello():
            return {"message": "Hello"}

        result = app.handle_request()

        assert result["statusCode"] == 200
        # ルートレベルの設定が優先される
        assert result["headers"]["Access-Control-Allow-Origin"] == "https://route.com"


if __name__ == "__main__":
    # pytest がない環境でも実行できるように直接テストを実行
    test_class = TestCORS()

    tests = [
        test_class.test_cors_config_creation,
        test_class.test_cors_headers_generation,
        test_class.test_global_cors_enable,
        test_class.test_options_preflight_handling,
        test_class.test_route_level_cors,
        test_class.test_route_level_custom_cors,
        test_class.test_cors_with_error_responses,
        test_class.test_cors_priority,
    ]

    print("Running CORS tests...")

    for i, test in enumerate(tests, 1):
        try:
            test()
            print(f"✓ Test {i}: {test.__name__} - PASSED")
        except Exception as e:
            print(f"✗ Test {i}: {test.__name__} - FAILED: {e}")

    print("All CORS tests completed!")
