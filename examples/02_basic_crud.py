"""
02. 基本的な CRUD API - 実用的なデータ操作

データクラス、バリデーション、エラーハンドリングを含む
実際のアプリケーションに近い CRUD API のサンプルです。
"""

from dataclasses import dataclass
from typing import Optional, List
from lambapi import API, Response, create_lambda_handler
from lambapi.annotations import Body, Path, Query


@dataclass
class User:
    """ユーザーデータクラス"""

    name: str
    email: str
    age: Optional[int] = None


def create_app(event, context):
    app = API(event, context)

    # メモリ上のデータ（実際の開発では DB を使用）
    users_db = {
        1: {"id": 1, "name": "Alice", "email": "alice@example.com", "age": 25},
        2: {"id": 2, "name": "Bob", "email": "bob@example.com", "age": 30},
    }

    @app.get("/users")
    def list_users(limit: int = 10, search: Optional[str] = None):
        """ユーザー一覧取得（自動推論でクエリパラメータ）"""
        users = list(users_db.values())

        # 検索フィルター
        if search:
            users = [u for u in users if search.lower() in u["name"].lower()]

        return {"users": users[:limit], "total": len(users), "limit": limit}

    @app.get("/users/{user_id}")
    def get_user(user_id: int):
        """個別ユーザー取得（自動推論でパスパラメータ）"""
        if user_id not in users_db:
            return Response({"error": "User not found"}, status_code=404)

        return {"user": users_db[user_id]}

    @app.post("/users")
    def create_user(user: User):
        """ユーザー作成（自動推論でボディパラメータ）"""
        new_id = max(users_db.keys()) + 1 if users_db else 1
        new_user = {"id": new_id, "name": user.name, "email": user.email, "age": user.age}
        users_db[new_id] = new_user

        return Response({"message": "User created", "user": new_user}, status_code=201)

    @app.put("/users/{user_id}")
    def update_user(user_id: int, user: User = Body()):
        """ユーザー更新（混合パラメータ：Path + Body）"""
        if user_id not in users_db:
            return Response({"error": "User not found"}, status_code=404)

        users_db[user_id].update({"name": user.name, "email": user.email, "age": user.age})

        return {"message": "User updated", "user": users_db[user_id]}

    @app.delete("/users/{user_id}")
    def delete_user(user_id: int):
        """ユーザー削除"""
        if user_id not in users_db:
            return Response({"error": "User not found"}, status_code=404)

        deleted_user = users_db.pop(user_id)
        return {"message": "User deleted", "user": deleted_user}

    return app


lambda_handler = create_lambda_handler(create_app)


if __name__ == "__main__":
    # CRUD 操作のテスト
    print("=== CRUD API テスト ===")

    import json

    def test_request(method, path, body=None, query=None):
        event = {
            "httpMethod": method,
            "path": path,
            "queryStringParameters": query,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(body) if body else None,
        }
        result = lambda_handler(event, None)
        print(f"{method} {path}: {result['statusCode']} - {json.loads(result['body'])}")

    # テストシーケンス
    test_request("GET", "/users")
    test_request("GET", "/users/1")
    test_request("POST", "/users", {"name": "Charlie", "email": "charlie@example.com", "age": 28})
    test_request("GET", "/users", query={"search": "alice"})
    test_request(
        "PUT",
        "/users/1",
        {"name": "Alice Updated", "email": "alice.updated@example.com", "age": 26},
    )
    test_request("DELETE", "/users/2")
    test_request("GET", "/users/999")  # 404 テスト
