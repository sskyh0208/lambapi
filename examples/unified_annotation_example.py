"""
統一されたアノテーション方式のサンプル
従来方式を廃止し、FastAPI 風のアノテーションのみをサポート
"""

import json
import sys
import os
from typing import Optional
from dataclasses import dataclass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lambapi import API, create_lambda_handler
from lambapi.annotations import (
    Body, 
    Path, 
    Query, 
    Header,
    CurrentUser,
    RequireRole, 
    OptionalAuth
)

try:
    from pydantic import BaseModel, field_validator
    PYDANTIC_AVAILABLE = True
    
    # Pydantic モデル
    class UserCreateRequest(BaseModel):
        name: str
        email: str
        age: Optional[int] = None
        
        @field_validator('name')
        @classmethod
        def name_must_not_be_empty(cls, v):
            if not v.strip():
                raise ValueError('名前は空にできません')
            return v.strip()

    class UserResponse(BaseModel):
        id: str
        name: str
        email: str
        age: Optional[int]
        created_at: str
        
except ImportError:
    PYDANTIC_AVAILABLE = False
    BaseModel = None


# データクラスの例
@dataclass
class SimpleUser:
    name: str
    email: str
    age: Optional[int] = None


def create_app(event, context):
    """アプリケーション作成関数"""
    app = API(event, context)

    # === 基本的なアノテーション使用例 ===

    @app.post("/users")
    def create_user(user: UserCreateRequest = Body()):
        """Body アノテーションでリクエストボディを受け取り"""
        return {
            "id": f"user_{hash(user.email) % 10000}",
            "name": user.name,
            "email": user.email,
            "age": user.age,
            "created_at": "2024-01-01T00:00:00Z"
        }

    @app.get("/users/{user_id}")
    def get_user(user_id: str = Path()):
        """Path アノテーションでパスパラメータを受け取り"""
        return {
            "id": user_id,
            "name": f"User {user_id}",
            "email": f"user{user_id}@example.com"
        }

    @app.get("/users")
    def list_users(
        page: int = Query(default=1),
        limit: int = Query(default=10),
        search: Optional[str] = Query(default=None, alias="q")
    ):
        """Query アノテーションでクエリパラメータを受け取り"""
        return {
            "page": page,
            "limit": limit, 
            "search": search,
            "users": [f"user{i}" for i in range(1, limit + 1)]
        }

    @app.get("/debug/headers")
    def debug_headers(
        user_agent: str = Header(alias="User-Agent"),
        content_type: Optional[str] = Header(alias="Content-Type")
    ):
        """Header アノテーションでヘッダーを受け取り"""
        return {
            "user_agent": user_agent,
            "content_type": content_type
        }

    # === 自動推論（アノテーションなし）の例 ===

    if PYDANTIC_AVAILABLE:
        @app.post("/users/auto")
        def create_user_auto(user: UserCreateRequest):
            """アノテーションなしでも Pydantic モデルは自動的に Body として処理"""
            return {"message": "created", "user_name": user.name}

    @app.post("/users/dataclass") 
    def create_user_dataclass(user: SimpleUser):
        """データクラスも自動的に Body として処理"""
        return {"message": "created", "user_name": user.name}

    @app.get("/users/mixed/{user_id}")
    def get_user_mixed(user_id: str, include_profile: bool = False):
        """パスパラメータとクエリパラメータの自動推論"""
        return {
            "user_id": user_id,
            "include_profile": include_profile,
            "profile": {"bio": "Sample bio"} if include_profile else None
        }

    # === 認証アノテーション使用例 ===
    # 注意: 実際に動作させるには DynamoDBAuth を設定する必要があります

    @app.get("/profile")
    def get_my_profile(user = CurrentUser()):
        """CurrentUser アノテーションで認証必須のエンドポイント"""
        return {
            "user_id": getattr(user, 'id', 'unknown'),
            "message": "This is your profile"
        }

    @app.delete("/admin/users/{user_id}")
    def delete_user(
        user_id: str = Path(),
        admin_user = RequireRole(['admin'])
    ):
        """RequireRole アノテーションで管理者権限必須のエンドポイント"""
        return {
            "message": f"User {user_id} deleted by admin {getattr(admin_user, 'id', 'unknown')}"
        }

    @app.get("/posts")
    def get_posts(
        user = OptionalAuth(),
        page: int = Query(default=1)
    ):
        """OptionalAuth アノテーションでオプショナル認証"""
        if user:
            return {
                "message": "Personalized posts",
                "user_id": getattr(user, 'id', 'unknown'),
                "page": page
            }
        else:
            return {
                "message": "Public posts",
                "page": page
            }

    # === 複合的な使用例 ===

    @app.put("/users/{user_id}")
    def update_user(
        user_id: str = Path(),
        user_data: UserCreateRequest = Body(),
        version: int = Query(default=1),
        current_user = CurrentUser()
    ):
        """複数のアノテーションを組み合わせた例"""
        return {
            "updated_user_id": user_id,
            "new_data": {
                "name": user_data.name,
                "email": user_data.email
            },
            "version": version,
            "updated_by": getattr(current_user, 'id', 'unknown')
        }

    @app.get("/health")
    def health_check():
        """引数なしの関数"""
        return {"status": "ok", "annotation_system": "unified"}

    return app


# Lambda 関数のエントリーポイント
lambda_handler = create_lambda_handler(create_app)


# ローカルテスト用コード
if __name__ == "__main__":
    
    # テストケース 1: Body アノテーション
    test_event_1 = {
        "httpMethod": "POST",
        "path": "/users",
        "queryStringParameters": None,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"name": "Alice", "email": "alice@example.com", "age": 28}),
    }

    print("=== Test 1: Body アノテーション ===")
    result1 = lambda_handler(test_event_1, None)
    print(json.dumps(result1, indent=2, ensure_ascii=False))

    # テストケース 2: Path アノテーション
    test_event_2 = {
        "httpMethod": "GET",
        "path": "/users/123",
        "queryStringParameters": None,
        "headers": {},
        "body": None,
    }

    print("\n=== Test 2: Path アノテーション ===")
    result2 = lambda_handler(test_event_2, None)
    print(json.dumps(result2, indent=2, ensure_ascii=False))

    # テストケース 3: Query アノテーション
    test_event_3 = {
        "httpMethod": "GET", 
        "path": "/users",
        "queryStringParameters": {"page": "2", "limit": "5", "q": "john"},
        "headers": {},
        "body": None,
    }

    print("\n=== Test 3: Query アノテーション ===")
    result3 = lambda_handler(test_event_3, None)
    print(json.dumps(result3, indent=2, ensure_ascii=False))

    # テストケース 4: Header アノテーション
    test_event_4 = {
        "httpMethod": "GET",
        "path": "/debug/headers",
        "queryStringParameters": None,
        "headers": {
            "User-Agent": "TestClient/1.0",
            "Content-Type": "application/json"
        },
        "body": None,
    }

    print("\n=== Test 4: Header アノテーション ===")
    result4 = lambda_handler(test_event_4, None)
    print(json.dumps(result4, indent=2, ensure_ascii=False))

    # テストケース 5: 自動推論（Pydantic）
    if PYDANTIC_AVAILABLE:
        test_event_5 = {
            "httpMethod": "POST",
            "path": "/users/auto",
            "queryStringParameters": None,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"name": "Bob", "email": "bob@example.com"}),
        }

        print("\n=== Test 5: 自動推論（Pydantic） ===")
        result5 = lambda_handler(test_event_5, None)
        print(json.dumps(result5, indent=2, ensure_ascii=False))

    # テストケース 6: データクラス自動推論
    test_event_6 = {
        "httpMethod": "POST",
        "path": "/users/dataclass",
        "queryStringParameters": None,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"name": "Charlie", "email": "charlie@example.com", "age": 30}),
    }

    print("\n=== Test 6: データクラス自動推論 ===")
    result6 = lambda_handler(test_event_6, None)
    print(json.dumps(result6, indent=2, ensure_ascii=False))

    # テストケース 7: 引数なし関数
    test_event_7 = {
        "httpMethod": "GET",
        "path": "/health",
        "queryStringParameters": None,
        "headers": {},
        "body": None,
    }

    print("\n=== Test 7: 引数なし関数 ===")
    result7 = lambda_handler(test_event_7, None)
    print(json.dumps(result7, indent=2, ensure_ascii=False))