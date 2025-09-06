# 基本的な API

このチュートリアルでは、lambapi を使って実際の API を構築しながら、基本的な機能を学びます。

## 目標

このチュートリアルを完了すると、以下ができるようになります：

- 基本的な CRUD API の作成
- パスパラメータとクエリパラメータの使用
- リクエストボディの処理
- カスタムレスポンスの返却
- エラーハンドリングの実装

## 1. プロジェクトのセットアップ

### ディレクトリ構造

```
my-api/
├── app.py
├── models.py
└── requirements.txt
```

### 必要なパッケージ

```txt title="requirements.txt"
lambapi
```

```bash
pip install -r requirements.txt
```

## 2. データモデルの定義

まず、API で使用するデータモデルを定義しましょう。

```python title="models.py"
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime

@dataclass
class User:
    id: str
    name: str
    email: str
    age: int
    created_at: str = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()

@dataclass
class CreateUserRequest:
    name: str
    email: str
    age: int

@dataclass
class UpdateUserRequest:
    name: Optional[str] = None
    email: Optional[str] = None
    age: Optional[int] = None

# インメモリデータストア（本番環境では DB を使用）
USERS_DB = {}
```

## 3. 基本的な API の実装（依存性注入版）

```python title="app.py"
from lambapi import API, Response, create_lambda_handler, Query, Path, Body
from lambapi.exceptions import NotFoundError, ValidationError
from models import User, CreateUserRequest, UpdateUserRequest, USERS_DB
import uuid

def create_app(event, context):
    app = API(event, context)

    # ヘルスチェック
    @app.get("/health")
    def health_check():
        """API のヘルスチェック"""
        return {
            "status": "healthy",
            "timestamp": "2025-01-01T00:00:00Z",
            "version": "1.0.0"
        }

    # ユーザー一覧取得（依存性注入版）
    @app.get("/users")
    def get_users(
        limit: int = Query(10, ge=1, le=100, description="取得件数"),
        offset: int = Query(0, ge=0, description="オフセット"),
        search: str = Query("", max_length=50, description="検索キーワード")
    ):
        """ユーザー一覧を取得"""
        all_users = list(USERS_DB.values())

        # 検索フィルタリング
        if search:
            all_users = [
                user for user in all_users
                if search.lower() in user.name.lower()
                or search.lower() in user.email.lower()
            ]

        # ページネーション
        total = len(all_users)
        users = all_users[offset:offset + limit]

        return {
            "users": [user.__dict__ for user in users],
            "pagination": {
                "total": total,
                "limit": limit,
                "offset": offset,
                "has_more": offset + limit < total
            }
        }

    # 特定ユーザー取得（依存性注入版）
    @app.get("/users/{user_id}")
    def get_user(user_id: str = Path(..., description="ユーザー ID")):
        """特定のユーザーを取得"""
        if user_id not in USERS_DB:
            raise NotFoundError("User", user_id)

        user = USERS_DB[user_id]
        return {"user": user.__dict__}

    # ユーザー作成（依存性注入版）
    @app.post("/users")
    def create_user(user_data: CreateUserRequest = Body(...)):
        """新しいユーザーを作成"""
        # user_data は自動的にバリデーション済み

        # メール重複チェック
        for existing_user in USERS_DB.values():
            if existing_user.email == user_data.email:
                raise ValidationError("Email already exists", field="email", value=user_data.email)

        # ユーザー作成
        user_id = str(uuid.uuid4())
        user = User(
            id=user_id,
            name=user_data.name,
            email=user_data.email,
            age=user_data.age
        )

        USERS_DB[user_id] = user

        return Response(
            {
                "message": "User created successfully",
                "user": user.__dict__
            },
            status_code=201
        )

    # ユーザー更新（依存性注入版）
    @app.put("/users/{user_id}")
    def update_user(
        user_id: str = Path(..., description="更新対象のユーザー ID"),
        user_data: UpdateUserRequest = Body(...)
    ):
        """既存ユーザーを更新"""
        if user_id not in USERS_DB:
            raise NotFoundError("User", user_id)

        user = USERS_DB[user_id]

        # 更新可能なフィールドのみ処理
        if user_data.name is not None:
            user.name = user_data.name
        if user_data.email is not None:
            # メール重複チェック（自分以外）
            for uid, existing_user in USERS_DB.items():
                if uid != user_id and existing_user.email == user_data.email:
                    raise ValidationError("Email already exists", field="email")
            user.email = user_data.email
        if user_data.age is not None:
            user.age = user_data.age

        return {
            "message": "User updated successfully",
            "user": user.__dict__
        }

    # ユーザー削除（依存性注入版）
    @app.delete("/users/{user_id}")
    def delete_user(user_id: str = Path(..., description="削除対象のユーザー ID")):
        """ユーザーを削除"""
        if user_id not in USERS_DB:
            raise NotFoundError("User", user_id)

        user = USERS_DB.pop(user_id)

        return {
            "message": f"User {user.name} deleted successfully",
            "deleted_user_id": user_id
        }

    # 統計情報
    @app.get("/stats")
    def get_stats():
        """ユーザー統計を取得"""
        users = list(USERS_DB.values())

        if not users:
            return {
                "total_users": 0,
                "average_age": 0,
                "age_distribution": {}
            }

        total_users = len(users)
        average_age = sum(user.age for user in users) / total_users

        # 年齢分布
        age_ranges = {
            "0-18": 0,
            "19-30": 0,
            "31-50": 0,
            "51+": 0
        }

        for user in users:
            if user.age <= 18:
                age_ranges["0-18"] += 1
            elif user.age <= 30:
                age_ranges["19-30"] += 1
            elif user.age <= 50:
                age_ranges["31-50"] += 1
            else:
                age_ranges["51+"] += 1

        return {
            "total_users": total_users,
            "average_age": round(average_age, 2),
            "age_distribution": age_ranges
        }

    return app

# Lambda エントリーポイント
lambda_handler = create_lambda_handler(create_app)

# ローカルテスト用
if __name__ == "__main__":
    # サンプルデータ
    sample_users = [
        User("1", "Alice", "alice@example.com", 25),
        User("2", "Bob", "bob@example.com", 30),
        User("3", "Charlie", "charlie@example.com", 35)
    ]

    for user in sample_users:
        USERS_DB[user.id] = user

    # テスト実行
    test_events = [
        {
            'httpMethod': 'GET',
            'path': '/users',
            'queryStringParameters': {'limit': '2'},
            'headers': {},
            'body': None
        },
        {
            'httpMethod': 'GET',
            'path': '/users/1',
            'headers': {},
            'body': None
        },
        {
            'httpMethod': 'GET',
            'path': '/stats',
            'headers': {},
            'body': None
        }
    ]

    context = type('Context', (), {'aws_request_id': 'test-123'})()

    for event in test_events:
        print(f"\n=== {event['httpMethod']} {event['path']} ===")
        result = lambda_handler(event, context)
        print(f"Status: {result['statusCode']}")
        print(f"Response: {result['body']}")
```

## 4. API のテスト

### 基本的なテスト

```python title="test_api.py"
import json
from app import lambda_handler

def create_test_context():
    return type('Context', (), {'aws_request_id': 'test-123'})()

def test_health_check():
    event = {
        'httpMethod': 'GET',
        'path': '/health',
        'headers': {},
        'body': None
    }

    result = lambda_handler(event, create_test_context())
    assert result['statusCode'] == 200

    body = json.loads(result['body'])
    assert body['status'] == 'healthy'

def test_get_users():
    event = {
        'httpMethod': 'GET',
        'path': '/users',
        'queryStringParameters': {'limit': '5'},
        'headers': {},
        'body': None
    }

    result = lambda_handler(event, create_test_context())
    assert result['statusCode'] == 200

    body = json.loads(result['body'])
    assert 'users' in body
    assert 'pagination' in body

def test_create_user():
    event = {
        'httpMethod': 'POST',
        'path': '/users',
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({
            'name': 'Test User',
            'email': 'test@example.com',
            'age': 25
        })
    }

    result = lambda_handler(event, create_test_context())
    assert result['statusCode'] == 201

    body = json.loads(result['body'])
    assert body['message'] == 'User created successfully'
    assert body['user']['name'] == 'Test User'

if __name__ == "__main__":
    test_health_check()
    test_get_users()
    test_create_user()
    print("All tests passed!")
```

## 5. エラーハンドリングの追加

```python title="error_handlers.py"
from lambapi import ErrorHandler, Response
from lambapi.exceptions import ValidationError, NotFoundError

def create_error_handler():
    """カスタムエラーハンドラーを作成"""
    error_handler = ErrorHandler()

    @error_handler.catch(ValidationError)
    def handle_validation_error(error, request, context):
        return Response({
            "error": "VALIDATION_ERROR",
            "message": error.message,
            "field": getattr(error, 'field', None),
            "request_id": context.aws_request_id
        }, status_code=400)

    @error_handler.catch(NotFoundError)
    def handle_not_found_error(error, request, context):
        return Response({
            "error": "NOT_FOUND",
            "message": error.message,
            "request_id": context.aws_request_id
        }, status_code=404)

    @error_handler.default
    def handle_unknown_error(error, request, context):
        return Response({
            "error": "INTERNAL_ERROR",
            "message": "An unexpected error occurred",
            "request_id": context.aws_request_id
        }, status_code=500)

    return error_handler

# メインアプリケーションで使用
def create_app(event, context):
    app = API(event, context)
    
    # エラーハンドラーを追加
    error_handler = create_error_handler()
    app.add_error_handler(error_handler)
    
    # ルート定義...
    return app
```

## 6. 実用的な機能の追加

### ページネーションの改善

```python
@app.get("/users")
def get_users(
    limit: int = 10,
    offset: int = 0,
    sort_by: str = "name",
    sort_order: str = "asc",
    search: str = ""
):
    """高度なフィルタリングとソート機能付きユーザー一覧"""
    all_users = list(USERS_DB.values())

    # 検索
    if search:
        all_users = [
            user for user in all_users
            if search.lower() in user.name.lower()
            or search.lower() in user.email.lower()
        ]

    # ソート
    reverse = sort_order.lower() == "desc"
    if sort_by == "name":
        all_users.sort(key=lambda u: u.name, reverse=reverse)
    elif sort_by == "age":
        all_users.sort(key=lambda u: u.age, reverse=reverse)
    elif sort_by == "created_at":
        all_users.sort(key=lambda u: u.created_at, reverse=reverse)

    # ページネーション
    total = len(all_users)
    users = all_users[offset:offset + limit]

    return {
        "users": [user.__dict__ for user in users],
        "pagination": {
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": offset + limit < total
        },
        "filters": {
            "search": search,
            "sort_by": sort_by,
            "sort_order": sort_order
        }
    }
```

### バッチ操作

```python
@app.post("/users/batch")
def create_users_batch(request):
    """複数ユーザーの一括作成"""
    data = request.json()
    users_data = data.get("users", [])

    if not users_data:
        raise ValidationError("No users provided")

    created_users = []
    errors = []

    for i, user_data in enumerate(users_data):
        try:
            # バリデーション
            if not user_data.get("name"):
                errors.append(f"User {i}: Name is required")
                continue

            # ユーザー作成
            user_id = str(uuid.uuid4())
            user = User(
                id=user_id,
                name=user_data["name"],
                email=user_data["email"],
                age=user_data["age"]
            )

            USERS_DB[user_id] = user
            created_users.append(user.__dict__)

        except Exception as e:
            errors.append(f"User {i}: {str(e)}")

    return {
        "message": f"Batch operation completed",
        "created": len(created_users),
        "errors": len(errors),
        "users": created_users,
        "error_details": errors if errors else None
    }
```

## 7. 次のステップ

このチュートリアルで基本的な CRUD API を作成しました。次は以下のトピックに進みましょう：

- [CORS 設定](cors.md) - フロントエンドとの連携
- [API リファレンス](../api/api.md) - すべてのクラスとメソッドの詳細
- [デプロイメント](../guides/deployment.md) - 本番環境での運用

## まとめ

このチュートリアルでは以下を学びました：

- ✅ 基本的な CRUD API の実装
- ✅ パスパラメータとクエリパラメータの使用
- ✅ リクエストボディの処理
- ✅ カスタムレスポンスとステータスコード
- ✅ バリデーションとエラーハンドリング
- ✅ ページネーションとフィルタリング
- ✅ バッチ操作の実装

これらの基礎をマスターすることで、実際のプロダクションで使える API を構築できるようになります。
