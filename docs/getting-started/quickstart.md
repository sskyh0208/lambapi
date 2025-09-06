# クイックスタート

lambapi を使って最初の API を構築しましょう。このガイドでは、5 分で動作する API を作成できます。

## 前提条件

- Python 3.10 以上
- AWS Lambda の基本的な知識（任意）

## インストール

```bash
# 基本インストール
pip install lambapi

# ローカル開発環境（uvicorn 付き）
pip install lambapi[dev]
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

### 2. パスパラメータの使用（依存性注入）

```python title="app.py"
from lambapi import Path

@app.get("/hello/{name}")
def hello_name(name: str = Path(..., description="挨拶対象の名前")):
    return {"message": f"Hello, {name}!"}
```

### 3. クエリパラメータとバリデーション（依存性注入）

```python title="app.py"
from lambapi import Query

@app.get("/search")
def search(
    q: str = Query(..., min_length=1, description="検索クエリ"),
    limit: int = Query(10, ge=1, le=100, description="結果数"),
    sort: str = Query("name", regex="^(name|date|score)$", description="ソート方法")
):
    return {
        "query": q,
        "limit": limit,
        "sort": sort,
        "results": [f"item-{i}" for i in range(1, min(limit, 5) + 1)]
    }
```

### 4. リクエストボディの処理（依存性注入）

```python title="app.py"
from lambapi import Body, Path
from dataclasses import dataclass
from typing import Optional

@dataclass
class CreateUserRequest:
    name: str
    email: str
    age: Optional[int] = None

@dataclass
class UpdateUserRequest:
    name: Optional[str] = None
    email: Optional[str] = None
    age: Optional[int] = None

@app.post("/users")
def create_user(user_data: CreateUserRequest = Body(...)):
    return {
        "message": "User created",
        "user": {"name": user_data.name, "email": user_data.email, "age": user_data.age}
    }

@app.put("/users/{user_id}")
def update_user(
    user_id: str = Path(..., description="ユーザー ID"),
    user_data: UpdateUserRequest = Body(...)
):
    return {
        "message": f"User {user_id} updated",
        "user_id": user_id,
        "updates": {"name": user_data.name, "email": user_data.email}
    }

@app.delete("/users/{user_id}")
def delete_user(user_id: str = Path(..., description="削除対象のユーザー ID")):
    return {"message": f"User {user_id} deleted"}
```

## 完全な例（依存性注入版）

```python title="complete_app.py"
from lambapi import API, Response, create_lambda_handler, Query, Path, Body
from dataclasses import dataclass
from typing import Optional

@dataclass
class CreateUserRequest:
    name: str
    email: str
    age: Optional[int] = None

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

    # 挨拶エンドポイント（依存性注入）
    @app.get("/hello/{name}")
    def hello(
        name: str = Path(..., description="挨拶対象の名前"),
        lang: str = Query("ja", regex="^(ja|en|es)$", description="言語")
    ):
        greetings = {
            "ja": f"こんにちは、{name}さん！",
            "en": f"Hello, {name}!",
            "es": f"¡Hola, {name}!"
        }
        return {
            "message": greetings.get(lang, greetings["en"]),
            "language": lang
        }

    # ユーザー一覧（依存性注入）
    @app.get("/users")
    def get_users(
        limit: int = Query(10, ge=1, le=100, description="取得件数"),
        offset: int = Query(0, ge=0, description="オフセット")
    ):
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

    # ユーザー作成（依存性注入）
    @app.post("/users")
    def create_user(user_data: CreateUserRequest = Body(...)):
        # バリデーションは依存性注入で自動実行済み
        return Response(
            {
                "message": "User created successfully",
                "user": {
                    "id": 123,
                    "name": user_data.name,
                    "email": user_data.email,
                    "age": user_data.age
                }
            },
            status_code=201
        )

    # 個別ユーザー取得（依存性注入）
    @app.get("/users/{user_id}")
    def get_user(user_id: str = Path(..., description="ユーザー ID")):
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

### 1. uvicorn でのローカル開発

```bash
# ローカル開発サーバーを起動（推奨）
lambapi serve complete_app

# または uvicorn を直接使用
uvicorn complete_app:lambda_handler --host 0.0.0.0 --port 8000

# API テスト
curl "http://localhost:8000/hello/world?lang=en"
curl "http://localhost:8000/users?limit=5&offset=0"
curl -X POST http://localhost:8000/users \
  -H "Content-Type: application/json" \
  -d '{"name":"John Doe","email":"john@example.com","age":30}'
```

### 2. Python でのユニットテスト

```python title="test_local.py"
import json

# テスト用のイベントを作成
def test_hello_endpoint():
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

def test_user_creation():
    event = {
        'httpMethod': 'POST',
        'path': '/users',
        'queryStringParameters': None,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({
            "name": "Alice Smith",
            "email": "alice@example.com",
            "age": 25
        })
    }

    context = type('Context', (), {'aws_request_id': 'test-456'})()
    result = lambda_handler(event, context)
    print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    test_hello_endpoint()
    test_user_creation()
```

### 3. SAM Local でのテスト

```yaml title="template.yaml"
AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31

Resources:
  lambapiFunction:
    Type: AWS::Serverless::Function
    Properties:
      CodeUri: .
      Handler: complete_app.lambda_handler
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
curl "http://localhost:3000/hello/world?lang=en"
curl "http://localhost:3000/users?limit=5&offset=0"
```

## 依存性注入の型変換とバリデーション

lambapi の依存性注入は自動的に型変換とバリデーションを行います：

```python
from lambapi import Query

@app.get("/calc")
def calculate(
    x: int = Query(..., description="第 1 オペランド"),
    y: int = Query(..., description="第 2 オペランド"),
    operation: str = Query("add", regex="^(add|multiply|subtract|divide)$", description="演算種別")
):
    """
    GET /calc?x=10&y=5&operation=multiply
    → x=10 (int), y=5 (int), operation="multiply" (str)
    → すべて自動型変換・バリデーション済み
    """
    if operation == "add":
        return {"result": x + y}
    elif operation == "multiply":
        return {"result": x * y}
    elif operation == "subtract":
        return {"result": x - y}
    elif operation == "divide":
        if y == 0:
            return {"error": "Division by zero"}
        return {"result": x / y}

@app.get("/settings")
def get_settings(
    debug: bool = Query(False, description="デバッグモード"),
    max_items: int = Query(100, ge=1, le=1000, description="最大アイテム数")
):
    """
    GET /settings?debug=true&max_items=50
    → debug=True (bool), max_items=50 (int)
    → バリデーション: max_items は 1-1000 の範囲内
    """
    return {
        "debug_mode": debug,
        "max_items": max_items,
        "environment": "development" if debug else "production"
    }
```

## エラーハンドリング

依存性注入により、多くのバリデーションエラーは自動的に処理されます：

```python
from lambapi import ValidationError, NotFoundError, Path, Query

@app.get("/users/{user_id}")
def get_user(
    user_id: int = Path(..., gt=0, le=1000, description="ユーザー ID（1-1000）")
):
    # user_id は既に int 型に変換され、範囲もバリデーション済み
    # 1000 より大きい値は自動的に 400 エラーになる
    
    # ビジネスロジックでの存在チェック
    if user_id == 999:  # 例：特定の ID が存在しない場合
        raise NotFoundError("User", str(user_id))

    return {"id": user_id, "name": f"User {user_id}"}

@app.get("/search")
def search_users(
    name: str = Query(..., min_length=2, max_length=50, description="検索する名前"),
    active: bool = Query(True, description="アクティブユーザーのみ")
):
    # name の長さは自動バリデーション済み
    # 短すぎる・長すぎる場合は自動的に 400 エラー
    
    return {
        "query": name,
        "active_only": active,
        "results": [f"User matching '{name}'"]
    }

# カスタムエラーハンドラー
from lambapi import ErrorHandler

error_handler = ErrorHandler()

@error_handler.catch(ValidationError)
def handle_validation_error(error, request, context):
    return {
        "error": "validation_failed",
        "message": str(error),
        "field": getattr(error, 'field', None)
    }

app.add_error_handler(error_handler)
```

## 次のステップ

おめでとうございます！依存性注入を活用した lambapi アプリケーションが動作しています。

**学習したこと**：
- ✅ 依存性注入（Query, Path, Body）による型安全な API 開発
- ✅ 自動型変換とバリデーション
- ✅ データクラスによる構造化リクエスト
- ✅ エラーハンドリングの簡素化

次は以下のトピックを学びましょう：

- [依存性注入](../tutorial/dependency-injection.md) - より詳細な依存性注入パターン
- [基本概念](concepts.md) - lambapi の設計思想とアーキテクチャ
- [基本的な API](../tutorial/basic-api.md) - 実践的な CRUD API の構築
- [認証システム](../guides/authentication.md) - DynamoDB + JWT 認証
- [CORS 設定](../tutorial/cors.md) - フロントエンドとの連携
