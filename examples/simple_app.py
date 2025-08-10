#!/usr/bin/env python3
"""
シンプルな Lambda API 使用例

最小限の設定でモダンな API を作成します。
"""

import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lambapi import API, Response, create_lambda_handler


def create_app(event, context):
    """シンプルなアプリケーション作成"""
    app = API(event, context)

    @app.get("/")
    def hello():
        return {"message": "Hello, Lambda API!"}

    @app.get("/users/{user_id}")
    def get_user(user_id: str):
        return {"user_id": user_id, "name": f"User {user_id}"}

    @app.get("/search")
    def search(q: str = "", limit: int = 10):
        return {"query": q, "limit": limit, "results": []}

    @app.post("/users")
    def create_user(request):
        user_data = request.json()
        return Response({"message": "User created", "user": user_data}, status_code=201)

    return app


# Lambda handler
lambda_handler = create_lambda_handler(create_app)


if __name__ == "__main__":
    # ローカルテスト
    test_events = [
        {
            "httpMethod": "GET",
            "path": "/",
            "queryStringParameters": None,
            "headers": {},
            "body": None,
        },
        {
            "httpMethod": "GET",
            "path": "/users/alice",
            "queryStringParameters": None,
            "headers": {},
            "body": None,
        },
        {
            "httpMethod": "GET",
            "path": "/search",
            "queryStringParameters": {"q": "python", "limit": "5"},
            "headers": {},
            "body": None,
        },
    ]

    for i, event in enumerate(test_events, 1):
        print(f"=== Test {i}: {event['httpMethod']} {event['path']} ===")
        result = lambda_handler(event, None)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        print()
