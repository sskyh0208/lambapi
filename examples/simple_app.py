#!/usr/bin/env python3
"""
シンプルな Lambda API 使用例（v0.2.x）

最小限の設定でモダンな API を作成します。
統合アノテーションシステムと自動推論機能を使用。
"""

import json
import sys
import os
from dataclasses import dataclass
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lambapi import API, Response, create_lambda_handler
from lambapi.annotations import Body, Path, Query


@dataclass
class UserCreateRequest:
    name: str
    email: str
    age: Optional[int] = None


def create_app(event, context):
    """シンプルなアプリケーション作成（v0.2.x 版）"""
    app = API(event, context)

    @app.get("/")
    def hello():
        return {
            "message": "Hello, Lambda API v0.2.x!",
            "features": ["自動推論", "アノテーション", "型安全性"],
        }

    # 自動推論: user_id は自動的に Path パラメータ
    @app.get("/users/{user_id}")
    def get_user(user_id: str):
        return {"user_id": user_id, "name": f"User {user_id}"}

    # 自動推論: q と limit は自動的に Query パラメータ
    @app.get("/search")
    def search(q: str = "", limit: int = 10):
        return {
            "query": q,
            "limit": limit,
            "results": [f"result-{i}" for i in range(1, min(limit, 5) + 1)],
        }

    # 自動推論: UserCreateRequest は自動的に Body パラメータ
    @app.post("/users")
    def create_user(user_data: UserCreateRequest):
        return Response(
            {
                "message": "User created",
                "user": {"name": user_data.name, "email": user_data.email, "age": user_data.age},
            },
            status_code=201,
        )

    # 明示的アノテーション版の例
    @app.put("/users/{user_id}")
    def update_user(
        user_id: str = Path(),
        user_data: UserCreateRequest = Body(),
        version: str = Query(default="v1"),
    ):
        return {
            "message": f"User {user_id} updated",
            "user": {"name": user_data.name, "email": user_data.email, "age": user_data.age},
            "version": version,
        }

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
        {
            "httpMethod": "POST",
            "path": "/users",
            "queryStringParameters": None,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"name": "Test User", "email": "test@example.com", "age": 25}),
        },
        {
            "httpMethod": "PUT",
            "path": "/users/123",
            "queryStringParameters": {"version": "v2"},
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"name": "Updated User", "email": "updated@example.com"}),
        },
    ]

    for i, event in enumerate(test_events, 1):
        print(f"=== Test {i}: {event['httpMethod']} {event['path']} ===")
        result = lambda_handler(event, None)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        print()
