# クイックスタート

lambapi を使って最初の API を構築しましょう。このガイドでは、5 分で動作する API を作成できます。

## 前提条件

- Python 3.7 以上
- AWS Lambda の基本的な知識（任意）

## インストール

```bash
pip install lambapi
```

## 最初の API

### 1. 基本的な Hello World API

```python title="app.py"
from lambapi import API, create_lambda_handler

def create_app(event, context):
    app = API(event, context)

    @app.get("/")
    def hello():
        return {"message": "Hello, lambapi!"}

    return app

# Lambda エントリーポイント
lambda_handler = create_lambda_handler(create_app)
```

### 2. パスパラメータの使用

```python title="app.py"
@app.get("/hello/{name}")
def hello_name(name: str):
    return {"message": f"Hello, {name}!"}
```

### 3. クエリパラメータとデフォルト値

```python title="app.py"
@app.get("/search")
def search(q: str = "", limit: int = 10, sort: str = "name"):
    return {
        "query": q,
        "limit": limit,
        "sort": sort,
        "results": [f"item-{i}" for i in range(1, limit + 1)]
    }
```

### 4. 複数の HTTP メソッド

```python title="app.py"
@app.post("/users")
def create_user(request):
    user_data = request.json()
    return {
        "message": "User created",
        "user": user_data
    }

@app.put("/users/{user_id}")
def update_user(user_id: str, request):
    user_data = request.json()
    return {
        "message": f"User {user_id} updated",
        "user": user_data
    }

@app.delete("/users/{user_id}")
def delete_user(user_id: str):
    return {"message": f"User {user_id} deleted"}
```

## 完全な例

```python title="complete_app.py"
from lambapi import API, Response, create_lambda_handler

def create_app(event, context):
    app = API(event, context)

    # ルートエンドポイント
    @app.get("/")
    def root():
        return {
            "name": "My API",
            "version": "1.0.0",
            "endpoints": [
                "GET /",
                "GET /hello/{name}",
                "GET /users",
                "POST /users",
                "GET /users/{id}"
            ]
        }

    # 挨拶エンドポイント
    @app.get("/hello/{name}")
    def hello(name: str, lang: str = "ja"):
        greetings = {
            "ja": f"こんにちは、{name}さん！",
            "en": f"Hello, {name}!",
            "es": f"¡Hola, {name}!"
        }
        return {
            "message": greetings.get(lang, greetings["en"]),
            "language": lang
        }

    # ユーザー一覧
    @app.get("/users")
    def get_users(limit: int = 10, offset: int = 0):
        users = [
            {"id": i, "name": f"User {i}"}
            for i in range(offset + 1, offset + limit + 1)
        ]
        return {
            "users": users,
            "pagination": {
                "limit": limit,
                "offset": offset,
                "total": 100
            }
        }

    # ユーザー作成
    @app.post("/users")
    def create_user(request):
        user_data = request.json()

        # 簡単なバリデーション
        if not user_data.get("name"):
            return Response(
                {"error": "Name is required"},
                status_code=400
            )

        return Response(
            {
                "message": "User created successfully",
                "user": {
                    "id": 123,
                    "name": user_data["name"],
                    "email": user_data.get("email")
                }
            },
            status_code=201
        )

    # 個別ユーザー取得
    @app.get("/users/{user_id}")
    def get_user(user_id: str):
        return {
            "id": user_id,
            "name": f"User {user_id}",
            "email": f"user{user_id}@example.com",
            "created_at": "2025-01-01T00:00:00Z"
        }

    return app

lambda_handler = create_lambda_handler(create_app)
```

## テスト方法

### 1. ローカルでのテスト

```python title="test_local.py"
import json

# テスト用のイベントを作成
event = {
    'httpMethod': 'GET',
    'path': '/hello/世界',
    'queryStringParameters': {'lang': 'ja'},
    'headers': {},
    'body': None
}

context = type('Context', (), {
    'aws_request_id': 'test-123',
    'log_group_name': 'test',
    'log_stream_name': 'test'
})()

# ハンドラーを実行
result = lambda_handler(event, context)
print(json.dumps(result, indent=2, ensure_ascii=False))
```

### 2. SAM Local でのテスト

```yaml title="template.yaml"
AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31

Resources:
  lambapiFunction:
    Type: AWS::Serverless::Function
    Properties:
      CodeUri: .
      Handler: app.lambda_handler
      Runtime: python3.13
      Events:
        ApiGateway:
          Type: Api
          Properties:
            Path: /{proxy+}
            Method: ANY
```

```bash
sam local start-api
curl http://localhost:3000/hello/world?lang=en
```

## 型変換の例

lambapi は自動的に型変換を行います：

```python
@app.get("/calc")
def calculate(x: int, y: int, operation: str = "add"):
    """
    GET /calc?x=10&y=5&operation=multiply
    → x=10 (int), y=5 (int), operation="multiply" (str)
    """
    if operation == "add":
        return {"result": x + y}
    elif operation == "multiply":
        return {"result": x * y}
    else:
        return {"error": "Unsupported operation"}

@app.get("/settings")
def get_settings(debug: bool = False, max_items: int = 100):
    """
    GET /settings?debug=true&max_items=50
    → debug=True (bool), max_items=50 (int)
    """
    return {
        "debug_mode": debug,
        "max_items": max_items,
        "environment": "development" if debug else "production"
    }
```

## エラーハンドリング

```python
from lambapi import ValidationError, NotFoundError

@app.get("/users/{user_id}")
def get_user(user_id: str):
    # 入力検証
    if not user_id.isdigit():
        raise ValidationError(
            "User ID must be numeric",
            field="user_id",
            value=user_id
        )

    # 存在チェック
    if int(user_id) > 1000:
        raise NotFoundError("User", user_id)

    return {"id": user_id, "name": f"User {user_id}"}
```

## 次のステップ

おめでとうございます！最初の lambapi アプリケーションが動作しています。

次は以下のトピックを学びましょう：

- [基本概念](concepts.md) - lambapi の設計思想とアーキテクチャ
- [基本的な API](../tutorial/basic-api.md) - 実践的な CRUD API の構築
- [CORS 設定](../tutorial/cors.md) - フロントエンドとの連携
