"""
DynamoDB 認証機能の使用例

このサンプルでは、DynamoDB を使った認証システムの実装方法を示します。
"""

import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lambapi import API, Response, create_lambda_handler, DynamoDBAuth


def create_app(event, context):
    """認証機能付きアプリケーション"""
    app = API(event, context)

    # DynamoDB 認証システムの初期化
    # テーブル名: "users" (id と password カラムが必須)
    # use_email=True の場合、email でもログイン可能
    auth = DynamoDBAuth(
        table_name="users",
        id_field="id",
        use_email=True,  # email でのログインを有効化
        region_name="us-east-1",
    )

    # 認証システムを API に追加
    # 自動的に /auth/signup, /auth/login, /auth/logout エンドポイントが追加される
    app.include_auth(auth)

    # ===== パブリックエンドポイント =====

    @app.get("/")
    def public_root():
        """パブリック API（認証不要）"""
        return {"message": "Welcome to authenticated API!", "public": True}

    @app.get("/health")
    def health_check():
        """ヘルスチェック"""
        return {"status": "ok", "auth_enabled": True}

    # ===== 認証が必要なエンドポイント =====

    @app.get("/profile")
    @auth.require_auth
    def get_profile(request):
        """ユーザープロフィール取得（認証必須）"""
        user = request.user  # 認証デコレータで自動的に設定される
        return {
            "message": "Profile accessed successfully",
            "user": {"user_id": user.get("user_id"), "email": user.get("email")},
        }

    @app.get("/dashboard")
    @auth.require_auth
    def get_dashboard(request):
        """ダッシュボード（認証必須）"""
        user = request.user
        return {
            "message": f"Welcome to dashboard, {user.get('user_id')}!",
            "data": [
                {"item": "Item 1", "value": 100},
                {"item": "Item 2", "value": 200},
                {"item": "Item 3", "value": 300},
            ],
        }

    @app.post("/protected-action")
    @auth.require_auth
    def protected_action(request):
        """保護されたアクション（認証必須）"""
        user = request.user
        action_data = request.json()

        return {
            "message": "Protected action executed",
            "user_id": user.get("user_id"),
            "action": action_data.get("action", "unknown"),
            "timestamp": int(__import__("time").time()),
        }

    # ===== カスタムエラーハンドリング =====

    @app.error_handler(Exception)
    def handle_auth_errors(error, request, context):
        """認証エラーのカスタムハンドリング"""
        if "Authentication" in str(type(error)):
            return Response(
                {"error": "Authentication required", "message": str(error)}, status_code=401
            )
        elif "Authorization" in str(type(error)):
            return Response({"error": "Access denied", "message": str(error)}, status_code=403)
        else:
            return Response(
                {"error": "Internal server error", "message": str(error)}, status_code=500
            )

    return app


# Lambda 関数のエントリーポイント
lambda_handler = create_lambda_handler(create_app)


# ローカルテスト用コード
if __name__ == "__main__":
    print("=== DynamoDB 認証機能テスト ===\n")

    # テストケース 1: パブリック API
    test_event_1 = {
        "httpMethod": "GET",
        "path": "/",
        "queryStringParameters": None,
        "headers": {"Content-Type": "application/json"},
        "body": None,
    }

    print("Test 1: パブリック API アクセス")
    result1 = lambda_handler(test_event_1, None)
    print(json.dumps(result1, indent=2, ensure_ascii=False))
    print()

    # テストケース 2: ユーザー登録
    test_event_2 = {
        "httpMethod": "POST",
        "path": "/auth/signup",
        "queryStringParameters": None,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(
            {
                "id": "testuser123",
                "email": "test@example.com",
                "password": "securepassword123",
                "name": "Test User",
            }
        ),
    }

    print("Test 2: ユーザー登録")
    result2 = lambda_handler(test_event_2, None)
    print(json.dumps(result2, indent=2, ensure_ascii=False))
    print()

    # テストケース 3: ログイン
    test_event_3 = {
        "httpMethod": "POST",
        "path": "/auth/login",
        "queryStringParameters": None,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(
            {"id": "testuser123", "password": "securepassword123"}  # id または email でログイン
        ),
    }

    print("Test 3: ログイン")
    result3 = lambda_handler(test_event_3, None)
    print(json.dumps(result3, indent=2, ensure_ascii=False))
    print()

    # トークンを取得（実際のテストでは result3 からトークンを抽出）
    sample_token = (
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
        "eyJ1c2VyX2lkIjoidGVzdHVzZXIxMjMiLCJlbWFpbCI6InRlc3RAZXhhbXBsZS5jb20i"
        "LCJpYXQiOjE3MzM2MjE4MjEsImV4cCI6MTczMzYyNTQyMX0."
        "dummy_signature"
    )

    # テストケース 4: 認証が必要なエンドポイント（認証ヘッダーなし）
    test_event_4 = {
        "httpMethod": "GET",
        "path": "/profile",
        "queryStringParameters": None,
        "headers": {"Content-Type": "application/json"},
        "body": None,
    }

    print("Test 4: 認証必須エンドポイント（認証ヘッダーなし）")
    result4 = lambda_handler(test_event_4, None)
    print(json.dumps(result4, indent=2, ensure_ascii=False))
    print()

    # テストケース 5: 認証が必要なエンドポイント（認証ヘッダーあり）
    test_event_5 = {
        "httpMethod": "GET",
        "path": "/profile",
        "queryStringParameters": None,
        "headers": {"Content-Type": "application/json", "Authorization": f"Bearer {sample_token}"},
        "body": None,
    }

    print("Test 5: 認証必須エンドポイント（認証ヘッダーあり）")
    result5 = lambda_handler(test_event_5, None)
    print(json.dumps(result5, indent=2, ensure_ascii=False))
    print()

    # テストケース 6: ログアウト
    test_event_6 = {
        "httpMethod": "POST",
        "path": "/auth/logout",
        "queryStringParameters": None,
        "headers": {"Content-Type": "application/json", "Authorization": f"Bearer {sample_token}"},
        "body": None,
    }

    print("Test 6: ログアウト")
    result6 = lambda_handler(test_event_6, None)
    print(json.dumps(result6, indent=2, ensure_ascii=False))
    print()

    print("=== 使用方法の説明 ===")
    print(
        """
1. DynamoDB テーブルの作成:
   - テーブル名: "users"
   - プライマリキー: "id" (String)
   - 必須カラム: "id", "password"
   - オプション: "email", その他任意のフィールド

2. 基本的な使用方法:
   ```python
   from lambapi import API, DynamoDBAuth

   def create_app(event, context):
       app = API(event, context)
       auth = DynamoDBAuth("users", use_email=True)
       app.include_auth(auth)

       @app.get("/protected")
       @auth.require_auth
       def protected_endpoint(request):
           user = request.user  # 認証されたユーザー情報
           return {"user_id": user["user_id"]}
   ```

3. 自動追加されるエンドポイント:
   - POST /auth/signup : ユーザー登録
   - POST /auth/login  : ログイン
   - POST /auth/logout : ログアウト

4. 認証ヘッダーの形式:
   Authorization: Bearer <JWT_TOKEN>

5. DynamoDB テーブル例:
   {
     "id": "user123",
     "password": "$2b$12$hashed_password...",
     "email": "user@example.com",
     "name": "John Doe",
     "created_at": 1633024800
   }
"""
    )
