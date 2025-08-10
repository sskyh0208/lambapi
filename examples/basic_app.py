"""
API 使用例 - v0.2.x 統合アノテーションシステム
Lambda 関数でのモダンな API の実装例
"""

import json
import sys
import os
from dataclasses import dataclass
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lambapi import API, Response, create_lambda_handler
from lambapi.annotations import Body, Path, Query


@dataclass
class User:
    """ユーザーデータクラス"""
    name: str
    email: str
    age: Optional[int] = None


@dataclass
class LoginCredentials:
    """ログイン認証情報"""
    username: str
    password: str


# グローバルスコープでのルート定義（重要：パフォーマンス最適化のため）
def create_app(event, context):
    """アプリケーション作成関数"""
    app = API(event, context)

    # CORS 設定
    app.enable_cors(
        origins=["*"],
        methods=["GET", "POST", "PUT", "DELETE"],
        headers=["Content-Type", "Authorization"]
    )

    # ===== ルート定義 =====

    @app.get("/")
    def hello_world():
        """基本的な Hello World"""
        msg = "Hello lambapi v0.2.x!"
        print(msg)
        return {"message": msg}

    @app.get("/health")
    def health_check():
        """ヘルスチェック"""
        return {"status": "ok", "service": "lambapi", "version": "v0.2.x"}

    @app.get("/users/{user_id}")
    def get_user(user_id: int = Path(), include_details: bool = Query(default=False)):
        """ユーザー取得（統合アノテーションシステム使用）"""
        user_data = {
            "user_id": user_id,
            "name": f"User {user_id}",
            "email": f"user{user_id}@example.com",
        }

        if include_details:
            user_data["details"] = {
                "created_at": "2024-01-01T00:00:00Z",
                "last_login": "2024-01-02T10:30:00Z",
            }

        return user_data

    @app.post("/users")
    def create_user(user: User = Body()):
        """ユーザー作成（統合アノテーションシステム - 明示的アノテーション）
        
        v0.2.x の統合アノテーションシステムにより自動バリデーションが実行されます。
        データクラスによる型安全性とバリデーションを提供。
        """
        # 作成処理のシミュレーション
        new_user = {
            "id": f"user_{hash(user.email)}",
            "name": user.name,
            "email": user.email,
            "age": user.age,
            "created_at": "2025-01-01T00:00:00Z",
        }

        return Response(
            {"message": "User created successfully", "user": new_user}, 
            status_code=201
        )

    @app.post("/users/auto")
    def create_user_auto(user: User):
        """ユーザー作成（自動推論版）
        
        FastAPI 風の自動推論により、User データクラスは自動的に Body として扱われます。
        """
        return Response({
            "message": "User created with auto inference",
            "user": {
                "id": f"auto_{hash(user.email)}",
                "name": user.name,
                "email": user.email,
                "age": user.age
            }
        }, status_code=201)

    @app.put("/users/{user_id}")
    def update_user(
        user_id: int = Path(),
        user: User = Body()
    ):
        """ユーザー更新（混合アノテーション）
        
        Path と Body アノテーションを混合して使用する例。
        統合アノテーションシステムにより両方のパラメータを統一的に処理。
        """
        return {
            "message": f"User {user_id} updated successfully",
            "user": {
                "id": user_id,
                "name": user.name,
                "email": user.email,
                "age": user.age,
                "updated_at": "2025-01-01T12:00:00Z"
            }
        }

    @app.delete("/users/{user_id}")
    def delete_user(user_id: int):  # 自動推論で Path
        """ユーザー削除（自動推論）
        
        user_id は自動的に Path パラメータとして推論されます。
        """
        return Response({"message": f"User {user_id} deleted"}, status_code=204)

    @app.get("/api/v1/products/{category}")
    def get_products_by_category(
        category: str = Path(),
        limit: int = Query(default=10),
        offset: int = Query(default=0)
    ):
        """カテゴリ別商品取得（完全アノテーション版）
        
        Path と複数の Query パラメータを明示的にアノテーション。
        """

        # 商品データのシミュレーション
        products = [
            {
                "id": f"prod-{category}-{i}",
                "name": f"{category.title()} Product {i}",
                "price": 100 + i * 10,
                "category": category,
            }
            for i in range(offset + 1, offset + limit + 1)
        ]

        return {
            "category": category,
            "products": products,
            "pagination": {
                "limit": limit,
                "offset": offset,
                "total": 100,  # 実際のアプリでは DB から取得
            },
        }

    @app.get("/api/v1/products/search")
    def search_products(
        q: str = Query(),
        category: Optional[str] = Query(default=None),
        min_price: Optional[int] = Query(default=None),
        max_price: Optional[int] = Query(default=None)
    ):
        """商品検索（複数クエリパラメータの例）
        
        複数のオプションクエリパラメータを使用した検索機能。
        """
        # 検索結果のシミュレーション
        results = []
        for i in range(1, 6):  # 5 件の結果をシミュレート
            price = 50 + i * 25
            if min_price and price < min_price:
                continue
            if max_price and price > max_price:
                continue
                
            results.append({
                "id": f"search-{i}",
                "name": f"{q} Product {i}",
                "price": price,
                "category": category or "general"
            })
        
        return {
            "query": q,
            "filters": {
                "category": category,
                "min_price": min_price,
                "max_price": max_price
            },
            "results": results,
            "count": len(results)
        }

    @app.post("/api/v1/auth/login")
    def login(credentials: LoginCredentials):
        """ログイン例（データクラスによる自動バリデーション）
        
        LoginCredentials データクラスが自動的に Body として推論され、
        バリデーションが実行されます。
        """
        # 簡単な認証チェック
        if credentials.username == "admin" and credentials.password == "password":
            return {
                "token": "dummy-jwt-token-v2",
                "expires_in": 3600,
                "user": {
                    "id": "admin-user", 
                    "username": credentials.username, 
                    "role": "administrator"
                },
            }
        else:
            return Response({"error": "Invalid credentials"}, status_code=401)

    # エラーハンドリングの例
    @app.get("/error-test")
    def error_test(error_type: str = Query(default="general")):
        """エラーテスト用エンドポイント（Query アノテーション使用）
        
        Query アノテーションによりクエリパラメータを型安全に取得。
        """
        if error_type == "not_found":
            return Response({"error": "Resource not found"}, status_code=404)
        elif error_type == "server_error":
            raise Exception("Intentional server error for testing")
        else:
            return {
                "message": "No error", 
                "error_type_requested": error_type,
                "available_types": ["general", "not_found", "server_error"]
            }

    @app.get("/demo/mixed/{item_id}")
    def mixed_parameters_demo(
        item_id: str = Path(),
        format: str = Query(default="json"),
        include_meta: bool = Query(default=False),
        user_agent: Optional[str] = Query(alias="user-agent", default=None)
    ):
        """混合パラメータのデモエンドポイント
        
        Path、Query（デフォルト値付き）、Query（エイリアス付き）の組み合わせ例。
        統合アノテーションシステムの柔軟性を示すデモ。
        """
        result = {
            "item_id": item_id,
            "format": format,
            "data": f"Sample data for {item_id}"
        }
        
        if include_meta:
            result["metadata"] = {
                "timestamp": "2025-01-01T00:00:00Z",
                "version": "v0.2.x",
                "user_agent": user_agent
            }
        
        return result

    return app


# Lambda 関数のエントリーポイント
lambda_handler = create_lambda_handler(create_app)


# ローカルテスト用コード（v0.2.x 対応）
if __name__ == "__main__":
    print("=== lambapi v0.2.x 統合アノテーションシステム テスト ===")
    print()
    
    # テストケース 1: 基本の GET
    test_event_1 = {
        "httpMethod": "GET",
        "path": "/",
        "queryStringParameters": None,
        "headers": {"Content-Type": "application/json"},
        "body": None,
    }

    print("=== Test 1: Basic GET (v0.2.x) ===")
    result1 = lambda_handler(test_event_1, None)
    print(json.dumps(result1, indent=2, ensure_ascii=False))

    # テストケース 2: 統合アノテーションシステム（Path + Query）
    test_event_2 = {
        "httpMethod": "GET",
        "path": "/users/123",
        "queryStringParameters": {"include_details": "true"},
        "headers": {},
        "body": None,
    }

    print("\n=== Test 2: Path + Query annotations ===")
    result2 = lambda_handler(test_event_2, None)
    print(json.dumps(result2, indent=2, ensure_ascii=False))

    # テストケース 3: データクラス自動推論（Body）
    test_event_3 = {
        "httpMethod": "POST",
        "path": "/users",
        "queryStringParameters": None,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"name": "Alice Smith", "email": "alice@example.com", "age": 28}),
    }

    print("\n=== Test 3: Dataclass Body annotation ===")
    result3 = lambda_handler(test_event_3, None)
    print(json.dumps(result3, indent=2, ensure_ascii=False))

    # テストケース 4: 自動推論版ユーザー作成
    test_event_4 = {
        "httpMethod": "POST",
        "path": "/users/auto",
        "queryStringParameters": None,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"name": "Bob Wilson", "email": "bob@example.com"}),
    }

    print("\n=== Test 4: Auto inference Body ===")
    result4 = lambda_handler(test_event_4, None)
    print(json.dumps(result4, indent=2, ensure_ascii=False))

    # テストケース 5: 複数クエリパラメータの検索
    test_event_5 = {
        "httpMethod": "GET",
        "path": "/api/v1/products/search",
        "queryStringParameters": {
            "q": "laptop",
            "category": "electronics", 
            "min_price": "50",
            "max_price": "200"
        },
        "headers": {},
        "body": None,
    }

    print("\n=== Test 5: Multiple Query parameters ===")
    result5 = lambda_handler(test_event_5, None)
    print(json.dumps(result5, indent=2, ensure_ascii=False))
    
    # テストケース 6: 混合パラメータデモ
    test_event_6 = {
        "httpMethod": "GET",
        "path": "/demo/mixed/item-123",
        "queryStringParameters": {
            "format": "xml",
            "include_meta": "true",
            "user-agent": "lambapi-test-client/1.0"
        },
        "headers": {},
        "body": None,
    }

    print("\n=== Test 6: Mixed parameters demo ===")
    result6 = lambda_handler(test_event_6, None)
    print(json.dumps(result6, indent=2, ensure_ascii=False))

    # テストケース 7: 認証例（データクラス）
    test_event_7 = {
        "httpMethod": "POST",
        "path": "/api/v1/auth/login",
        "queryStringParameters": None,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"username": "admin", "password": "password"}),
    }

    print("\n=== Test 7: Login with dataclass validation ===")
    result7 = lambda_handler(test_event_7, None)
    print(json.dumps(result7, indent=2, ensure_ascii=False))

    print("\n=== All tests completed for lambapi v0.2.x ===")
