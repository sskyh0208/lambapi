#!/usr/bin/env python3
"""
新しいパスパラメータ記法のテスト
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from lambapi import API, create_lambda_handler


def create_test_app(event, context):
    """テスト用アプリケーション"""
    app = API(event, context)

    # モダンな記法（パスパラメータのみ）
    @app.get("/users/{user_id}")
    def get_user(user_id: str):
        return {"user_id": user_id, "method": "GET"}

    # モダンな記法（パスパラメータ + request）
    @app.put("/users/{user_id}")
    def update_user(user_id: str, request):
        return {"user_id": user_id, "method": "PUT", "body": request.json()}

    # 複数のパスパラメータ
    @app.get("/users/{user_id}/posts/{post_id}")
    def get_user_post(user_id: str, post_id: str):
        return {"user_id": user_id, "post_id": post_id, "method": "GET"}

    # 簡易な記法
    @app.get("/legacy/{item_id}")
    def get_legacy_item(request):
        item_id = request.path_params.get("item_id")
        return {"item_id": item_id, "method": "legacy"}

    return app


# Lambda handler
lambda_handler = create_lambda_handler(create_test_app)


if __name__ == "__main__":
    # テスト 1: パスパラメータのみ
    test_event_1 = {
        "httpMethod": "GET",
        "path": "/users/alice",
        "queryStringParameters": None,
        "headers": {},
        "body": None,
    }

    print("=== Test 1: Path param only ===")
    result1 = lambda_handler(test_event_1, None)
    print(json.dumps(result1, indent=2, ensure_ascii=False))

    # テスト 2: パスパラメータ + request
    test_event_2 = {
        "httpMethod": "PUT",
        "path": "/users/bob",
        "queryStringParameters": None,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"name": "Bob Smith", "age": 30}),
    }

    print("\n=== Test 2: Path param + request ===")
    result2 = lambda_handler(test_event_2, None)
    print(json.dumps(result2, indent=2, ensure_ascii=False))

    # テスト 3: 複数のパスパラメータ
    test_event_3 = {
        "httpMethod": "GET",
        "path": "/users/charlie/posts/123",
        "queryStringParameters": None,
        "headers": {},
        "body": None,
    }

    print("\n=== Test 3: Multiple path params ===")
    result3 = lambda_handler(test_event_3, None)
    print(json.dumps(result3, indent=2, ensure_ascii=False))

    # テスト 4: 簡易な記法
    test_event_4 = {
        "httpMethod": "GET",
        "path": "/legacy/old-item",
        "queryStringParameters": None,
        "headers": {},
        "body": None,
    }

    print("\n=== Test 4: Legacy syntax ===")
    result4 = lambda_handler(test_event_4, None)
    print(json.dumps(result4, indent=2, ensure_ascii=False))
