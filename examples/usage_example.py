#!/usr/bin/env python3
"""
lambapi v0.2.x の使用例
統合アノテーションシステムと自動推論機能を使った基本的なサンプル
"""

from lambapi import API, Response, create_lambda_handler, serve
from lambapi.annotations import Body, Path, Query
from lambapi.exceptions import ValidationError, NotFoundError
from dataclasses import dataclass
from typing import Optional


@dataclass
class CreateUserRequest:
    name: str
    email: Optional[str] = None


@dataclass
class User:
    id: str
    name: str
    email: str


def create_app(event, context):
    app = API(event, context)

    # サンプルデータ
    users = {
        "1": {"id": "1", "name": "Alice", "email": "alice@example.com"},
        "2": {"id": "2", "name": "Bob", "email": "bob@example.com"},
    }

    @app.get("/")
    def root():
        return {
            "message": "Welcome to lambapi v0.2.x!",
            "version": "2.0.x",
            "features": ["統合アノテーションシステム", "自動推論機能", "型安全性"],
            "usage": "Use lambapi serve usage_example to run locally",
        }

    # 自動推論: limit と search は自動的に Query パラメータとして扱われる
    @app.get("/users")
    def get_users(limit: int = 10, search: Optional[str] = None):
        user_list = list(users.values())

        # 検索フィルタリング
        if search:
            user_list = [u for u in user_list if search.lower() in u["name"].lower()]

        # ページネーション
        user_list = user_list[:limit]
        return {"users": user_list, "total": len(user_list), "search": search, "limit": limit}

    # 自動推論: user_id は自動的に Path パラメータとして扱われる
    @app.get("/users/{user_id}")
    def get_user(user_id: str):
        if user_id not in users:
            raise NotFoundError("User", user_id)
        return {"user": users[user_id]}

    # 明示的アノテーション版
    @app.get("/api/users/{user_id}")
    def get_user_explicit(user_id: str = Path()):
        if user_id not in users:
            raise NotFoundError("User", user_id)
        return {"user": users[user_id]}

    # 自動推論: CreateUserRequest は自動的に Body パラメータとして扱われる
    @app.post("/users")
    def create_user(user_request: CreateUserRequest):
        if not user_request.name.strip():
            raise ValidationError("Name is required", field="name")

        user_id = str(len(users) + 1)
        email = user_request.email or f"user{user_id}@example.com"

        user = {
            "id": user_id,
            "name": user_request.name,
            "email": email,
        }
        users[user_id] = user

        return Response({"message": "User created", "user": user}, status_code=201)

    # 明示的アノテーション版
    @app.post("/api/users")
    def create_user_explicit(user_request: CreateUserRequest = Body()):
        user_id = str(len(users) + 1)
        email = user_request.email or f"user{user_id}@example.com"

        user = {
            "id": user_id,
            "name": user_request.name,
            "email": email,
        }
        users[user_id] = user

        return Response({"message": "User created (explicit)", "user": user}, status_code=201)

    # 混合アノテーション版
    @app.put("/users/{user_id}")
    def update_user(
        user_id: str = Path(),  # 明示的 Path
        user_request: CreateUserRequest = Body(),  # 明示的 Body
        version: str = Query(default="v1"),  # 明示的 Query
    ):
        if user_id not in users:
            raise NotFoundError("User", user_id)

        users[user_id]["name"] = user_request.name
        if user_request.email:
            users[user_id]["email"] = user_request.email

        return {"message": "User updated", "user": users[user_id], "version": version}

    return app


# Lambda エントリーポイント
lambda_handler = create_lambda_handler(create_app)


if __name__ == "__main__":
    print(
        """
🚀 lambapi v0.2.x 使用例

ローカルサーバーで起動するには:
  lambapi serve usage_example

または Python から直接:
  from lambapi import serve
  serve('usage_example')

テスト用の curl コマンド（v0.2.x 新機能）:
  # 基本機能
  curl http://localhost:8000/
  curl http://localhost:8000/users
  curl "http://localhost:8000/users?limit=5&search=alice"

  # 自動推論版の API
  curl -X POST http://localhost:8000/users \\
       -H "Content-Type: application/json" -d '{"name":"Test User"}'

  # 明示的アノテーション版の API
  curl -X POST http://localhost:8000/api/users \\
       -H "Content-Type: application/json" -d '{"name":"Test User API"}'

  # 混合アノテーション版
  curl -X PUT "http://localhost:8000/users/1?version=v2" \\
       -H "Content-Type: application/json" -d '{"name":"Updated User"}'
"""
    )

    # Python から直接起動する場合のデモ
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--serve":
        serve(__file__)
