"""
CORS 機能の使用例

この例では、CORS プリフライトリクエストの自動処理機能を使った
様々な CORS 設定パターンを紹介します。
"""

import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lambapi import API, Response, create_lambda_handler, CORSConfig, create_cors_config


def create_app(event, context):
    """CORS 機能を使ったアプリケーション作成関数"""
    app = API(event, context)

    # ===== パターン 1: グローバル CORS 設定 =====
    # すべてのルートに適用される CORS 設定
    app.enable_cors(
        origins=["https://example.com", "https://app.example.com"],
        methods=["GET", "POST", "PUT", "DELETE"],
        headers=["Content-Type", "Authorization", "X-API-Key"],
        allow_credentials=True,
        max_age=3600,  # プリフライトリクエストのキャッシュ時間（秒）
    )

    @app.get("/")
    def hello_world():
        """基本的なエンドポイント（グローバル CORS 設定が適用される）"""
        return {"message": "Hello CORS World!", "cors": "global"}

    @app.get("/users")
    def get_users():
        """ユーザー一覧取得（グローバル CORS 設定が適用される）"""
        return {"users": [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]}

    @app.post("/users")
    def create_user(request):
        """ユーザー作成（グローバル CORS 設定が適用される）"""
        user_data = request.json()
        return Response(
            {"message": "User created successfully", "user": {"id": 3, **user_data}},
            status_code=201,
        )

    # ===== パターン 2: ルートレベル CORS 設定（デフォルト） =====
    @app.get("/public", cors=True)
    def public_endpoint():
        """公開エンドポイント（デフォルトの CORS 設定を使用）"""
        return {"message": "Public endpoint", "cors": "route-default"}

    # ===== パターン 3: ルートレベル カスタム CORS 設定 =====
    # 特定のエンドポイントのみ異なる CORS 設定を適用
    strict_cors = create_cors_config(
        origins=["https://trusted.example.com"],  # 信頼できるオリジンのみ
        methods=["GET"],  # GET のみ許可
        headers=["Content-Type"],  # 最小限のヘッダーのみ
        allow_credentials=False,  # 認証情報は送信不可
        max_age=7200,  # 長めのキャッシュ時間
    )

    @app.get("/admin/stats", cors=strict_cors)
    def admin_stats():
        """管理者向け統計情報（厳格な CORS 設定）"""
        return {
            "message": "Admin statistics",
            "cors": "route-strict",
            "stats": {"users": 1000, "requests": 50000},
        }

    # ===== パターン 4: 開発用 CORS 設定 =====
    dev_cors = create_cors_config(
        origins="*",  # 開発時はすべてのオリジンを許可
        methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        headers=["*"],  # すべてのヘッダーを許可
        allow_credentials=False,
    )

    @app.get("/dev/test", cors=dev_cors)
    def dev_test():
        """開発・テスト用エンドポイント"""
        return {"message": "Development endpoint", "cors": "dev-open"}

    # ===== パターン 5: CORS 無効のエンドポイント =====
    @app.get("/internal")
    def internal_api():
        """内部 API（CORS ヘッダーなし）"""
        return {"message": "Internal API", "cors": "none"}

    # ===== パターン 6: 個別メソッドでの異なる CORS 設定 =====
    api_cors = create_cors_config(
        origins=["https://api-client.example.com"],
        methods=["GET", "POST"],
        headers=["Content-Type", "Authorization"],
    )

    @app.get("/api/data", cors=api_cors)
    def get_api_data():
        """API データ取得"""
        return {"data": "API response", "cors": "api-specific"}

    @app.post("/api/data", cors=api_cors)
    def post_api_data(request):
        """API データ投稿"""
        data = request.json()
        return {"message": "Data received", "received": data}

    # ===== エラーハンドリングのテスト =====
    @app.get("/error-test")
    def error_test():
        """エラーテスト（エラーレスポンスにも CORS ヘッダーが付与される）"""
        raise Exception("Test error for CORS")

    return app


# Lambda 関数のエントリーポイント
lambda_handler = create_lambda_handler(create_app)


# ローカルテスト用コード
if __name__ == "__main__":
    print("=== CORS 機能のテスト ===\n")

    # テストケース 1: 通常の GET リクエスト
    test_event_1 = {
        "httpMethod": "GET",
        "path": "/",
        "queryStringParameters": None,
        "headers": {"Origin": "https://example.com", "Content-Type": "application/json"},
        "body": None,
    }

    print("1. 通常の GET リクエスト（グローバル CORS）:")
    result1 = lambda_handler(test_event_1, None)
    print(f"Status: {result1['statusCode']}")
    print(f"CORS Origin: {result1['headers'].get('Access-Control-Allow-Origin')}")
    print(f"CORS Methods: {result1['headers'].get('Access-Control-Allow-Methods')}")
    print(f"Response: {result1['body']}\n")

    # テストケース 2: OPTIONS プリフライトリクエスト
    test_event_2 = {
        "httpMethod": "OPTIONS",
        "path": "/users",
        "queryStringParameters": None,
        "headers": {
            "Origin": "https://example.com",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type, Authorization",
        },
        "body": None,
    }

    print("2. OPTIONS プリフライトリクエスト:")
    result2 = lambda_handler(test_event_2, None)
    print(f"Status: {result2['statusCode']}")
    print(f"CORS Origin: {result2['headers'].get('Access-Control-Allow-Origin')}")
    print(f"CORS Methods: {result2['headers'].get('Access-Control-Allow-Methods')}")
    print(f"CORS Headers: {result2['headers'].get('Access-Control-Allow-Headers')}")
    print(f"Max-Age: {result2['headers'].get('Access-Control-Max-Age')}")
    print(f"Response Body: '{result2['body']}'\n")

    # テストケース 3: ルートレベル CORS 設定
    test_event_3 = {
        "httpMethod": "GET",
        "path": "/admin/stats",
        "queryStringParameters": None,
        "headers": {"Origin": "https://trusted.example.com", "Content-Type": "application/json"},
        "body": None,
    }

    print("3. ルートレベル厳格 CORS 設定:")
    result3 = lambda_handler(test_event_3, None)
    print(f"Status: {result3['statusCode']}")
    print(f"CORS Origin: {result3['headers'].get('Access-Control-Allow-Origin')}")
    print(f"CORS Methods: {result3['headers'].get('Access-Control-Allow-Methods')}")
    print(f"Response: {result3['body']}\n")

    # テストケース 4: 許可されていないオリジンからのリクエスト
    test_event_4 = {
        "httpMethod": "GET",
        "path": "/admin/stats",
        "queryStringParameters": None,
        "headers": {"Origin": "https://unauthorized.com", "Content-Type": "application/json"},
        "body": None,
    }

    print("4. 許可されていないオリジンからのリクエスト:")
    result4 = lambda_handler(test_event_4, None)
    print(f"Status: {result4['statusCode']}")
    print(f"CORS Origin: {result4['headers'].get('Access-Control-Allow-Origin')}")
    print(f"Response: {result4['body']}\n")

    # テストケース 5: 404 エラーでの CORS ヘッダー
    test_event_5 = {
        "httpMethod": "GET",
        "path": "/nonexistent",
        "queryStringParameters": None,
        "headers": {"Origin": "https://example.com", "Content-Type": "application/json"},
        "body": None,
    }

    print("5. 404 エラーでの CORS ヘッダー:")
    result5 = lambda_handler(test_event_5, None)
    print(f"Status: {result5['statusCode']}")
    print(f"CORS Origin: {result5['headers'].get('Access-Control-Allow-Origin')}")
    print(f"Response: {result5['body']}\n")

    print("=== CORS テスト完了 ===")
    print("\\n 使用方法:")
    print("1. app.enable_cors() でグローバル CORS 設定")
    print("2. @app.get('/', cors=True) でルートレベル デフォルト CORS")
    print("3. @app.get('/', cors=custom_config) でルートレベル カスタム CORS")
    print("4. OPTIONS リクエストは自動的に処理されます")
