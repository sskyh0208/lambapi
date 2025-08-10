# 基本的な API

このチュートリアルでは、lambapi v0.2.x の新しいアノテーションシステムを使って実際の API を構築しながら、基本的な機能を学びます。

## 目標

このチュートリアルを完了すると、以下ができるようになります：

- 統合アノテーションシステムを使った CRUD API の作成
- FastAPI 風の自動推論機能の活用
- Body, Path, Query, Header アノテーションの使い分け
- データクラスと Pydantic を使った自動バリデーション
- カスタムレスポンスとエラーハンドリング

## 1. プロジェクトのセットアップ

### ディレクトリ構造

```
my-api/
├── app.py
├── models.py
├── requirements.txt
└── tests/
    └── test_api.py
```

### 必要なパッケージ

```txt title="requirements.txt"
lambapi>=0.2.0
pydantic  # オプション: より強力なバリデーション用
```

```bash
pip install -r requirements.txt
```

## 2. データモデルの定義

新しい v0.2.x では、データクラスと Pydantic モデル両方がサポートされています。

```python title="models.py"
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime
import uuid

# データクラス版（軽量）
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

# Pydantic 版（高機能バリデーション）
try:
    from pydantic import BaseModel, field_validator, EmailStr

    class PydanticUser(BaseModel):
        id: str
        name: str
        email: str
        age: int
        created_at: Optional[str] = None

        @field_validator('age')
        @classmethod
        def validate_age(cls, v):
            if v < 0 or v > 150:
                raise ValueError('年齢は 0-150 の範囲で入力してください')
            return v

    class PydanticCreateUserRequest(BaseModel):
        name: str
        email: str
        age: int

        @field_validator('name')
        @classmethod
        def validate_name(cls, v):
            if len(v.strip()) == 0:
                raise ValueError('名前は必須です')
            return v.strip()

except ImportError:
    PydanticUser = None
    PydanticCreateUserRequest = None

# インメモリデータストア（本番環境では DB を使用）
USERS_DB = {}

def create_user(user_data: dict) -> User:
    """ユーザーを作成して DB に保存"""
    user_id = str(uuid.uuid4())
    user = User(
        id=user_id,
        name=user_data['name'],
        email=user_data['email'],
        age=user_data['age']
    )
    USERS_DB[user_id] = user
    return user

def get_user_by_id(user_id: str) -> Optional[User]:
    """ID でユーザーを取得"""
    return USERS_DB.get(user_id)

def delete_user_by_id(user_id: str) -> bool:
    """ID でユーザーを削除"""
    if user_id in USERS_DB:
        del USERS_DB[user_id]
        return True
    return False
```

## 3. アノテーションを使った API の実装

```python title="app.py"
from lambapi import API, Response, create_lambda_handler
from lambapi.annotations import Body, Path, Query, Header
from lambapi.exceptions import NotFoundError, ValidationError
from models import (
    User, CreateUserRequest, UpdateUserRequest,
    create_user, get_user_by_id, delete_user_by_id, USERS_DB
)
from typing import List, Optional

def create_app(event, context):
    app = API(event, context)

    # ヘルスチェック（アノテーションなし）
    @app.get("/health")
    def health_check():
        """API のヘルスチェック"""
        return {
            "status": "healthy",
            "timestamp": "2025-01-01T00:00:00Z",
            "version": "2.0.0"
        }

    # 自動推論版：ユーザー一覧取得
    @app.get("/users")
    def get_users(limit: int = 10, offset: int = 0, search: str = ""):
        """ユーザー一覧を取得（自動推論）"""
        all_users = list(USERS_DB.values())

        # 検索フィルタリング
        if search:
            all_users = [
                user for user in all_users
                if search.lower() in user.name.lower() or search.lower() in user.email.lower()
            ]

        # ページネーション
        total = len(all_users)
        users = all_users[offset:offset + limit]

        return {
            "users": [
                {
                    "id": user.id,
                    "name": user.name,
                    "email": user.email,
                    "age": user.age,
                    "created_at": user.created_at
                } for user in users
            ],
            "pagination": {
                "total": total,
                "limit": limit,
                "offset": offset,
                "has_more": offset + limit < total
            }
        }

    # アノテーション版：ユーザー一覧取得（ヘッダー使用）
    @app.get("/api/users")
    def get_users_with_header(
        limit: int = Query(default=10),
        offset: int = Query(default=0),
        search: str = Query(default=""),
        user_agent: str = Header(alias="User-Agent")
    ):
        """ユーザー一覧を取得（アノテーション版）"""
        all_users = list(USERS_DB.values())

        if search:
            all_users = [
                user for user in all_users
                if search.lower() in user.name.lower()
            ]

        users = all_users[offset:offset + limit]

        return {
            "users": [{"id": u.id, "name": u.name, "email": u.email, "age": u.age} for u in users],
            "metadata": {
                "total": len(all_users),
                "user_agent": user_agent,
                "search_query": search
            }
        }

    # 自動推論版：個別ユーザー取得
    @app.get("/users/{user_id}")
    def get_user(user_id: str):
        """個別ユーザーを取得（自動推論：Path パラメータ）"""
        user = get_user_by_id(user_id)
        if not user:
            raise NotFoundError("User", user_id)

        return {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "age": user.age,
            "created_at": user.created_at
        }

    # アノテーション版：個別ユーザー取得
    @app.get("/api/users/{user_id}")
    def get_user_explicit(user_id: str = Path()):
        """個別ユーザーを取得（明示的アノテーション）"""
        user = get_user_by_id(user_id)
        if not user:
            raise NotFoundError("User", user_id)

        return user

    # 自動推論版：ユーザー作成
    @app.post("/users")
    def create_user_endpoint(user_request: CreateUserRequest):
        """ユーザーを作成（自動推論：Body パラメータ）"""
        # バリデーション（データクラスでは基本的な型チェックのみ）
        if not user_request.name.strip():
            raise ValidationError("名前は必須です", field="name", value=user_request.name)

        if user_request.age < 0 or user_request.age > 150:
            raise ValidationError("年齢は 0-150 の範囲で入力してください", field="age", value=user_request.age)

        user = create_user({
            "name": user_request.name,
            "email": user_request.email,
            "age": user_request.age
        })

        return Response(
            {
                "message": "ユーザーが作成されました",
                "user": {
                    "id": user.id,
                    "name": user.name,
                    "email": user.email,
                    "age": user.age,
                    "created_at": user.created_at
                }
            },
            status_code=201
        )

    # アノテーション版：ユーザー作成
    @app.post("/api/users")
    def create_user_explicit(user_request: CreateUserRequest = Body()):
        """ユーザーを作成（明示的アノテーション）"""
        user = create_user({
            "name": user_request.name,
            "email": user_request.email,
            "age": user_request.age
        })

        return Response(user.__dict__, status_code=201)

    # 混合版：ユーザー更新
    @app.put("/users/{user_id}")
    def update_user(
        user_id: str,  # 自動推論：Path パラメータ
        user_request: UpdateUserRequest  # 自動推論：Body パラメータ
    ):
        """ユーザーを更新（混合アノテーション）"""
        user = get_user_by_id(user_id)
        if not user:
            raise NotFoundError("User", user_id)

        # 更新処理
        if user_request.name is not None:
            user.name = user_request.name
        if user_request.email is not None:
            user.email = user_request.email
        if user_request.age is not None:
            user.age = user_request.age

        return {
            "message": "ユーザーが更新されました",
            "user": {
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "age": user.age,
                "created_at": user.created_at
            }
        }

    # 完全アノテーション版：ユーザー更新
    @app.put("/api/users/{user_id}")
    def update_user_explicit(
        user_id: str = Path(),
        user_request: UpdateUserRequest = Body(),
        version: str = Query(default="v1"),
        content_type: str = Header(alias="Content-Type")
    ):
        """ユーザーを更新（完全アノテーション）"""
        user = get_user_by_id(user_id)
        if not user:
            raise NotFoundError("User", user_id)

        # バージョンチェック
        if version != "v1":
            return Response(
                {"error": "サポートされていない API バージョンです"},
                status_code=400
            )

        # Content-Type チェック
        if "application/json" not in content_type:
            return Response(
                {"error": "Content-Type は application/json である必要があります"},
                status_code=400
            )

        # 更新処理
        updated_fields = []
        if user_request.name is not None:
            user.name = user_request.name
            updated_fields.append("name")
        if user_request.email is not None:
            user.email = user_request.email
            updated_fields.append("email")
        if user_request.age is not None:
            user.age = user_request.age
            updated_fields.append("age")

        return {
            "message": f"ユーザーが更新されました: {', '.join(updated_fields)}",
            "user": user.__dict__,
            "version": version
        }

    # 自動推論版：ユーザー削除
    @app.delete("/users/{user_id}")
    def delete_user(user_id: str):
        """ユーザーを削除（自動推論）"""
        if not delete_user_by_id(user_id):
            raise NotFoundError("User", user_id)

        return {"message": "ユーザーが削除されました", "user_id": user_id}

    # 検索エンドポイント（複雑なクエリパラメータ）
    @app.get("/search/users")
    def search_users(
        q: str = Query(),
        age_min: Optional[int] = Query(default=None),
        age_max: Optional[int] = Query(default=None),
        sort_by: str = Query(default="name"),
        sort_order: str = Query(default="asc")
    ):
        """ユーザー検索（複雑なクエリパラメータ）"""
        users = list(USERS_DB.values())

        # テキスト検索
        if q:
            users = [u for u in users if q.lower() in u.name.lower() or q.lower() in u.email.lower()]

        # 年齢フィルタリング
        if age_min is not None:
            users = [u for u in users if u.age >= age_min]
        if age_max is not None:
            users = [u for u in users if u.age <= age_max]

        # ソート
        reverse = sort_order == "desc"
        if sort_by == "name":
            users.sort(key=lambda u: u.name, reverse=reverse)
        elif sort_by == "age":
            users.sort(key=lambda u: u.age, reverse=reverse)
        elif sort_by == "created_at":
            users.sort(key=lambda u: u.created_at, reverse=reverse)

        return {
            "query": {
                "text": q,
                "age_range": {"min": age_min, "max": age_max},
                "sort": {"by": sort_by, "order": sort_order}
            },
            "results": [u.__dict__ for u in users],
            "count": len(users)
        }

    return app

lambda_handler = create_lambda_handler(create_app)
```

## 4. テストの作成

```python title="tests/test_api.py"
import json
import pytest
from app import lambda_handler

def create_test_event(method, path, body=None, query_params=None, headers=None):
    """テスト用 Lambda イベントを作成"""
    return {
        'httpMethod': method,
        'path': path,
        'queryStringParameters': query_params or {},
        'headers': headers or {'Content-Type': 'application/json'},
        'body': json.dumps(body) if body else None
    }

class TestAPI:
    def test_health_check(self):
        """ヘルスチェックのテスト"""
        event = create_test_event('GET', '/health')
        result = lambda_handler(event, None)

        assert result['statusCode'] == 200
        body = json.loads(result['body'])
        assert body['status'] == 'healthy'

    def test_create_user_auto_inference(self):
        """ユーザー作成の自動推論テスト"""
        user_data = {"name": "Alice", "email": "alice@example.com", "age": 25}
        event = create_test_event('POST', '/users', body=user_data)

        result = lambda_handler(event, None)

        assert result['statusCode'] == 201
        body = json.loads(result['body'])
        assert body['message'] == 'ユーザーが作成されました'
        assert body['user']['name'] == 'Alice'

    def test_get_user_with_path_param(self):
        """パスパラメータを使ったユーザー取得テスト"""
        # まずユーザーを作成
        user_data = {"name": "Bob", "email": "bob@example.com", "age": 30}
        create_event = create_test_event('POST', '/users', body=user_data)
        create_result = lambda_handler(create_event, None)

        create_body = json.loads(create_result['body'])
        user_id = create_body['user']['id']

        # ユーザーを取得
        get_event = create_test_event('GET', f'/users/{user_id}')
        get_result = lambda_handler(get_event, None)

        assert get_result['statusCode'] == 200
        get_body = json.loads(get_result['body'])
        assert get_body['name'] == 'Bob'

    def test_get_users_with_query_params(self):
        """クエリパラメータを使ったユーザー一覧取得テスト"""
        event = create_test_event('GET', '/users', query_params={
            'limit': '5',
            'offset': '0',
            'search': 'alice'
        })

        result = lambda_handler(event, None)

        assert result['statusCode'] == 200
        body = json.loads(result['body'])
        assert body['pagination']['limit'] == 5

    def test_annotation_version_with_headers(self):
        """ヘッダーアノテーションのテスト"""
        event = create_test_event('GET', '/api/users', headers={
            'User-Agent': 'TestClient/1.0',
            'Content-Type': 'application/json'
        })

        result = lambda_handler(event, None)

        assert result['statusCode'] == 200
        body = json.loads(result['body'])
        assert body['metadata']['user_agent'] == 'TestClient/1.0'
```

## 5. 実行とテスト

### ローカルテスト

```python title="local_test.py"
import json
from app import lambda_handler

# ヘルスチェック
health_event = {
    'httpMethod': 'GET',
    'path': '/health',
    'queryStringParameters': {},
    'headers': {},
    'body': None
}

result = lambda_handler(health_event, None)
print("Health Check:")
print(json.dumps(json.loads(result['body']), indent=2, ensure_ascii=False))

# ユーザー作成（自動推論）
create_event = {
    'httpMethod': 'POST',
    'path': '/users',
    'queryStringParameters': {},
    'headers': {'Content-Type': 'application/json'},
    'body': json.dumps({
        "name": "田中太郎",
        "email": "tanaka@example.com",
        "age": 28
    })
}

result = lambda_handler(create_event, None)
print("\nUser Creation:")
print(json.dumps(json.loads(result['body']), indent=2, ensure_ascii=False))
```

## まとめ

このチュートリアルでは、lambapi v0.2.x の新機能を学びました：

### 🎯 学んだ内容

1. **統合アノテーションシステム**
   - `Body`, `Path`, `Query`, `Header` の使い分け
   - 明示的アノテーション vs 自動推論

2. **FastAPI 風の自動推論**
   - データクラス/Pydantic モデル → 自動的に Body
   - パスパラメータ → 自動的に Path
   - その他のパラメータ → 自動的に Query

3. **型安全性とバリデーション**
   - データクラスによる基本バリデーション
   - Pydantic による高度なバリデーション
   - 自動型変換

4. **レスポンス処理**
   - 辞書の自動 JSON 変換
   - Response オブジェクトによるカスタムレスポンス
   - データクラスの自動シリアライゼーション

### 🚀 次のステップ

- [認証システム](../guides/authentication.md) - CurrentUser, RequireRole アノテーション
- [CORS 設定](cors.md) - フロントエンドとの連携
- [デプロイメント](../guides/deployment.md) - 本番環境への展開
