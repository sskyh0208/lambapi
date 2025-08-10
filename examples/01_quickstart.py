"""
01. クイックスタート - 最もシンプルな lambapi の使い方

lambapi の基本的な使い方を 5 分で理解できるサンプルです。
"""

from lambapi import API, create_lambda_handler


def create_app(event, context):
    app = API(event, context)

    @app.get("/")
    def hello():
        """シンプルな Hello World"""
        return {"message": "Hello, lambapi v0.2.x!"}

    @app.get("/users/{user_id}")
    def get_user(user_id: int):  # 自動的に Path パラメータとして推論
        return {"user_id": user_id, "name": f"User {user_id}"}

    @app.get("/search")
    def search(q: str = ""):  # 自動的に Query パラメータとして推論
        return {"query": q, "results": [f"result for {q}"]}

    return app


# Lambda エントリーポイント
lambda_handler = create_lambda_handler(create_app)


if __name__ == "__main__":
    # ローカルテスト
    print("=== lambapi クイックスタート テスト ===")

    import json

    # テスト 1: Hello World
    event = {
        "httpMethod": "GET",
        "path": "/",
        "queryStringParameters": None,
        "headers": {},
        "body": None,
    }
    result = lambda_handler(event, None)
    print(f"GET /: {json.loads(result['body'])}")

    # テスト 2: パスパラメータ
    event["path"] = "/users/123"
    result = lambda_handler(event, None)
    print(f"GET /users/123: {json.loads(result['body'])}")

    # テスト 3: クエリパラメータ
    event["path"] = "/search"
    event["queryStringParameters"] = {"q": "lambapi"}
    result = lambda_handler(event, None)
    print(f"GET /search?q=lambapi: {json.loads(result['body'])}")
