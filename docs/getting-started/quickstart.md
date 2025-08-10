# クイックスタート

lambapi を使って最初の API を構築しましょう。このガイドでは、5 分で動作する API を作成できます。

## 前提条件

- Python 3.10 以上
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

### 2. アノテーションを使ったパラメータ注入

```python title="app.py"
from lambapi.annotations import Path, Query

@app.get("/hello/{name}")
def hello_name(name: str = Path(), lang: str = Query(default="ja")):
    greetings = {
        "ja": f"こんにちは、{name}さん！",
        "en": f"Hello, {name}!",
        "es": f"¡Hola, {name}!"
    }
    return {
        "message": greetings.get(lang, greetings["en"]),
        "language": lang
    }
```

### 3. FastAPI 風の自動推論

```python title="app.py"
# 自動推論：型アノテーションから自動的にパラメータソースを判定
@app.get("/search")
def search(q: str = "", limit: int = 10, sort: str = "name"):
    return {
        "query": q,
        "limit": limit,
        "sort": sort,
        "results": [f"item-{i}" for i in range(1, limit + 1)]
    }

# パスパラメータも自動推論
@app.get("/users/{user_id}")
def get_user(user_id: int):  # 自動的に Path パラメータとして扱われる
    return {
        "id": user_id,
        "name": f"User {user_id}",
        "email": f"user{user_id}@example.com"
    }
```

### 4. データクラスとバリデーション

```python title="app.py"
from dataclasses import dataclass
from lambapi.annotations import Body
from typing import Optional

@dataclass
class CreateUserRequest:
    name: str
    email: str
    age: Optional[int] = None

@app.post("/users")
def create_user(user: CreateUserRequest = Body()):
    return {
        "message": "User created",
        "user": {
            "id": f"user_{hash(user.email)}",
            "name": user.name,
            "email": user.email,
            "age": user.age
        }
    }

# 自動推論版（Body は自動的に推論される）
@app.post("/users/auto")
def create_user_auto(user: CreateUserRequest):
    return {"message": "User created with auto inference", "user": user}
```

## 完全な例

```python title="complete_app.py"
from lambapi import API, Response, create_lambda_handler
from lambapi.annotations import Body, Path, Query
from dataclasses import dataclass
from typing import Optional

@dataclass
class User:
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
            "version": "2.0.0",
            "endpoints": [
                "GET /",
                "GET /hello/{name}",
                "GET /users",
                "POST /users",
                "GET /users/{id}"
            ]
        }

    # アノテーション版の挨拶エンドポイント
    @app.get("/hello/{name}")
    def hello(name: str = Path(), lang: str = Query(default="ja")):
        greetings = {
            "ja": f"こんにちは、{name}さん！",
            "en": f"Hello, {name}!",
            "es": f"¡Hola, {name}!"
        }
        return {
            "message": greetings.get(lang, greetings["en"]),
            "language": lang
        }

    # 自動推論版のユーザー一覧
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

    # データクラス版のユーザー作成
    @app.post("/users")
    def create_user(user: User):  # 自動推論で Body として扱われる
        return Response(
            {
                "message": "User created successfully",
                "user": {
                    "id": f"user_{hash(user.email)}",
                    "name": user.name,
                    "email": user.email,
                    "age": user.age
                }
            },
            status_code=201
        )

    # 自動推論版の個別ユーザー取得
    @app.get("/users/{user_id}")
    def get_user(user_id: int):  # 自動的に Path パラメータ
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

## 認証システム

```python title="auth_example.py"
from lambapi import API, create_lambda_handler
from lambapi.annotations import Path, CurrentUser, RequireRole, OptionalAuth
from lambapi.auth import DynamoDBAuth, BaseUser
from dataclasses import dataclass
from typing import Optional

@dataclass
class User(BaseUser):
    name: str
    email: str
    role: str

def create_app(event, context):
    app = API(event, context)

    # 認証設定
    auth = DynamoDBAuth(
        table_name="users",
        user_model=User,
        region_name="ap-northeast-1"
    )
    app.include_auth(auth)

    # 認証が必要なエンドポイント
    @app.get("/profile")
    def get_profile(current_user: User = CurrentUser()):
        return {"user": current_user}

    # ロール制限
    @app.delete("/admin/users/{user_id}")
    def delete_user(
        user_id: int = Path(),
        admin_user: User = RequireRole(roles=["admin"])
    ):
        return {"deleted": user_id, "by": admin_user.name}

    # オプショナル認証
    @app.get("/posts")
    def list_posts(user: Optional[User] = OptionalAuth()):
        if user:
            return {"posts": "personalized", "user": user.name}
        return {"posts": "public"}

    return app
```

## エラーハンドリング

```python
from lambapi import ValidationError, NotFoundError

@app.get("/users/{user_id}")
def get_user(user_id: int):
    # バリデーションエラーは自動的に処理される
    if user_id <= 0:
        raise ValidationError(
            "User ID must be positive",
            field="user_id",
            value=user_id
        )

    # 存在チェック
    if user_id > 1000:
        raise NotFoundError("User", user_id)

    return {"id": user_id, "name": f"User {user_id}"}
```

## 次のステップ

おめでとうございます！新しい lambapi v0.2.x が動作しています。

次は以下のトピックを学びましょう：

- [基本概念](concepts.md) - lambapi の設計思想とアーキテクチャ
- [基本的な API](../tutorial/basic-api.md) - 実践的な CRUD API の構築
- [CORS 設定](../tutorial/cors.md) - フロントエンドとの連携
