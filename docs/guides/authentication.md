# 認証システム

LambAPI では、DynamoDB を使用した JWT ベースの認証システムを提供します。この認証システムは、ユーザー管理、セッション管理、ロールベースアクセス制御をサポートしています。

## 概要

### 特徴

- **JWT トークン認証**: セキュアなトークンベース認証
- **DynamoDB バックエンド**: AWS サービスとの完全統合
- **軽量な BaseUser**: 頻繁なインスタンス化に最適化
- **カスタマイズ可能**: BaseUser を継承してカスタムユーザーモデルを作成
- **ロールベース認証**: 細かいアクセス制御をサポート
- **セッション管理**: DynamoDB を使用した永続セッション
- **パスワード暗号化**: bcrypt による安全なハッシュ化
- **カスタムトークン**: JWT ペイロードのフィールドを自由に設定可能

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
from lambapi import API, create_lambda_handler, Authenticated, Body
from lambapi.auth import BaseUser, DynamoDBAuth
from dataclasses import dataclass

@dataclass
class LoginRequest:
    id: str
    password: str

@dataclass
class SignupRequest:
    id: str
    password: str
    name: str = ""

def create_app(event, context):
    app = API(event, context)

    # 認証システムの初期化（secret_key が必須）
    auth = DynamoDBAuth(BaseUser, secret_key="your-secure-secret-key")
    # または環境変数を設定: export LAMBAPI_SECRET_KEY="your-secure-secret-key"
    # auth = DynamoDBAuth(BaseUser)  # 環境変数 LAMBAPI_SECRET_KEY から自動取得

    @app.post("/auth/signup")
    def signup(signup_data: SignupRequest = Body(...)):
        # BaseUser インスタンスを作成してサインアップ
        user = BaseUser()
        user.id = signup_data.id
        user.password = signup_data.password
        if signup_data.name:
            user.name = signup_data.name
        return auth.signup(user)

    @app.post("/auth/login")
    def login(login_data: LoginRequest = Body(...)):
        # BaseUser インスタンスを作成してログイン
        user = BaseUser()
        user.id = login_data.id
        return auth.login(user, login_data.password)

    @app.post("/auth/logout")
    def logout(request):
        return auth.logout(request)

    # 依存性注入による認証済みユーザー取得
    @app.get("/protected")
    def protected_endpoint(user: BaseUser = Authenticated(...)):
        return {"message": f"Hello, {user.id}!"}

    @app.get("/profile")
    def get_profile(user: BaseUser = Authenticated(...)):
        return {
            "id": user.id,
            "created_at": user.created_at.isoformat() if user.created_at else None
        }

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
        is_role_permission = True
        # JWT トークンに含めるフィールドをカスタマイズ
        token_include_fields = ["id", "name", "role", "department", "permissions"]

    def __init__(self, id=None, password=None, name="", email="", role="user", 
                 department="", permissions=None):
        # 必須フィールド
        self.id = id
        self.password = password
        
        # 自由にカスタムプロパティを追加
        self.name = name
        self.email = email
        self.role = role
        self.department = department
        self.permissions = permissions or []

# カスタムユーザーで認証システムを初期化（secret_key 必須）
auth = DynamoDBAuth(User, secret_key="your-secure-secret-key")

# 使用例
@app.post("/auth/signup")
def signup(signup_data: SignupRequest = Body(...)):
    user = User(
        id=signup_data.id,
        password=signup_data.password,
        name=signup_data.name,
        email=signup_data.email,
        role="user",
        department=signup_data.get("department", "general"),
        permissions=["read"]
    )
    return auth.signup(user)
```

### 3. パスワード検証

パスワードのバリデーションは BaseUser で行うことができます：

```python
from lambapi.auth import BaseUser

class CustomUser(BaseUser):
    class Meta(BaseUser.Meta):
        password_min_length = 12
        password_require_uppercase = True
        password_require_lowercase = True
        password_require_digit = True
        password_require_special = True

    def __init__(self, id=None, password=None):
        self.id = id
        self.password = password

# インスタンスメソッドでの検証
user = CustomUser()
try:
    user.validate_password("WeakPass")  # エラーが発生
except ValueError as e:
    print(f"パスワードエラー: {e}")

# クラスメソッドでの検証
try:
    CustomUser.validate_password("StrongPass123!")
    print("パスワードは有効です")
except ValueError as e:
    print(f"パスワードエラー: {e}")
```

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

### Authenticated 依存性注入

lambapi v0.2.1 以降では、依存性注入を使用して、より型安全で簡潔な認証処理が可能です：

```python
from lambapi import API, Authenticated, Query, Path

@app.get("/profile")
@auth.require_role("user")
def get_profile(
    user: CustomUser = Authenticated(..., description="認証されたユーザー")
):
    # user パラメータが自動的に注入される
    return {
        "user_id": user.id,
        "role": getattr(user, 'role', 'user'),
        "created_at": user.created_at.isoformat() if user.created_at else None
    }

@app.post("/admin/users/{target_user_id}")
@auth.require_role("admin")
def update_user_as_admin(
    # 複数の依存性注入を組み合わせ可能
    admin: CustomUser = Authenticated(..., description="管理者ユーザー"),
    target_user_id: str = Path(..., description="対象ユーザー ID"),
    new_role: str = Query(..., description="新しいロール")
):
    return {
        "message": f"管理者 {admin.id} がユーザー {target_user_id} のロールを {new_role} に変更しました"
    }
```

#### 従来方式との比較

```python
# 従来の方式（引き続きサポート）
@app.get("/profile")
@auth.require_role("user")  
def get_profile_legacy(user, request):
    return {"user_id": user.id}

# 新しい依存性注入方式
@app.get("/profile")
@auth.require_role("user")
def get_profile_modern(
    user: CustomUser = Authenticated(...)
):
    return {"user_id": user.id}
```

新しい方式の利点：
- **型安全性**: ユーザーオブジェクトの型が明確
- **IDE サポート**: 自動補完や型チェック
- **バリデーション**: パラメータの自動バリデーション
- **ドキュメント生成**: 自動 API 仕様書生成

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
        expiration = 3600                       # トークン有効期限（秒）
        
        # JWT トークンのカスタマイズ
        token_include_fields = ["id", "name", "role"]  # トークンに含めるフィールド
        # None の場合は全フィールド（password以外）を含める

        # 機能設定
        is_role_permission = True               # ロール権限を有効化
        enable_auth_logging = False             # 認証ログを有効化

        # パスワード要件
        password_min_length = 8                 # 最小文字数
        password_require_uppercase = False      # 大文字必須
        password_require_lowercase = False      # 小文字必須
        password_require_digit = True           # 数字必須
        password_require_special = False        # 特殊文字必須

        # タイムスタンプ
        auto_timestamps = True                  # 自動タイムスタンプ
```

### JWT トークンのカスタマイズ

JWT ペイロードに含めるフィールドを自由に設定できます：

```python
class User(BaseUser):
    class Meta(BaseUser.Meta):
        # 特定のフィールドのみトークンに含める
        token_include_fields = ["id", "role", "department", "team", "permissions"]

    def __init__(self, id=None, password=None, name="", email="", role="user", 
                 department="", team="", permissions=None, company="", location=""):
        # 必須フィールド
        self.id = id
        self.password = password
        
        # カスタムプロパティを自由に設定
        self.name = name
        self.email = email
        self.role = role
        self.department = department
        self.team = team
        self.permissions = permissions or []
        self.company = company
        self.location = location

# 使用例 - 自分の好きなプロパティを設定
user = User(
    id="user123",
    password="hashedpassword",
    name="山田太郎",
    email="yamada@example.com",
    role="admin",
    department="engineering",
    team="backend",
    permissions=["read", "write", "admin"],
    company="TechCorp",
    location="Tokyo"
)

# token_include_fields に指定されたフィールドのみがJWTに含まれる
payload = user.to_token_payload()
# {"id": "user123", "role": "admin", "department": "engineering", "team": "backend", "permissions": [...], "iat": ..., "exp": ...}
```

### JWT トークンのデコード

トークンからペイロードを取得：

```python
# クラスメソッドでのデコード
try:
    payload = BaseUser.decode_token_payload(token, secret_key)
    user_id = payload.get("id")
    role = payload.get("role")
except ValueError as e:
    print(f"トークンエラー: {e}")
```

## API リファレンス

### ユーザー登録

DynamoDBAuth.signup() メソッドは BaseUser オブジェクトを受け取り、BaseUser オブジェクトを返します：

```python
# signup メソッドの使用
user = BaseUser()
user.id = "user123"
user.password = "password123"
user.name = "User Name"

try:
    saved_user = auth.signup(user)
    print(f"ユーザー登録完了: {saved_user.id}")
except ValidationError as e:
    print(f"バリデーションエラー: {e}")
except ConflictError as e:
    print(f"重複エラー: {e}")
```

### ログイン

DynamoDBAuth.login() メソッドは BaseUser オブジェクトとパスワードを受け取り、JWT トークンを返します：

```python
# login メソッドの使用
user = BaseUser()
user.id = "user123"
password = "password123"

try:
    token = auth.login(user, password)
    print(f"ログイン成功。トークン: {token}")
except AuthenticationError as e:
    print(f"認証エラー: {e}")
except ValidationError as e:
    print(f"バリデーションエラー: {e}")
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

1. **環境変数を使用** (最重要):
   ```bash
   # 本番環境での推奨方法
   export LAMBAPI_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
   ```
   ```python
   # コード内では環境変数から自動取得
   auth = DynamoDBAuth()  # LAMBAPI_SECRET_KEY を自動使用
   ```

2. **明示的な secret_key 指定** (開発・テスト用):
   ```python
   # 開発環境やテストでの明示的指定
   auth = DynamoDBAuth(secret_key="development-key-do-not-use-in-production")
   ```

3. **強力な秘密鍵を生成**:
   ```bash
   # 安全なランダムキー生成
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

4. **秘密鍵の管理**:
   - **絶対にソースコードに含めない**
   - 環境変数または AWS Systems Manager Parameter Store を使用
   - 定期的にローテーションを実施

5. **HTTPS の使用**: 本番環境では必ず HTTPS を使用

6. **適切な権限設定**: DynamoDB IAM ロールの最小権限の原則

## トラブルシューティング

### よくあるエラー

#### ImportError: 認証依存関係がない

```python
# 解決方法
pip install lambapi[auth]
```

#### DynamoDB 接続エラー

```python
# ローカル開発用設定
class User(BaseUser):
    class Meta(BaseUser.Meta):
        endpoint_url = "http://localhost:8000"
```

#### JWT デコードエラー

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
from lambapi import API, create_lambda_handler, Authenticated, Body
from lambapi.auth import BaseUser, DynamoDBAuth
from lambapi.exceptions import AuthenticationError

class User(BaseUser):
    class Meta(BaseUser.Meta):
        table_name = os.getenv("DYNAMODB_TABLE", "users")
        expiration = 3600  # 1 時間
        is_role_permission = True
        enable_auth_logging = True
        token_include_fields = ["id", "name", "role"]  # カスタムトークン

    def __init__(self):
        pass

def create_app(event, context):
    app = API(event, context)

    # 認証システムの初期化
    auth = DynamoDBAuth(User)

    # サインアップエンドポイント
    @app.post("/auth/signup")
    def signup(signup_data: dict = Body(...)):
        user = User()
        user.id = signup_data["id"]
        user.password = signup_data["password"]
        user.name = signup_data.get("name", "")
        user.role = signup_data.get("role", "user")
        
        saved_user = auth.signup(user)
        return {"message": "ユーザー登録完了", "user_id": saved_user.id}

    # ログインエンドポイント
    @app.post("/auth/login")
    def login(login_data: dict = Body(...)):
        user = User()
        user.id = login_data["id"]
        
        token = auth.login(user, login_data["password"])
        return {"message": "ログイン成功", "token": token}

    # ログアウトエンドポイント
    @app.post("/auth/logout")
    def logout(request):
        result = auth.logout(request)
        return result

    # パブリックエンドポイント
    @app.get("/")
    def public_endpoint():
        return {"message": "Public access"}

    # 認証が必要なエンドポイント（依存性注入）
    @app.get("/profile")
    def get_profile(user: User = Authenticated(...)):
        return {"profile": user.to_dict()}

    # ロール制限エンドポイント
    @app.get("/admin/stats")
    @auth.require_role("admin")
    def admin_stats(user: User = Authenticated(...)):
        return {"stats": "admin only data", "user": user.id}

    # 手動認証チェック
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
from lambapi.auth import BaseUser, DynamoDBAuth

class TestAuth(unittest.TestCase):
    def setUp(self):
        self.auth = DynamoDBAuth(BaseUser, secret_key="test-secret")

    def test_user_signup(self):
        # ユーザー登録テスト
        user = BaseUser()
        user.id = "testuser"
        user.password = "password123"
        
        result = self.auth.signup(user)
        self.assertEqual(result.id, "testuser")
        
    def test_login(self):
        # ログインテスト
        # まずサインアップ
        user = BaseUser()
        user.id = "testuser2"
        user.password = "password123"
        self.auth.signup(user)
        
        # ログイン
        login_user = BaseUser()
        login_user.id = "testuser2"
        token = self.auth.login(login_user, "password123")
        
        self.assertIsInstance(token, str)
        self.assertTrue(len(token) > 0)
```

## 参考資料

- [JWT 公式サイト](https://jwt.io/)
- [DynamoDB 開発者ガイド](https://docs.aws.amazon.com/dynamodb/)
- [bcrypt ライブラリ](https://pypi.org/project/bcrypt/)
- [LambAPI API リファレンス](api/api.md)
