"""
基本的な lambapi アプリケーション
"""

from typing import Dict, Any
from lambapi import API, create_lambda_handler


def create_app(event: Dict[str, Any], context: Any) -> API:
    app = API(event, context)

    @app.get("/")
    def root() -> Dict[str, str]:
        return {"message": "Hello, lambapi!", "version": "1.0.0"}

    @app.get("/hello/{name}")
    def hello(name: str) -> Dict[str, str]:
        return {"message": f"Hello, {name}!"}

    return app


# Lambda エントリーポイント
lambda_handler = create_lambda_handler(create_app)


if __name__ == "__main__":
    # ローカルテスト用
    test_event: Dict[str, Any] = {
        "httpMethod": "GET",
        "path": "/",
        "queryStringParameters": {},
        "headers": {},
        "body": None,
    }

    context = type("Context", (), {"aws_request_id": "test-123"})()
    result = lambda_handler(test_event, context)
    print(result)
