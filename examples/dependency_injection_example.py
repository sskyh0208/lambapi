"""
依存性注入（Dependency Injection）機能のサンプル

FastAPI 風の Query, Path, Body, Authenticated 依存性注入の実用例
"""

import json
import sys
import os
from dataclasses import dataclass
from typing import Optional, List, Dict, Any, Union

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lambapi import API, Response, create_lambda_handler, Query, Path, Body, Authenticated
from lambapi.auth import DynamoDBAuth
from pynamodb.models import Model
from pynamodb.attributes import (
    UnicodeAttribute,
    BooleanAttribute,
    NumberAttribute,
    UTCDateTimeAttribute,
)
from pynamodb.indexes import GlobalSecondaryIndex, AllProjection
import datetime


# データクラス定義
@dataclass
class CreateUserRequest:
    name: str
    email: str
    age: Optional[int] = None
    roles: Optional[List[str]] = None


@dataclass
class UpdateUserRequest:
    name: Optional[str] = None
    email: Optional[str] = None
    age: Optional[int] = None


@dataclass
class CreatePostRequest:
    title: str
    content: str
    published: bool = False
    tags: Optional[List[str]] = None


# PynamoDBモデル定義
class EmailIndex(GlobalSecondaryIndex):
    """Email検索用のGSI"""

    class Meta:
        index_name = "email-index"
        projection = AllProjection()
        read_capacity_units = 1
        write_capacity_units = 1

    email = UnicodeAttribute(hash_key=True)


class User(Model):
    """カスタムユーザーモデル（PynamoDB）"""

    class Meta:
        table_name = "dependency_injection_users"
        region = "us-east-1"
        host = "http://localhost:8000"  # ローカル DynamoDB 用

    id = UnicodeAttribute(hash_key=True)
    password = UnicodeAttribute()
    email = UnicodeAttribute()
    email_index = EmailIndex()
    name = UnicodeAttribute()
    role = UnicodeAttribute(default="user")
    is_active = BooleanAttribute(default=True)
    created_at = UTCDateTimeAttribute(default=datetime.datetime.utcnow)


class UserSession(Model):
    """セッション管理モデル"""

    class Meta:
        table_name = "dependency_injection_sessions"
        region = "us-east-1"
        host = "http://localhost:8000"  # ローカル DynamoDB 用

    id = UnicodeAttribute(hash_key=True)
    user_id = UnicodeAttribute()
    token = UnicodeAttribute()
    expires_at = UTCDateTimeAttribute()
    created_at = UTCDateTimeAttribute(default=datetime.datetime.utcnow)
    ttl = NumberAttribute()


def create_app(event: Dict[str, Any], context: Any) -> API:
    """アプリケーション作成関数"""
    app = API(event, context)

    # 認証システムの初期化
    # nosec B106 - テスト用のハードコードされたキー
    auth = DynamoDBAuth(
        user_model=User,
        secret_key="demo-secret-key-for-dependency-injection",  # nosec B106
        session_model=UserSession,
        expiration=3600,
        is_email_login=True,
        is_role_permission=True,
        token_include_fields=["id", "email", "name", "role", "is_active"],
    )

    # ===== 基本的な依存性注入の例 =====

    @app.get("/search")
    def search_items(
        # クエリパラメータの依存性注入
        query: str = Query(..., description="検索クエリ", min_length=1, max_length=100),
        limit: int = Query(10, ge=1, le=100, description="結果の上限数"),
        offset: int = Query(0, ge=0, description="オフセット"),
        category: str = Query(
            "all", regex=r"^(electronics|books|clothing|all)$", description="カテゴリー"
        ),
        sort: str = Query("relevance", alias="sort_by", description="ソート方法"),
    ) -> Dict[str, Any]:
        """検索機能（クエリパラメータの依存性注入デモ）"""
        return {
            "query": query,
            "limit": limit,
            "offset": offset,
            "category": category,
            "sort": sort,
            "results": f"{limit}件の結果（{offset}件目から）を表示",
        }

    @app.get("/users/{user_id}/posts/{post_id}")
    def get_user_post(
        # パスパラメータの依存性注入
        user_id: str = Path(..., description="ユーザー ID", min_length=1),
        post_id: int = Path(..., gt=0, description="投稿 ID"),
    ) -> Dict[str, Any]:
        """特定ユーザーの投稿取得（パスパラメータの依存性注入デモ）"""
        return {
            "user_id": user_id,
            "post_id": post_id,
            "post": {
                "title": f"ユーザー {user_id} の投稿 {post_id}",
                "content": "投稿内容...",
                "author": user_id,
            },
        }

    @app.post("/users")
    def create_user(
        # リクエストボディの依存性注入
        user_data: CreateUserRequest = Body(..., description="ユーザー作成データ")
    ) -> Dict[str, Any]:
        """ユーザー作成（リクエストボディの依存性注入デモ）"""
        return {
            "message": "ユーザーが作成されました",
            "user": {
                "name": user_data.name,
                "email": user_data.email,
                "age": user_data.age,
                "roles": user_data.roles or ["user"],
            },
        }

    # ===== 認証機能との組み合わせ例 =====

    @app.get("/profile")
    @auth.require_role("user")
    def get_profile(
        # 認証ユーザーの依存性注入
        user: User = Authenticated(..., description="認証されたユーザー")
    ) -> Dict[str, Any]:
        """プロフィール取得（認証ユーザーの依存性注入デモ）"""
        return {
            "user_id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat() if user.created_at else None,
        }

    @app.put("/users/{target_user_id}")
    @auth.require_role("admin")
    def update_user_as_admin(
        # 複数の依存性注入を組み合わせ
        admin: User = Authenticated(..., description="管理者ユーザー"),
        target_user_id: str = Path(..., description="対象ユーザー ID", min_length=1),
        new_role: str = Query(..., description="新しいロール", regex=r"^(user|admin|moderator)$"),
        user_data: UpdateUserRequest = Body(..., description="ユーザー更新データ"),
    ) -> Dict[str, Any]:
        """管理者による他ユーザー更新（全ての依存性注入を組み合わせたデモ）"""
        return {
            "message": f"管理者 {admin.id} がユーザー {target_user_id} を更新しました",
            "admin_user": admin.id,
            "target_user": target_user_id,
            "new_role": new_role,
            "updates": {"name": user_data.name, "email": user_data.email, "age": user_data.age},
        }

    @app.post("/posts")
    @auth.require_role(["user", "admin"])
    def create_post(
        # 認証ユーザーとリクエストボディの組み合わせ
        user: User = Authenticated(..., description="投稿者"),
        post_data: CreatePostRequest = Body(..., description="投稿データ"),
    ) -> Dict[str, Any]:
        """投稿作成（認証 + ボディの依存性注入デモ）"""
        return {
            "message": "投稿が作成されました",
            "post": {
                "title": post_data.title,
                "content": post_data.content,
                "published": post_data.published,
                "tags": post_data.tags or [],
                "author_id": user.id,
                "author_role": user.role,
            },
        }

    # ===== エラーハンドリング例 =====

    @app.get("/products/{product_id}")
    def get_product(
        product_id: int = Path(..., gt=0, le=999999, description="商品 ID"),
        include_reviews: bool = Query(False, description="レビューを含めるか"),
        max_reviews: int = Query(5, ge=1, le=50, description="レビュー最大件数"),
    ) -> Union[Dict[str, Any], Response]:
        """商品詳細取得（バリデーションエラーのデモ）"""
        # 存在しない商品の場合
        if product_id > 1000:
            return Response({"error": "商品が見つかりません"}, status_code=404)

        return {
            "product_id": product_id,
            "name": f"商品 {product_id}",
            "include_reviews": include_reviews,
            "max_reviews": max_reviews if include_reviews else 0,
        }

    # ===== 従来の方式との混在例 =====

    @app.get("/legacy")
    def legacy_handler(request: Any) -> Dict[str, Any]:
        """従来の方式（互換性のデモ）"""
        query_param = request.query_params.get("q", "default")
        return {"query": query_param, "type": "legacy"}

    @app.get("/modern")
    def modern_handler(q: str = Query("default", description="クエリパラメータ")) -> Dict[str, str]:
        """新しい依存性注入方式"""
        return {"query": q, "type": "modern"}

    return app


# Lambda 関数のエントリーポイント
lambda_handler = create_lambda_handler(create_app)


# ローカルテスト用コード
if __name__ == "__main__":
    print("=== 依存性注入機能デモ ===\n")

    # テストケース 1: クエリパラメータの依存性注入
    test_event_1 = {
        "httpMethod": "GET",
        "path": "/search",
        "queryStringParameters": {
            "query": "Python books",
            "limit": "20",
            "category": "books",
            "sort_by": "relevance",
        },
        "headers": {},
        "body": None,
    }

    print("=== Test 1: クエリパラメータの依存性注入 ===")
    result1 = lambda_handler(test_event_1, None)
    print(json.dumps(result1, indent=2, ensure_ascii=False))

    # テストケース 2: パスパラメータの依存性注入
    test_event_2: Dict[str, Any] = {
        "httpMethod": "GET",
        "path": "/users/alice/posts/123",
        "queryStringParameters": None,
        "headers": {},
        "body": None,
    }

    print("\n=== Test 2: パスパラメータの依存性注入 ===")
    result2 = lambda_handler(test_event_2, None)
    print(json.dumps(result2, indent=2, ensure_ascii=False))

    # テストケース 3: リクエストボディの依存性注入
    test_event_3 = {
        "httpMethod": "POST",
        "path": "/users",
        "queryStringParameters": None,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(
            {
                "name": "John Doe",
                "email": "john@example.com",
                "age": 30,
                "roles": ["user", "beta_tester"],
            }
        ),
    }

    print("\n=== Test 3: リクエストボディの依存性注入 ===")
    result3 = lambda_handler(test_event_3, None)
    print(json.dumps(result3, indent=2, ensure_ascii=False))

    # テストケース 4: バリデーションエラー
    test_event_4 = {
        "httpMethod": "GET",
        "path": "/search",
        "queryStringParameters": {
            "query": "",  # 最小長 1 文字の制約違反
            "limit": "200",  # 上限 100 の制約違反
            "category": "invalid",  # 正規表現制約違反
        },
        "headers": {},
        "body": None,
    }

    print("\n=== Test 4: バリデーションエラーのテスト ===")
    result4 = lambda_handler(test_event_4, None)
    print(json.dumps(result4, indent=2, ensure_ascii=False))

    # テストケース 5: 従来方式との比較
    test_event_5 = {
        "httpMethod": "GET",
        "path": "/legacy",
        "queryStringParameters": {"q": "legacy test"},
        "headers": {},
        "body": None,
    }

    print("\n=== Test 5: 従来方式 ===")
    result5 = lambda_handler(test_event_5, None)
    print(json.dumps(result5, indent=2, ensure_ascii=False))

    test_event_6 = {
        "httpMethod": "GET",
        "path": "/modern",
        "queryStringParameters": {"q": "modern test"},
        "headers": {},
        "body": None,
    }

    print("\n=== Test 6: 新しい依存性注入方式 ===")
    result6 = lambda_handler(test_event_6, None)
    print(json.dumps(result6, indent=2, ensure_ascii=False))

    print("\n=== デモ完了 ===")
    print("認証機能付きのエンドポイントをテストするには、")
    print("先に /auth/signup でユーザー登録と /auth/login でログインが必要です。")
