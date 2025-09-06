"""
統合ルーター実装例
複数のルーターを統合して管理する方法を示します。
"""

import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lambapi import API, Router, Response, create_lambda_handler


# ===== 個別のルーター定義 =====

# 認証ルーター
auth_router = Router()


@auth_router.post("/login")
def login(request):
    """ログイン"""
    credentials = request.json()

    if credentials.get("username") == "admin" and credentials.get("password") == "password":

        return {
            "token": "dummy-jwt-token",
            "expires_in": 3600,
            "user": {"id": "admin-user", "username": "admin", "role": "administrator"},
        }
    else:
        return Response({"error": "Invalid credentials"}, status_code=401)


@auth_router.post("/logout")
def logout(request):
    """ログアウト"""
    return {"message": "Successfully logged out"}


# パブリックルーター
public_router = Router()


@public_router.get("/health")
def health_check(request):
    """ヘルスチェック"""
    return {"status": "ok", "service": "lambapi"}


@public_router.get("/version")
def version_info(request):
    """バージョン情報"""
    return {"version": "1.0.0", "api": "lambapi"}


# 支払いルーター
payment_router = Router()


@payment_router.post("/charge")
def create_charge(request):
    """支払い処理"""
    payment_data = request.json()

    return {
        "charge_id": "charge_123",
        "amount": payment_data.get("amount", 0),
        "status": "succeeded",
    }


@payment_router.get("/history")
def payment_history(request):
    """支払い履歴"""
    return {
        "payments": [
            {"id": "pay_1", "amount": 1000, "status": "completed"},
            {"id": "pay_2", "amount": 2000, "status": "completed"},
        ]
    }


# 生成ルーター
generate_router = Router()


@generate_router.post("/text")
def generate_text(request):
    """テキスト生成"""
    request_data = request.json()

    return {
        "generated_text": f"Generated: {request_data.get('prompt', 'Hello')}",
        "model": "lambapi-v1",
    }


@generate_router.post("/image")
def generate_image(request):
    """画像生成"""
    request_data = request.json()

    return {
        "image_url": "https://example.com/generated-image.jpg",
        "prompt": request_data.get("prompt", "A beautiful landscape"),
    }


# ===== 統合ルーター =====

# メインルーターで全てを統合
main_router = Router()

# 各ルーターをプレフィックス付きで統合
main_router.add_router(auth_router, prefix="/auth", tags=["auth"])
main_router.add_router(public_router, prefix="/public", tags=["public"])
main_router.add_router(payment_router, prefix="/payment", tags=["payment"])
main_router.add_router(generate_router, prefix="/generate", tags=["generate"])


def create_app(event, context):
    """アプリケーション作成関数"""
    app = API(event, context)

    # CORS 設定のミドルウェア
    def cors_middleware(request, response):
        if isinstance(response, Response):
            response.headers.update(
                {
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                    "Access-Control-Allow-Headers": "Content-Type, Authorization",
                }
            )
        return response

    app.add_middleware(cors_middleware)

    # ルート直接定義
    @app.get("/")
    def root(request):
        return {"message": "Welcome to integrated router API"}

    # 統合されたルーターを登録
    app.add_router(main_router)

    return app


# Lambda 関数のエントリーポイント
lambda_handler = create_lambda_handler(create_app)


# ローカルテスト用コード
if __name__ == "__main__":
    # テストケース 1: ルート
    test_event_1 = {
        "httpMethod": "GET",
        "path": "/",
        "queryStringParameters": None,
        "headers": {"Content-Type": "application/json"},
        "body": None,
    }

    print("=== Test 1: Root ===")
    result1 = lambda_handler(test_event_1, None)
    print(json.dumps(result1, indent=2, ensure_ascii=False))

    # テストケース 2: 認証ログイン
    test_event_2 = {
        "httpMethod": "POST",
        "path": "/auth/login",
        "queryStringParameters": None,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"username": "admin", "password": "password"}),
    }

    print("\n=== Test 2: Auth Login ===")
    result2 = lambda_handler(test_event_2, None)
    print(json.dumps(result2, indent=2, ensure_ascii=False))

    # テストケース 3: パブリックヘルスチェック
    test_event_3 = {
        "httpMethod": "GET",
        "path": "/public/health",
        "queryStringParameters": None,
        "headers": {},
        "body": None,
    }

    print("\n=== Test 3: Public Health ===")
    result3 = lambda_handler(test_event_3, None)
    print(json.dumps(result3, indent=2, ensure_ascii=False))

    # テストケース 4: 支払い処理
    test_event_4 = {
        "httpMethod": "POST",
        "path": "/payment/charge",
        "queryStringParameters": None,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"amount": 5000, "currency": "jpy"}),
    }

    print("\n=== Test 4: Payment Charge ===")
    result4 = lambda_handler(test_event_4, None)
    print(json.dumps(result4, indent=2, ensure_ascii=False))

    # テストケース 5: テキスト生成
    test_event_5 = {
        "httpMethod": "POST",
        "path": "/generate/text",
        "queryStringParameters": None,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"prompt": "Write a story about AI"}),
    }

    print("\n=== Test 5: Generate Text ===")
    result5 = lambda_handler(test_event_5, None)
    print(json.dumps(result5, indent=2, ensure_ascii=False))
