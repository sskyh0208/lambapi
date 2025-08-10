"""
Pydantic バリデーション機能のサンプル（v0.2.x）
統合アノテーションシステムと FastAPI 風の自動バリデーション機能の使用例
"""

import json
import sys
import os
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lambapi import API, Response, create_lambda_handler
from lambapi.annotations import Body, Path, Query

try:
    from pydantic import BaseModel, field_validator
    PYDANTIC_AVAILABLE = True
except ImportError:
    print("Pydantic がインストールされていません。pip install pydantic でインストールしてください。")
    BaseModel = None
    PYDANTIC_AVAILABLE = False


if PYDANTIC_AVAILABLE:
    # Pydantic モデル定義
    class CreateUserRequest(BaseModel):
        name: str
        email: str
        age: Optional[int] = None
        
        @field_validator('name')
        @classmethod
        def name_must_not_be_empty(cls, v):
            if not v.strip():
                raise ValueError('名前は空にできません')
            return v.strip()
        
        @field_validator('age')
        @classmethod
        def age_must_be_positive(cls, v):
            if v is not None and v < 0:
                raise ValueError('年齢は 0 以上である必要があります')
            return v

    class UserResponse(BaseModel):
        id: str
        name: str
        email: str
        age: Optional[int]
        created_at: str


def create_app(event, context):
    """アプリケーション作成関数"""
    app = API(event, context)

    if not PYDANTIC_AVAILABLE:
        @app.get("/")
        def no_pydantic():
            return {"error": "Pydantic がインストールされていません"}
        return app

    # ===== v0.2.x 自動推論版の Pydantic バリデーション =====

    @app.post("/users/auto")
    def create_user_auto(user: CreateUserRequest):
        """v0.2.x 自動推論版のユーザー作成（Pydantic モデルが自動的に Body として処理）"""
        # user は CreateUserRequest オブジェクトとして受け取れる
        print(f"受信データ: name={user.name}, email={user.email}, age={user.age}")

        # レスポンスデータを作成
        response_data = UserResponse(
            id=f"user_{hash(user.email) % 10000}",
            name=user.name,
            email=user.email,
            age=user.age,
            created_at="2024-01-01T00:00:00Z"
        )

        return response_data.model_dump()
    
    # 明示的アノテーション版
    @app.post("/users/explicit")
    def create_user_explicit(user: CreateUserRequest = Body()):
        """明示的アノテーションでのユーザー作成"""
        response_data = UserResponse(
            id=f"explicit_{hash(user.email) % 10000}",
            name=user.name,
            email=user.email,
            age=user.age,
            created_at="2024-01-01T00:00:00Z"
        )

        return response_data.model_dump()

    # 自動推論版の Path パラメータ
    @app.get("/users/{user_id}")
    def get_user_auto(user_id: str):
        """v0.2.x 自動推論版のユーザー取得（user_id が自動的に Path パラメータ）"""
        # パスパラメータが自動で型変換されて渡される
        response_data = UserResponse(
            id=user_id,
            name=f"User {user_id}",
            email=f"user{user_id}@example.com",
            age=25,
            created_at="2024-01-01T00:00:00Z"
        )

        return response_data.model_dump()
    
    # 明示的アノテーション版
    @app.get("/api/users/{user_id}")
    def get_user_explicit(user_id: str = Path()):
        """明示的アノテーションでのユーザー取得"""
        response_data = UserResponse(
            id=user_id,
            name=f"Explicit User {user_id}",
            email=f"explicit{user_id}@example.com",
            age=30,
            created_at="2024-01-01T00:00:00Z"
        )

        return response_data.model_dump()

    # 自動推論版の Query パラメータ
    @app.get("/users/search")
    def search_users(name: str = "defaultuser", age: int = 0, limit: int = 10):
        """v0.2.x 自動推論版のクエリパラメータテスト"""
        return {
            "search_criteria": {
                "name": name,
                "age": age,
                "limit": limit
            },
            "results": [
                {
                    "id": f"search-result-{i}",
                    "name": f"{name}-{i}",
                    "age": age + i
                }
                for i in range(1, min(limit, 5) + 1)
            ]
        }
    
    # 明示的アノテーション版の Query
    @app.get("/api/users/search")
    def search_users_explicit(
        name: str = Query(default="defaultuser"),
        age: int = Query(default=0),
        limit: int = Query(default=10)
    ):
        """明示的アノテーションでの検索"""
        return {
            "search_criteria": {
                "name": name,
                "age": age,
                "limit": limit
            },
            "results": [f"explicit-result-{i}" for i in range(1, min(limit, 3) + 1)]
        }

    # ===== 複合アノテーション例 =====
    
    @app.put("/users/{user_id}")
    def update_user_mixed(
        user_id: str = Path(),  # 明示的 Path
        user_data: CreateUserRequest = Body(),  # 明示的 Body
        version: str = Query(default="v1")  # 明示的 Query
    ):
        """複数のアノテーションを組み合わせた例"""
        response_data = UserResponse(
            id=user_id,
            name=user_data.name,
            email=user_data.email,
            age=user_data.age,
            created_at="2024-01-01T00:00:00Z"
        )

        return {
            "message": f"User {user_id} updated",
            "user": response_data.model_dump(),
            "version": version
        }

    @app.get("/health")
    def health_check():
        """ヘルスチェック（引数なし）"""
        return {
            "status": "ok", 
            "version": "v0.2.x",
            "pydantic_available": True,
            "features": ["自動推論", "明示的アノテーション", "Pydantic 統合"]
        }

    return app


# Lambda 関数のエントリーポイント
lambda_handler = create_lambda_handler(create_app)


# ローカルテスト用コード
if __name__ == "__main__":
    if not PYDANTIC_AVAILABLE:
        print("Pydantic がインストールされていないため、テストを実行できません。")
        sys.exit(1)

    # テストケース 1: FastAPI 風ユーザー作成（正常）
    test_event_1 = {
        "httpMethod": "POST",
        "path": "/users/fastapi-style",
        "queryStringParameters": None,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"name": "Alice Johnson", "email": "alice@example.com", "age": 28}),
    }

    print("=== Test 1: FastAPI 風ユーザー作成（正常） ===")
    result1 = lambda_handler(test_event_1, None)
    print(json.dumps(result1, indent=2, ensure_ascii=False))

    # テストケース 2: FastAPI 風ユーザー作成（バリデーションエラー）
    test_event_2 = {
        "httpMethod": "POST",
        "path": "/users/fastapi-style",
        "queryStringParameters": None,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"name": "", "email": "invalid@example.com", "age": -5}),
    }

    print("\n=== Test 2: Pydantic バリデーションエラー ===")
    result2 = lambda_handler(test_event_2, None)
    print(json.dumps(result2, indent=2, ensure_ascii=False))

    # テストケース 3: パスパラメータ自動注入
    test_event_3 = {
        "httpMethod": "GET",
        "path": "/users/123/fastapi-style",
        "queryStringParameters": None,
        "headers": {},
        "body": None,
    }

    print("\n=== Test 3: パスパラメータ自動注入 ===")
    result3 = lambda_handler(test_event_3, None)
    print(json.dumps(result3, indent=2, ensure_ascii=False))

    # テストケース 4: クエリパラメータ自動注入
    test_event_4 = {
        "httpMethod": "GET",
        "path": "/users/search",
        "queryStringParameters": {"name": "Bob", "age": "30"},
        "headers": {},
        "body": None,
    }

    print("\n=== Test 4: クエリパラメータ自動注入 ===")
    result4 = lambda_handler(test_event_4, None)
    print(json.dumps(result4, indent=2, ensure_ascii=False))

    # テストケース 5: 従来方式との互換性
    test_event_5 = {
        "httpMethod": "POST",
        "path": "/users/traditional",
        "queryStringParameters": None,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"name": "Charlie Brown", "email": "charlie@example.com", "age": 22}),
    }

    print("\n=== Test 5: 従来方式との互換性 ===")
    result5 = lambda_handler(test_event_5, None)
    print(json.dumps(result5, indent=2, ensure_ascii=False))

    # テストケース 6: 引数なしの関数
    test_event_6 = {
        "httpMethod": "GET",
        "path": "/health",
        "queryStringParameters": None,
        "headers": {},
        "body": None,
    }

    print("\n=== Test 6: 引数なしの関数 ===")
    result6 = lambda_handler(test_event_6, None)
    print(json.dumps(result6, indent=2, ensure_ascii=False))