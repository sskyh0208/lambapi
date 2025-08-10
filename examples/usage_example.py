#!/usr/bin/env python3
"""
lambapi の使用例
pip install lambapi 後の基本的な使用方法を示すサンプル
"""

from lambapi import API, Response, create_lambda_handler, serve
from lambapi.exceptions import ValidationError, NotFoundError


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
            "message": "Welcome to lambapi!",
            "version": "1.0.0",
            "usage": "Use lambapi serve usage_example to run locally",
        }

    @app.get("/users")
    def get_users(limit: int = 10):
        user_list = list(users.values())[:limit]
        return {"users": user_list, "total": len(user_list)}

    @app.get("/users/{user_id}")
    def get_user(user_id: str):
        if user_id not in users:
            raise NotFoundError("User", user_id)
        return {"user": users[user_id]}

    @app.post("/users")
    def create_user(request):
        data = request.json()

        if not data.get("name"):
            raise ValidationError("Name is required", field="name")

        user_id = str(len(users) + 1)
        user = {
            "id": user_id,
            "name": data["name"],
            "email": data.get("email", f"user{user_id}@example.com"),
        }
        users[user_id] = user

        return Response({"message": "User created", "user": user}, status_code=201)

    return app


# Lambda エントリーポイント
lambda_handler = create_lambda_handler(create_app)


if __name__ == "__main__":
    print(
        """
🚀 lambapi 使用例

ローカルサーバーで起動するには:
  lambapi serve usage_example

または Python から直接:
  from lambapi import serve
  serve('usage_example')

テスト用の curl コマンド:
  curl http://localhost:8000/
  curl http://localhost:8000/users
  curl -X POST http://localhost:8000/users \\
       -H "Content-Type: application/json" -d '{"name":"Test User"}'
"""
    )

    # Python から直接起動する場合のデモ
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--serve":
        serve(__file__)
