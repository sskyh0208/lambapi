"""
ローカルサーバーテスト用のサンプルアプリケーション
"""

from lambapi import API, Response, create_lambda_handler
from lambapi.exceptions import ValidationError, NotFoundError


def create_app(event, context):
    app = API(event, context)

    # サンプルデータストア
    users_db = {
        "1": {"id": "1", "name": "Alice", "email": "alice@example.com"},
        "2": {"id": "2", "name": "Bob", "email": "bob@example.com"},
        "3": {"id": "3", "name": "Charlie", "email": "charlie@example.com"},
    }

    @app.get("/")
    def root():
        """API のルートエンドポイント"""
        return {
            "message": "lambapi ローカルサーバーへようこそ！",
            "version": "1.0.0",
            "endpoints": [
                "GET /",
                "GET /hello/{name}",
                "GET /users",
                "POST /users",
                "GET /users/{user_id}",
                "PUT /users/{user_id}",
                "DELETE /users/{user_id}",
            ],
        }

    @app.get("/hello/{name}")
    def hello(name: str, lang: str = "ja"):
        """多言語対応の挨拶エンドポイント"""
        greetings = {
            "ja": f"こんにちは、{name}さん！",
            "en": f"Hello, {name}!",
            "es": f"¡Hola, {name}!",
        }
        return {"message": greetings.get(lang, greetings["en"]), "name": name, "language": lang}

    @app.get("/users")
    def get_users(limit: int = 10, search: str = ""):
        """ユーザー一覧取得"""
        users = list(users_db.values())

        # 検索フィルター
        if search:
            users = [
                user
                for user in users
                if search.lower() in user["name"].lower() or search.lower() in user["email"].lower()
            ]

        # リミット適用
        users = users[:limit]

        return {
            "users": users,
            "total": len(users),
            "limit": limit,
            "search": search if search else None,
        }

    @app.get("/users/{user_id}")
    def get_user(user_id: str):
        """特定ユーザー取得"""
        if user_id not in users_db:
            raise NotFoundError("User", user_id)

        return {"user": users_db[user_id]}

    @app.post("/users")
    def create_user(request):
        """新しいユーザー作成"""
        data = request.json()

        # バリデーション
        if not data.get("name"):
            raise ValidationError("Name is required", field="name")
        if not data.get("email"):
            raise ValidationError("Email is required", field="email")

        # 新しいユーザー ID を生成
        new_id = str(len(users_db) + 1)

        user = {"id": new_id, "name": data["name"], "email": data["email"]}

        users_db[new_id] = user

        return Response({"message": "User created successfully", "user": user}, status_code=201)

    @app.put("/users/{user_id}")
    def update_user(user_id: str, request):
        """ユーザー更新"""
        if user_id not in users_db:
            raise NotFoundError("User", user_id)

        data = request.json()
        user = users_db[user_id]

        # 更新可能なフィールドのみ処理
        if "name" in data:
            user["name"] = data["name"]
        if "email" in data:
            user["email"] = data["email"]

        return {"message": "User updated successfully", "user": user}

    @app.delete("/users/{user_id}")
    def delete_user(user_id: str):
        """ユーザー削除"""
        if user_id not in users_db:
            raise NotFoundError("User", user_id)

        deleted_user = users_db.pop(user_id)

        return {
            "message": f"User {deleted_user['name']} deleted successfully",
            "deleted_user_id": user_id,
        }

    return app


# Lambda エントリーポイント
lambda_handler = create_lambda_handler(create_app)


if __name__ == "__main__":
    # ローカルテスト用の簡単な実行
    import json

    test_event = {
        "httpMethod": "GET",
        "path": "/",
        "queryStringParameters": {},
        "headers": {},
        "body": None,
    }

    context = type("Context", (), {"aws_request_id": "test-123"})()

    result = lambda_handler(test_event, context)
    print(json.dumps(result, indent=2, ensure_ascii=False))
