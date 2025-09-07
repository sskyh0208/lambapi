# 認証システム概要

lambapi の認証システムは DynamoDB + JWT + セッション管理による堅牢でスケーラブルなソリューションです。

## 🏗️ アーキテクチャ

```mermaid
graph TB
    Client[Client] --> API[API Endpoint]
    API --> Auth[DynamoDBAuth]
    Auth --> UserModel[User Model<br/>PynamoDB]
    Auth --> SessionModel[Session Model<br/>PynamoDB]
    Auth --> JWT[JWT Token]
    
    UserModel --> UserTable[(DynamoDB<br/>Users Table)]
    SessionModel --> SessionTable[(DynamoDB<br/>Sessions Table)]
    UserTable --> GSI[Email GSI]
```

## 🚀 特徴

- **JWT トークン認証**: セキュアなトークンベース認証
- **PynamoDB 統合**: 型安全な ORM 統合  
- **セッション管理**: 独立したセッションモデルによる永続管理
- **email ログイン**: GSI による高速メール検索（`is_email_login=True`で有効化）
- **ロールベース認証**: 細かいアクセス制御
- **パスワード暗号化**: bcrypt による安全なハッシュ化
- **カスタムトークン**: JWT ペイロードのフィールド自由設定

## 📦 インストール

```bash
# 認証機能込みでインストール
pip install lambapi[auth]

# 必要な依存関係
# - pynamodb>=5.4.0 - DynamoDB ORM
# - PyJWT>=2.8.0 - JWT トークン処理  
# - bcrypt>=4.0.0 - パスワードハッシュ化
# - cryptography>=41.0.0 - 暗号化サポート
```

## 🔧 基本セットアップ

### 1. PynamoDB モデル定義

```python
from pynamodb.models import Model
from pynamodb.attributes import (
    UnicodeAttribute, BooleanAttribute, UTCDateTimeAttribute, NumberAttribute
)
from pynamodb.indexes import GlobalSecondaryIndex, AllProjection

# Email 検索用の GSI
class EmailIndex(GlobalSecondaryIndex):
    class Meta:
        index_name = 'email-index'
        projection = AllProjection()
        read_capacity_units = 1
        write_capacity_units = 1
    
    email = UnicodeAttribute(hash_key=True)

# ユーザーモデル
class User(Model):
    class Meta:
        table_name = "users"
        region = "us-east-1"
    
    id = UnicodeAttribute(hash_key=True)
    password = UnicodeAttribute()
    email = UnicodeAttribute()
    email_index = EmailIndex()  # email ログイン用（is_email_login=True の場合に必須）
    name = UnicodeAttribute()
    role = UnicodeAttribute(default="user")
    is_active = BooleanAttribute(default=True)
    created_at = UTCDateTimeAttribute(null=True)

# セッションモデル  
class UserSession(Model):
    class Meta:
        table_name = "user_sessions"
        region = "us-east-1"
    
    id = UnicodeAttribute(hash_key=True)
    user_id = UnicodeAttribute()
    token = UnicodeAttribute()
    expires_at = NumberAttribute()  # Unix timestamp
    ttl = NumberAttribute()  # DynamoDB TTL
```

### 2. DynamoDBAuth 初期化

```python
from lambapi.auth import DynamoDBAuth

auth = DynamoDBAuth(
    user_model=User,
    session_model=UserSession,
    secret_key="your-secure-secret-key",
    expiration=3600,  # 1時間
    is_email_login=True,  # email ログインを有効化（auth.email_login()が使用可能になる）
    is_role_permission=True,
    token_include_fields=["id", "email", "name", "role", "is_active"],
    password_min_length=8,
    password_require_digit=True
)
```

### 3. 認証エンドポイント

```python
from lambapi import API, Body, Authenticated

@app.post("/auth/signup")
def signup(data: dict = Body(...)):
    user = User(
        id=data["email"],
        password=data["password"],
        email=data["email"],
        name=data["name"]
    )
    token = auth.signup(user)
    return {"token": token}

@app.post("/auth/login") 
def login(data: dict = Body(...)):
    # is_email_login=True の場合のみ使用可能
    token = auth.email_login(data["email"], data["password"])
    return {"token": token}

# ID ログインも利用可能（is_email_login の設定に関係なく使用可能）
@app.post("/auth/id-login")
def id_login(data: dict = Body(...)):
    token = auth.login(data["user_id"], data["password"])
    return {"token": token}

@app.post("/auth/logout")
def logout(user: User = Authenticated(...)):
    auth.logout(user)
    return {"message": "ログアウトしました"}

@app.get("/profile")
@auth.require_role("user")
def get_profile(user: User = Authenticated(...)):
    return {"profile": user.to_dict()}
```

## 🔐 認証フロー

### 1. ユーザー登録

```mermaid
sequenceDiagram
    Client->>API: POST /auth/signup
    API->>DynamoDBAuth: signup(user)
    DynamoDBAuth->>DynamoDB: Check existing user
    DynamoDBAuth->>DynamoDB: Save new user
    DynamoDBAuth->>DynamoDBAuth: Generate JWT
    DynamoDBAuth->>DynamoDB: Save session
    DynamoDBAuth->>API: Return token
    API->>Client: {"token": "..."}
```

### 2. ログイン

```mermaid
sequenceDiagram
    Client->>API: POST /auth/login
    API->>DynamoDBAuth: email_login(email, password)
    DynamoDBAuth->>DynamoDB: Query by email GSI
    DynamoDBAuth->>DynamoDBAuth: Verify password
    DynamoDBAuth->>DynamoDBAuth: Generate JWT
    DynamoDBAuth->>DynamoDB: Save session
    DynamoDBAuth->>API: Return token
    API->>Client: {"token": "..."}
```

### 3. 認証済みリクエスト

```mermaid
sequenceDiagram
    Client->>API: GET /profile (Authorization: Bearer token)
    API->>DynamoDBAuth: get_authenticated_user()
    DynamoDBAuth->>DynamoDBAuth: Decode JWT
    DynamoDBAuth->>DynamoDB: Verify session
    DynamoDBAuth->>API: Return user
    API->>Handler: user object
    Handler->>Client: Profile data
```

## 🛡️ セキュリティ機能

### パスワード保護

- **bcrypt ハッシュ化**: ソルト付きハッシュで保存
- **設定可能な要件**: 文字数、文字種別の制限
- **安全なデフォルト**: 最小8文字、数字必須

```python
auth = DynamoDBAuth(
    # ... other params
    password_min_length=8,
    password_require_uppercase=False,
    password_require_lowercase=False, 
    password_require_digit=True,
    password_require_special=False
)
```

### トークンセキュリティ

- **JWT 署名**: HMAC-SHA256 で署名
- **有効期限**: 設定可能なトークン有効期限
- **セッション検証**: JWT とセッション両方をチェック

### 推奨セキュリティ設定

```python
import os

auth = DynamoDBAuth(
    user_model=User,
    session_model=UserSession,
    secret_key=os.environ["JWT_SECRET_KEY"],  # 環境変数を使用
    expiration=3600,  # 短い有効期限
    password_min_length=12,  # より長いパスワード
    password_require_uppercase=True,
    password_require_lowercase=True,
    password_require_digit=True,
    password_require_special=True
)
```

## 📊 DynamoDB テーブル設計

### Users テーブル

```json
{
  "TableName": "users",
  "KeySchema": [
    {"AttributeName": "id", "KeyType": "HASH"}
  ],
  "AttributeDefinitions": [
    {"AttributeName": "id", "AttributeType": "S"},
    {"AttributeName": "email", "AttributeType": "S"}
  ],
  "GlobalSecondaryIndexes": [
    {
      "IndexName": "email-index",
      "KeySchema": [{"AttributeName": "email", "KeyType": "HASH"}],
      "Projection": {"ProjectionType": "ALL"}
    }
  ]
}
```

### Sessions テーブル

```json
{
  "TableName": "user_sessions",
  "KeySchema": [
    {"AttributeName": "id", "KeyType": "HASH"}
  ],
  "TimeToLiveSpecification": {
    "AttributeName": "ttl",
    "Enabled": true
  }
}
```

## 🔧 設定オプション

### DynamoDBAuth コンストラクタ

| パラメータ | 型 | 説明 |
|------------|-----|------|
| `user_model` | `Type[Model]` | **必須** PynamoDB ユーザーモデル |
| `session_model` | `Type[Model]` | **必須** PynamoDB セッションモデル |
| `secret_key` | `str` | **必須** JWT 署名用秘密鍵 |
| `expiration` | `int` | トークン有効期限（秒）デフォルト: 3600 |
| `is_email_login` | `bool` | email ログイン有効化（`auth.email_login()`が使用可能）デフォルト: False |
| `is_role_permission` | `bool` | ロール権限有効化 デフォルト: False |
| `token_include_fields` | `List[str]` | JWT に含めるフィールド |
| `password_min_length` | `int` | パスワード最小文字数 デフォルト: 8 |
| `password_require_uppercase` | `bool` | 大文字必須 デフォルト: False |
| `password_require_lowercase` | `bool` | 小文字必須 デフォルト: False |
| `password_require_digit` | `bool` | 数字必須 デフォルト: True |
| `password_require_special` | `bool` | 特殊文字必須 デフォルト: False |

## 🚨 エラー処理

### 認証エラー

```python
from lambapi.exceptions import AuthenticationError, AuthorizationError

try:
    token = auth.login("user@example.com", "wrong_password")
except AuthenticationError as e:
    return {"error": str(e)}, 401
```

### DynamoDBAuth 専用例外クラス

v0.2.15 以降、DynamoDBAuth は設定や用途に応じた専用例外クラスを提供します：

#### 設定エラー（AuthConfigError）

```python
from lambapi.exceptions import AuthConfigError

try:
    # 無効な設定でのDynamoDBAuth初期化
    auth = DynamoDBAuth(
        user_model=str,  # PynamoDBモデルではない
        session_model=UserSession,
        secret_key="secret"
    )
except AuthConfigError as e:
    print(f"設定エラー: {e.message}")
    print(f"設定タイプ: {e.details['config_type']}")  # "user_model"
```

#### パスワード要件エラー（PasswordValidationError）

```python
from lambapi.exceptions import PasswordValidationError

try:
    auth.validate_password("123")  # 短すぎるパスワード
except PasswordValidationError as e:
    print(f"パスワードエラー: {e.message}")
    print(f"要件タイプ: {e.details['requirement_type']}")  # "min_length"
```

#### モデル定義エラー（ModelValidationError）

```python
from lambapi.exceptions import ModelValidationError

try:
    # トークンにpasswordフィールドを含める（禁止）
    auth = DynamoDBAuth(
        user_model=User,
        session_model=UserSession,
        secret_key="secret",
        token_include_fields=["id", "password"]
    )
except ModelValidationError as e:
    print(f"モデルエラー: {e.message}")
    print(f"フィールド: {e.details['field_name']}")  # "password"
```

#### 機能無効エラー（FeatureDisabledError）

```python
from lambapi.exceptions import FeatureDisabledError

try:
    # emailログインが無効な状態で実行
    auth = DynamoDBAuth(user_model=User, session_model=UserSession, 
                       secret_key="secret", is_email_login=False)
    token = auth.email_login("user@example.com", "password")
except FeatureDisabledError as e:
    print(f"機能エラー: {e.message}")
    print(f"機能名: {e.details['feature_name']}")  # "email_login"
```

#### ロール権限不足エラー（RolePermissionError）

```python
from lambapi.exceptions import RolePermissionError

@app.post("/admin/settings")
@auth.require_role("admin")  
def update_settings(user: Authenticated, data: dict = Body(...)):
    # userロールでアクセスした場合、自動的にRolePermissionErrorが発生
    return {"message": "設定を更新しました"}

# エラーハンドリング
try:
    # 内部的にrequire_roleデコレータで実行
    pass
except RolePermissionError as e:
    print(f"権限エラー: {e.message}")
    print(f"ユーザーロール: {e.details['user_role']}")      # "user"
    print(f"必要なロール: {e.details['required_roles']}")   # ["admin"]
    print(f"リソース: {e.details['resource']}")            # "endpoint"
    print(f"アクション: {e.details['action']}")            # "access"
```

### エラー統合ハンドリング

```python
from lambapi.exceptions import (
    AuthConfigError, PasswordValidationError, 
    ModelValidationError, FeatureDisabledError, RolePermissionError,
    AuthenticationError, ValidationError
)

def handle_auth_setup():
    try:
        auth = DynamoDBAuth(
            user_model=User,
            session_model=UserSession,
            secret_key=os.environ["JWT_SECRET"],
            is_email_login=True,
            password_min_length=12,
            password_require_uppercase=True
        )
        return auth
        
    except AuthConfigError as e:
        # 設定エラー: 開発者向けエラー
        logger.error(f"認証設定エラー [{e.details.get('config_type')}]: {e.message}")
        raise
        
    except ModelValidationError as e:
        # モデルエラー: 開発者向けエラー
        logger.error(f"モデル定義エラー [{e.details.get('model_name')}]: {e.message}")
        raise

def signup_user(user_data):
    try:
        user = User(**user_data)
        token = auth.signup(user)
        return {"token": token}
        
    except PasswordValidationError as e:
        # パスワードエラー: ユーザー向けエラー
        return {
            "error": "パスワード要件違反",
            "message": e.message,
            "requirement": e.details.get('requirement_type'),
            "field": e.details.get('field')
        }, 400
        
    except ValidationError as e:
        # 一般バリデーションエラー
        return {"error": e.message}, 400
        
    except AuthenticationError as e:
        # 認証エラー
        return {"error": "認証に失敗しました"}, 401
```

### エラーレスポンス構造

すべての専用例外クラスは構造化されたレスポンスを提供します：

```python
{
    "error": "AUTH_CONFIG_ERROR",  # エラーコード
    "message": "user_model must be a PynamoDB Model",  # エラーメッセージ
    "status_code": 500,  # HTTPステータスコード
    "details": {  # 詳細情報
        "config_type": "user_model"
    }
}
```

## 📈 パフォーマンス最適化

### GSI の活用

```python
# email ログインは GSI を使用して高速検索
token = auth.email_login("user@example.com", "password")
# O(1) の時間計算量でユーザーを取得
```

### セッション管理

```python
# TTL により期限切れセッションは自動削除
# DynamoDB のネイティブ機能を活用
```

### Lambda Cold Start 対策

```python
# 関数外でのインスタンス作成
auth = DynamoDBAuth(...)  # Lambda コンテナで再利用

def lambda_handler(event, context):
    app = API(event, context)
    # auth インスタンスを再利用
    return app
```

## 🔧 次のステップ

- [DynamoDB 認証詳細](dynamodb.md) - 詳細な実装ガイド
- [認証付き API の例](../examples/authentication.md) - 実用的なサンプル
- [デプロイガイド](../guides/deployment.md) - AWS Lambda へのデプロイ