# 認証システム

LambAPI では、DynamoDB を使用した JWT ベースの認証システムを提供します。この認証システムは、ユーザー管理、セッション管理、ロールベースアクセス制御をサポートしています。

## 概要

### 特徴

- **JWT トークン認証**: セキュアなトークンベース認証
- **DynamoDB バックエンド**: AWS サービスとの完全統合
- **カスタマイズ可能**: BaseUser を継承してカスタムユーザーモデルを作成
- **ロールベース認証**: 細かいアクセス制御をサポート
- **セッション管理**: DynamoDB を使用した永続セッション
- **パスワード暗号化**: bcrypt による安全なハッシュ化

### アーキテクチャ

```mermaid
graph TD
    A[Client] --> B[API Endpoint]
    B --> C[DynamoDBAuth]
    C --> D[BaseUser/CustomUser]
    C --> E[DynamoDB]
    C --> F[JWT Token]
    F --> G[Session Storage]
```

## インストール

認証機能を使用するには、オプショナル依存関係をインストールします：

```bash
pip install lambapi[auth]
```

必要な依存関係：
- `boto3>=1.28.0` - DynamoDB 接続
- `PyJWT>=2.8.0` - JWT トークン処理
- `bcrypt>=4.0.0` - パスワードハッシュ化
- `cryptography>=41.0.0` - 暗号化サポート

## 基本的な使用方法

### 1. BaseUser の使用

最もシンプルな使用方法：

```python
from lambapi import API, create_lambda_handler
from lambapi.auth import BaseUser, DynamoDBAuth

def create_app(event, context):
    app = API(event, context)

    # 認証システムの初期化（BaseUser を使用）
    auth = DynamoDBAuth()

    @app.post("/auth/signup")
    def signup(request):
        return auth.signup(request)

    @app.post("/auth/login")
    def login(request):
        return auth.login(request)

    @app.post("/auth/logout")
    def logout(request):
        return auth.logout(request)

    @app.get("/protected")
    def protected_endpoint(request):
        user = auth.get_authenticated_user(request)
        return {"message": f"Hello, {user.id}!"}

    return app

lambda_handler = create_lambda_handler(create_app)
```

### 2. カスタムユーザーモデル

より複雑なユーザー情報が必要な場合：

```python
from lambapi.auth import BaseUser, DynamoDBAuth

class User(BaseUser):
    class Meta(BaseUser.Meta):
        table_name = "my_users"
        secret_key = "your-secret-key-here"  # 本番環境では環境変数を使用
        is_email_login = True
        is_role_permission = True

    def __init__(self, id, password, name="", email="", role="user"):
        super().__init__(id, password)
        self.name = name
        self.email = email
        self.role = role

# カスタムユーザーで認証システムを初期化
auth = DynamoDBAuth(User)
```

### 3. ルーターを使用した認証エンドポイント

認証エンドポイントを自動的に作成：

```python
from lambapi import API
from lambapi.auth import BaseUser, DynamoDBAuth, create_auth_router

def create_app(event, context):
    app = API(event, context)

    # 認証システムと関連ルーターを作成
    auth = DynamoDBAuth(User)
    auth_router = create_auth_router(auth)

    # 認証ルーターを登録
    app.include_router(auth_router)

    return app
```

これにより以下のエンドポイントが自動作成されます：
- `POST /auth/signup` - ユーザー登録
- `POST /auth/login` - ログイン
- `POST /auth/logout` - ログアウト
- `DELETE /auth/user/{user_id}` - ユーザー削除
- `PUT /auth/user/{user_id}/password` - パスワード更新

## ロールベースアクセス制御

### require_role デコレータ

特定のロールを持つユーザーのみにアクセスを制限：

```python
@app.get("/admin/users")
@auth.require_role("admin")
def admin_only(user, request):
    # user パラメータが自動注入される
    return {"message": f"Admin access granted to {user.id}"}

@app.get("/moderator/reports")
@auth.require_role(["admin", "moderator"])
def moderator_access(user, request):
    # 複数のロールを許可
    return {"reports": [...]}
```

### 手動認証チェック

より柔軟な認証制御：

```python
@app.get("/profile")
def get_profile(request):
    try:
        user = auth.get_authenticated_user(request)
        return {"profile": user.to_dict()}
    except AuthenticationError:
        return {"error": "Authentication required"}, 401
```

## 設定オプション

### Meta クラス設定

BaseUser の Meta クラスで動作をカスタマイズ：

```python
class User(BaseUser):
    class Meta(BaseUser.Meta):
        # DynamoDB 設定
        table_name = "users"                    # テーブル名
        endpoint_url = "http://localhost:8000"  # ローカル DynamoDB

        # JWT 設定
        secret_key = "your-secret-key"          # JWT 署名キー
        expiration = 3600                       # トークン有効期限（秒）

        # 機能設定
        is_email_login = True                   # メールログインを有効化
        is_role_permission = True               # ロール権限を有効化
        enable_auth_logging = False             # 認証ログを有効化

        # ID 設定
        id_type = "uuid"                        # UUID 自動生成

        # パスワード要件
        password_min_length = 8                 # 最小文字数
        password_require_uppercase = False      # 大文字必須
        password_require_lowercase = False      # 小文字必須
        password_require_digit = True           # 数字必須
        password_require_special = False        # 特殊文字必須

        # タイムスタンプ
        auto_timestamps = True                  # 自動タイムスタンプ
```

## API リファレンス

### ユーザー登録

```http
POST /auth/signup
Content-Type: application/json

{
  "id": "user123",
  "password": "password123",
  "email": "user@example.com",     // is_email_login=True の場合必須
  "name": "User Name",             // カスタムフィールド
  "role": "user"                   // is_role_permission=True の場合
}
```

**レスポンス例:**
```json
{
  "message": "ユーザー登録が完了しました",
  "user_id": "user123"
}
```

### ログイン

```http
POST /auth/login
Content-Type: application/json

{
  "id": "user123",                 // ID またはメールでログイン
  "password": "password123"
}
```

**レスポンス例:**
```json
{
  "message": "ログインしました",
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": "user123",
    "email": "user@example.com",
    "name": "User Name",
    "role": "user"
  }
}
```

### ログアウト

```http
POST /auth/logout
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**レスポンス例:**
```json
{
  "message": "ログアウトしました"
}
```

### 認証が必要なエンドポイント

```http
GET /protected-endpoint
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

## DynamoDB テーブル設計

### テーブル構造

```json
{
  "TableName": "users",
  "KeySchema": [
    {
      "AttributeName": "id",
      "KeyType": "HASH"
    }
  ],
  "AttributeDefinitions": [
    {
      "AttributeName": "id",
      "AttributeType": "S"
    },
    {
      "AttributeName": "email",
      "AttributeType": "S"
    }
  ],
  "GlobalSecondaryIndexes": [
    {
      "IndexName": "email-index",
      "KeySchema": [
        {
          "AttributeName": "email",
          "KeyType": "HASH"
        }
      ],
      "Projection": {
        "ProjectionType": "ALL"
      }
    }
  ]
}
```

### セッション管理

セッション情報は同じテーブルに TTL 付きで保存されます：

```json
{
  "id": "abc123def456",      // セッション ID（16 文字のハッシュ）
  "token": "eyJhbGc...",     // JWT トークン
  "user_id": "user123",      // ユーザー ID
  "exp": "2024-01-01T12:00:00Z",  // 有効期限
  "ttl": 1704110400          // DynamoDB TTL（自動削除）
}
```

## セキュリティ考慮事項

### パスワード保護

- **bcrypt ハッシュ化**: ソルト付きハッシュで保存
- **設定可能な要件**: 文字数、文字種別の制限
- **フォールバック**: bcrypt が利用できない場合は SHA-256（テスト用）

### トークンセキュリティ

- **JWT 署名**: HMAC-SHA256 で署名
- **有効期限**: 設定可能なトークン有効期限
- **セッション検証**: トークンと DynamoDB セッションの二重チェック

### 推奨事項

1. **環境変数を使用**:
   ```python
   import os

   class User(BaseUser):
       class Meta(BaseUser.Meta):
           secret_key = os.getenv("JWT_SECRET_KEY", "fallback-key")
   ```

2. **強力な秘密鍵を生成**:
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

3. **HTTPS の使用**: 本番環境では必ず HTTPS を使用

4. **適切な権限設定**: DynamoDB IAM ロールの最小権限の原則

## トラブルシューティング

### よくあるエラー

**ImportError: 認証依存関係がない**

```python
# 解決方法
pip install lambapi[auth]
```

**DynamoDB 接続エラー**

```python
# ローカル開発用設定
class User(BaseUser):
    class Meta(BaseUser.Meta):
        endpoint_url = "http://localhost:8000"
```

**JWT デコードエラー**

```python
# secret_key の一致を確認
# トークンの有効期限を確認
```

### ログの有効化

```python
class User(BaseUser):
    class Meta(BaseUser.Meta):
        enable_auth_logging = True

# ログ出力例
# Auth Event: {"event": "login_success", "timestamp": "2024-01-01T12:00:00", "user_id": "user123"}
```

## サンプルコード

### 完全な認証付き API

```python
import os
from lambapi import API, create_lambda_handler
from lambapi.auth import BaseUser, DynamoDBAuth, create_auth_router
from lambapi.exceptions import AuthenticationError

class User(BaseUser):
    class Meta(BaseUser.Meta):
        table_name = os.getenv("DYNAMODB_TABLE", "users")
        secret_key = os.getenv("JWT_SECRET", "dev-secret")
        expiration = 3600  # 1 時間
        is_email_login = True
        is_role_permission = True
        enable_auth_logging = True

    def __init__(self, id, password, name="", email="", role="user"):
        super().__init__(id, password)
        self.name = name
        self.email = email
        self.role = role

def create_app(event, context):
    app = API(event, context)

    # 認証システムの初期化
    auth = DynamoDBAuth(User)

    # 認証エンドポイントの追加
    auth_router = create_auth_router(auth)
    app.include_router(auth_router)

    # パブリックエンドポイント
    @app.get("/")
    def public_endpoint():
        return {"message": "Public access"}

    # 認証が必要なエンドポイント
    @app.get("/profile")
    def get_profile(request):
        user = auth.get_authenticated_user(request)
        return {"profile": user.to_dict()}

    # ロール制限エンドポイント
    @app.get("/admin/stats")
    @auth.require_role("admin")
    def admin_stats(user, request):
        return {"stats": "admin only data", "user": user.id}

    # カスタム認証チェック
    @app.put("/profile")
    def update_profile(request):
        try:
            user = auth.get_authenticated_user(request)
            data = request.json()

            # プロフィール更新ロジック
            user.update_attributes(name=data.get("name"))

            return {"message": "Profile updated"}
        except AuthenticationError:
            return {"error": "Authentication required"}, 401

    return app

lambda_handler = create_lambda_handler(create_app)
```

### テスト用コード

```python
import unittest
import json
from lambapi import Request
from lambapi.auth import BaseUser, DynamoDBAuth

class TestAuth(unittest.TestCase):
    def setUp(self):
        self.auth = DynamoDBAuth(BaseUser)

    def test_user_signup(self):
        # ユーザー登録テスト
        event = {
            "body": json.dumps({
                "id": "testuser",
                "password": "password123"
            })
        }
        request = Request(event)
        result = self.auth.signup(request)

        self.assertEqual(result["user_id"], "testuser")
        self.assertIn("message", result)
```

## 参考資料

- [JWT 公式サイト](https://jwt.io/)
- [DynamoDB 開発者ガイド](https://docs.aws.amazon.com/dynamodb/)
- [bcrypt ライブラリ](https://pypi.org/project/bcrypt/)
- [LambAPI API リファレンス](api/api.md)
