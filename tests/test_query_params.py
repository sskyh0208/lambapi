#!/usr/bin/env python3
"""
モダンなクエリパラメータ記法のテスト
"""

import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lambapi import API, create_lambda_handler


def create_test_app(event, context):
    """テスト用アプリケーション"""
    app = API(event, context)

    # モダンな記法（クエリパラメータのみ）
    @app.get("/search")
    def search_items(q: str = ""):
        return {"query": q, "method": "search"}

    # 型アノテーション付きクエリパラメータ
    @app.get("/items")
    def get_items(limit: int = 10, offset: int = 0, active: bool = True):
        return {
            "limit": limit,
            "offset": offset,
            "active": active,
            "type_info": {
                "limit": type(limit).__name__,
                "offset": type(offset).__name__,
                "active": type(active).__name__,
            },
        }

    # パスパラメータ + クエリパラメータ
    @app.get("/users/{user_id}/posts")
    def get_user_posts(user_id: str, limit: int = 10, sort: str = "created_at"):
        return {
            "user_id": user_id,
            "limit": limit,
            "sort": sort,
            "posts": [f"post-{i}" for i in range(1, limit + 1)],
        }

    # 混合パターン（パスパラメータ + クエリパラメータ + request）
    @app.get("/categories/{category}/products")
    def get_category_products(category: str, limit: int = 20, min_price: float = 0.0, request=None):
        result = {
            "category": category,
            "limit": limit,
            "min_price": min_price,
            "type_info": {"limit": type(limit).__name__, "min_price": type(min_price).__name__},
        }

        # request がある場合の追加情報
        if request:
            result["has_request"] = True
            result["method"] = request.method

        return result

    # 簡易な記法
    @app.get("/legacy/search")
    def legacy_search(request):
        query = request.query_params.get("q", "")
        limit = int(request.query_params.get("limit", "5"))
        return {"query": query, "limit": limit, "method": "legacy"}

    return app


# Lambda handler
lambda_handler = create_lambda_handler(create_test_app)


if __name__ == "__main__":
    # テスト 1: 基本的なクエリパラメータ
    test_event_1 = {
        "httpMethod": "GET",
        "path": "/search",
        "queryStringParameters": {"q": "python"},
        "headers": {},
        "body": None,
    }

    print("=== Test 1: Basic query param ===")
    result1 = lambda_handler(test_event_1, None)
    print(json.dumps(result1, indent=2, ensure_ascii=False))

    # テスト 2: 型変換付きクエリパラメータ
    test_event_2 = {
        "httpMethod": "GET",
        "path": "/items",
        "queryStringParameters": {"limit": "25", "offset": "50", "active": "false"},
        "headers": {},
        "body": None,
    }

    print("\n=== Test 2: Type conversion ===")
    result2 = lambda_handler(test_event_2, None)
    print(json.dumps(result2, indent=2, ensure_ascii=False))

    # テスト 3: デフォルト値の使用
    test_event_3 = {
        "httpMethod": "GET",
        "path": "/items",
        "queryStringParameters": None,
        "headers": {},
        "body": None,
    }

    print("\n=== Test 3: Default values ===")
    result3 = lambda_handler(test_event_3, None)
    print(json.dumps(result3, indent=2, ensure_ascii=False))

    # テスト 4: パスパラメータ + クエリパラメータ
    test_event_4 = {
        "httpMethod": "GET",
        "path": "/users/alice/posts",
        "queryStringParameters": {"limit": "5", "sort": "updated_at"},
        "headers": {},
        "body": None,
    }

    print("\n=== Test 4: Path + Query params ===")
    result4 = lambda_handler(test_event_4, None)
    print(json.dumps(result4, indent=2, ensure_ascii=False))

    # テスト 5: 混合パターン
    test_event_5 = {
        "httpMethod": "GET",
        "path": "/categories/electronics/products",
        "queryStringParameters": {"limit": "15", "min_price": "99.99"},
        "headers": {},
        "body": None,
    }

    print("\n=== Test 5: Mixed pattern ===")
    result5 = lambda_handler(test_event_5, None)
    print(json.dumps(result5, indent=2, ensure_ascii=False))

    # テスト 6:簡易な記法
    test_event_6 = {
        "httpMethod": "GET",
        "path": "/legacy/search",
        "queryStringParameters": {"q": "api", "limit": "3"},
        "headers": {},
        "body": None,
    }

    print("\n=== Test 6: Legacy syntax ===")
    result6 = lambda_handler(test_event_6, None)
    print(json.dumps(result6, indent=2, ensure_ascii=False))
