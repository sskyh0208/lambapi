"""
03. 認証機能 - JWT 認証とロールベースアクセス制御

lambapi の統合認証システムを使った実用的なサンプルです。
CurrentUser, RequireRole, OptionalAuth アノテーションの使い方を学習できます。
"""

from dataclasses import dataclass
from typing import Optional
from lambapi import API, Response, create_lambda_handler
from lambapi.annotations import Body, Path, Query, CurrentUser, RequireRole, OptionalAuth
from lambapi.auth import DynamoDBAuth, BaseUser


@dataclass
class User(BaseUser):
    """ユーザーモデル（BaseUser を継承）"""

    name: str
    email: str
    role: str  # "user", "admin", "moderator"


@dataclass
class LoginRequest:
    """ログインリクエスト"""

    email: str
    password: str


@dataclass
class PostData:
    """投稿データ"""

    title: str
    content: str
    category: Optional[str] = None


def create_app(event, context):
    app = API(event, context)

    # 認証システムの設定
    # 注意: 実際の使用時は環境変数で DynamoDB テーブル名を設定してください
    try:
        auth = DynamoDBAuth(
            table_name="users",  # 環境変数: DYNAMODB_TABLE_NAME
            user_model=User,
            region_name="ap-northeast-1",
        )
        app.include_auth(auth)
        AUTH_ENABLED = True
    except Exception as e:
        print(f"認証システムが無効です（テスト用）: {e}")
        AUTH_ENABLED = False

    # === 認証不要なエンドポイント ===

    @app.get("/")
    def public_home():
        """パブリックなホームページ"""
        return {
            "message": "Welcome to lambapi with authentication!",
            "auth_enabled": AUTH_ENABLED,
            "endpoints": {
                "public": ["/", "/login", "/posts"],
                "auth_required": ["/profile", "/posts (POST)"],
                "admin_only": ["/admin/*"],
            },
        }

    @app.post("/login")
    def login(credentials: LoginRequest):
        """ログイン（認証システムのデモ用）"""
        # 注意: 実際の実装では DynamoDB から認証
        demo_users = {
            "user@example.com": {"password": "password", "role": "user", "name": "Demo User"},
            "admin@example.com": {"password": "admin", "role": "admin", "name": "Demo Admin"},
        }

        user_data = demo_users.get(credentials.email)
        if not user_data or user_data["password"] != credentials.password:
            return Response({"error": "Invalid credentials"}, status_code=401)

        return {
            "message": "Login successful",
            "token": "demo-jwt-token",  # 実際は JWT を生成
            "user": {
                "email": credentials.email,
                "name": user_data["name"],
                "role": user_data["role"],
            },
        }

    # === 認証が必要なエンドポイント ===

    if AUTH_ENABLED:

        @app.get("/profile")
        def get_profile(current_user: User = CurrentUser()):
            """プロフィール取得（認証必須）"""
            return {
                "message": "Your profile",
                "user": {
                    "id": current_user.id,
                    "name": current_user.name,
                    "email": current_user.email,
                    "role": current_user.role,
                },
            }

        @app.post("/posts")
        def create_post(post_data: PostData, current_user: User = CurrentUser()):
            """投稿作成（認証必須）"""
            return Response(
                {
                    "message": "Post created",
                    "post": {
                        "id": f"post_{hash(post_data.title)}",
                        "title": post_data.title,
                        "content": post_data.content,
                        "category": post_data.category,
                        "author": current_user.name,
                        "author_id": current_user.id,
                    },
                },
                status_code=201,
            )

        @app.delete("/admin/posts/{post_id}")
        def delete_post(post_id: str, admin_user: User = RequireRole(roles=["admin", "moderator"])):
            """投稿削除（管理者・モデレーター専用）"""
            return {
                "message": f"Post {post_id} deleted by {admin_user.name}",
                "deleted_by": {
                    "id": admin_user.id,
                    "name": admin_user.name,
                    "role": admin_user.role,
                },
            }

    # === オプショナル認証のエンドポイント ===

    @app.get("/posts")
    def list_posts(category: Optional[str] = None, user: Optional[User] = OptionalAuth()):
        """投稿一覧（オプショナル認証）"""
        posts = [
            {"id": "post_1", "title": "Public Post", "category": "general"},
            {"id": "post_2", "title": "Tech Post", "category": "tech"},
        ]

        # カテゴリーフィルター
        if category:
            posts = [p for p in posts if p["category"] == category]

        result = {"posts": posts, "total": len(posts), "filter": {"category": category}}

        # ログイン済みユーザーには追加情報を提供
        if user:
            result["personalized"] = True
            result["user_info"] = {"name": user.name, "role": user.role}
            # 管理者には非公開投稿も表示
            if user.role in ["admin", "moderator"]:
                result["posts"].append(
                    {"id": "post_private", "title": "Admin Only Post", "category": "admin"}
                )
        else:
            result["personalized"] = False

        return result

    return app


lambda_handler = create_lambda_handler(create_app)


if __name__ == "__main__":
    # 認証機能のテスト（DynamoDB なしでのデモ）
    print("=== 認証機能テスト（デモモード） ===")

    import json

    def test_request(method, path, body=None, query=None, headers=None):
        event = {
            "httpMethod": method,
            "path": path,
            "queryStringParameters": query,
            "headers": headers or {"Content-Type": "application/json"},
            "body": json.dumps(body) if body else None,
        }
        result = lambda_handler(event, None)
        print(f"{method} {path}: {result['statusCode']}")
        response_body = json.loads(result["body"])
        if result["statusCode"] >= 400:
            print(f"  Error: {response_body}")
        else:
            print(f"  Success: {response_body.get('message', 'OK')}")

    # テストシーケンス
    test_request("GET", "/")
    test_request("POST", "/login", {"email": "user@example.com", "password": "password"})
    test_request("GET", "/posts")
    test_request("GET", "/posts", query={"category": "tech"})

    print("\n 注意: 実際の認証テストには DynamoDB の設定が必要です")
    print("詳細は lambapi のドキュメントを参照してください")
