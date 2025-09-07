# 認証付き API の作成

DynamoDB と JWT を使用したセキュアな認証システムを構築する方法を学びましょう。

## 🎯 このガイドで作るもの

- ユーザー登録・ログイン機能
- JWT トークン認証
- ロールベースアクセス制御
- セッション管理
- プロフィール管理 API

## 📦 セットアップ

### 依存関係のインストール

```bash
pip install lambapi[auth] pydantic[email]
```

### 環境変数設定

```bash
export JWT_SECRET_KEY="your-super-secret-key-change-in-production"
export AWS_REGION="us-east-1"
```

## 🏗️ モデル定義

### PynamoDB モデル

```python
# models.py
from pynamodb.models import Model
from pynamodb.attributes import (
    UnicodeAttribute, BooleanAttribute, UTCDateTimeAttribute, NumberAttribute
)
from pynamodb.indexes import GlobalSecondaryIndex, AllProjection
import os

# Email 検索用の GSI
class EmailIndex(GlobalSecondaryIndex):
    \"\"\"メールアドレスでの検索用 GSI\"\"\"
    class Meta:
        index_name = 'email-index'
        projection = AllProjection()
        read_capacity_units = 1
        write_capacity_units = 1
    
    email = UnicodeAttribute(hash_key=True)

# ユーザーモデル
class User(Model):
    \"\"\"ユーザー情報を管理するモデル\"\"\"
    class Meta:
        table_name = "auth_users"
        region = os.getenv("AWS_REGION", "us-east-1")
        # ローカル開発時は DynamoDB Local を使用
        if os.getenv("DYNAMODB_ENDPOINT"):
            host = os.getenv("DYNAMODB_ENDPOINT")
    
    id = UnicodeAttribute(hash_key=True)  # ユーザー ID（email を使用）
    password = UnicodeAttribute()  # ハッシュ化されたパスワード
    email = UnicodeAttribute()  # メールアドレス
    email_index = EmailIndex()  # メール検索用 GSI
    name = UnicodeAttribute()  # フルネーム
    role = UnicodeAttribute(default="user")  # ユーザーロール
    is_active = BooleanAttribute(default=True)  # アクティブ状態
    is_verified = BooleanAttribute(default=False)  # メール認証状態
    created_at = UTCDateTimeAttribute(null=True)  # 作成日時

# セッションモデル
class UserSession(Model):
    \"\"\"ユーザーセッション管理モデル\"\"\"
    class Meta:
        table_name = "auth_sessions"
        region = os.getenv("AWS_REGION", "us-east-1")
        if os.getenv("DYNAMODB_ENDPOINT"):
            host = os.getenv("DYNAMODB_ENDPOINT")
    
    id = UnicodeAttribute(hash_key=True)  # セッション ID
    user_id = UnicodeAttribute()  # ユーザー ID
    token = UnicodeAttribute()  # JWT トークン
    expires_at = NumberAttribute()  # 有効期限（Unix timestamp）
    ttl = NumberAttribute()  # DynamoDB TTL（自動削除用）
```

### Pydantic モデル

```python
# schemas.py
from pydantic import BaseModel, EmailStr, Field
from typing import Optional

class SignupRequest(BaseModel):
    \"\"\"ユーザー登録リクエスト\"\"\"
    name: str = Field(..., min_length=1, max_length=100, description="フルネーム")
    email: EmailStr = Field(..., description="メールアドレス")
    password: str = Field(..., min_length=8, description="パスワード（8文字以上）")

class LoginRequest(BaseModel):
    \"\"\"ログインリクエスト\"\"\"
    email: EmailStr = Field(..., description="メールアドレス")
    password: str = Field(..., description="パスワード")

class UpdateProfileRequest(BaseModel):
    \"\"\"プロフィール更新リクエスト\"\"\"
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    
class ChangePasswordRequest(BaseModel):
    \"\"\"パスワード変更リクエスト\"\"\"
    current_password: str = Field(..., description="現在のパスワード")
    new_password: str = Field(..., min_length=8, description="新しいパスワード")
```

## 🔐 認証システム

### メインアプリケーション

```python
# app.py
import os
from lambapi import API, Body, Authenticated, create_lambda_handler
from lambapi.auth import DynamoDBAuth
from lambapi.exceptions import ValidationError, AuthenticationError
from models import User, UserSession
from schemas import SignupRequest, LoginRequest, UpdateProfileRequest, ChangePasswordRequest

def create_app(event, context):
    app = API(event, context)
    
    # 認証システムの初期化
    auth = DynamoDBAuth(
        user_model=User,
        session_model=UserSession,
        secret_key=os.getenv("JWT_SECRET_KEY", "dev-secret-key"),
        expiration=3600,  # 1時間
        is_email_login=True,  # email ログイン有効化
        is_role_permission=True,  # ロール権限有効化
        token_include_fields=["id", "email", "name", "role", "is_active", "is_verified"],
        
        # パスワード要件
        password_min_length=8,
        password_require_uppercase=False,
        password_require_lowercase=False,
        password_require_digit=True,
        password_require_special=False
    )
    
    # ===== 認証エンドポイント =====
    
    @app.post("/auth/signup")
    def signup(data: SignupRequest = Body(..., description="ユーザー登録データ")):
        \"\"\"ユーザー登録\"\"\"
        try:
            # User モデルインスタンスを作成
            user = User(
                id=data.email,  # ID として email を使用
                password=data.password,  # auth.signup() で自動ハッシュ化される
                email=data.email,
                name=data.name,
                role="user",
                is_active=True,
                is_verified=False
            )
            
            # ユーザー登録とトークン生成
            token = auth.signup(user)
            
            return {
                "message": "ユーザー登録が完了しました",
                "token": token,
                "user": {
                    "id": user.id,
                    "name": user.name,
                    "email": user.email,
                    "role": user.role
                }
            }
            
        except ValidationError as e:
            raise ValidationError(f"登録エラー: {str(e)}")
        except Exception as e:
            raise ValidationError(f"登録に失敗しました: {str(e)}")
    
    @app.post("/auth/login")
    def login(data: LoginRequest = Body(..., description="ログイン情報")):
        \"\"\"ログイン\"\"\"
        try:
            # email ログイン
            token = auth.email_login(data.email, data.password)
            
            return {
                "message": "ログインしました",
                "token": token
            }
            
        except AuthenticationError as e:
            raise AuthenticationError("メールアドレスまたはパスワードが正しくありません")
    
    @app.post("/auth/logout")
    def logout(user: User = Authenticated(..., description="認証されたユーザー")):
        \"\"\"ログアウト\"\"\"
        auth.logout(user)
        return {"message": "ログアウトしました"}
    
    # ===== ユーザープロフィール =====
    
    @app.get("/profile")
    @auth.require_role("user")  # user ロールが必要
    def get_profile(user: User = Authenticated(...)):
        \"\"\"プロフィール取得\"\"\"
        return {
            "profile": {
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "role": user.role,
                "is_active": user.is_active,
                "is_verified": user.is_verified,
                "created_at": user.created_at.isoformat() if user.created_at else None
            }
        }
    
    @app.put("/profile")
    @auth.require_role("user")
    def update_profile(
        data: UpdateProfileRequest = Body(...),
        user: User = Authenticated(...)
    ):
        \"\"\"プロフィール更新\"\"\"
        if data.name is not None:
            user.name = data.name
            user.save()
        
        return {
            "message": "プロフィールを更新しました",
            "profile": {
                "id": user.id,
                "name": user.name,
                "email": user.email
            }
        }
    
    @app.post("/auth/change-password")
    @auth.require_role("user")
    def change_password(
        data: ChangePasswordRequest = Body(...),
        user: User = Authenticated(...)
    ):
        \"\"\"パスワード変更\"\"\"
        # 現在のパスワードを確認
        if not auth._verify_password_hash(user.password, data.current_password):
            raise AuthenticationError("現在のパスワードが正しくありません")
        
        # 新しいパスワードをハッシュ化して保存
        new_hashed_password = auth._hash_password(data.new_password)
        user.password = new_hashed_password
        user.save()
        
        return {"message": "パスワードを変更しました"}
    
    # ===== 管理者機能 =====
    
    @app.get("/admin/users")
    @auth.require_role("admin")  # admin ロールが必要
    def list_all_users(admin: User = Authenticated(...)):
        \"\"\"全ユーザー一覧（管理者のみ）\"\"\"
        # 実際の実装では scan を使用（本番環境では要注意）
        users = []
        for user in User.scan():
            users.append({
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "role": user.role,
                "is_active": user.is_active,
                "created_at": user.created_at.isoformat() if user.created_at else None
            })
        
        return {
            "users": users,
            "count": len(users),
            "admin": admin.id
        }
    
    @app.put("/admin/users/{user_id}/role")
    @auth.require_role("admin")
    def update_user_role(
        user_id: str,
        new_role: str = Body(..., embed=True, regex="^(user|admin|moderator)$"),
        admin: User = Authenticated(...)
    ):
        \"\"\"ユーザーロール変更（管理者のみ）\"\"\"
        try:
            target_user = User.get(user_id)
            old_role = target_user.role
            target_user.role = new_role
            target_user.save()
            
            return {
                "message": f"ユーザー {target_user.name} のロールを {old_role} から {new_role} に変更しました",
                "admin": admin.id,
                "target_user": target_user.id
            }
        except User.DoesNotExist:
            raise NotFoundError("指定されたユーザーが見つかりません")
    
    # ===== モデレーター機能 =====
    
    @app.get("/moderator/reports")
    @auth.require_role(["admin", "moderator"])  # 複数ロール許可
    def get_reports(user: User = Authenticated(...)):
        \"\"\"レポート取得（管理者・モデレーター）\"\"\"
        return {
            "reports": [],  # 実際の実装では DB から取得
            "moderator": user.id,
            "role": user.role
        }
    
    return app

lambda_handler = create_lambda_handler(create_app)

# ローカル開発用
if __name__ == "__main__":
    from lambapi import serve
    serve("app.py", port=8000)
```

## 🧪 テスト例

### ユーザー登録

```bash
curl -X POST http://localhost:8000/auth/signup \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Alice Johnson",
    "email": "alice@example.com", 
    "password": "password123"
  }'
```

### ログイン

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "alice@example.com",
    "password": "password123"
  }'
```

### 認証が必要な API の呼び出し

```bash
# トークンを環境変数に保存
TOKEN="eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."

# プロフィール取得
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/profile

# プロフィール更新
curl -X PUT http://localhost:8000/profile \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Alice Smith"}'

# パスワード変更
curl -X POST http://localhost:8000/auth/change-password \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "current_password": "password123",
    "new_password": "newpassword456"
  }'
```

### 管理者機能

```bash
# 管理者でログイン
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "password": "adminpass123"
  }'

ADMIN_TOKEN="..."

# 全ユーザー取得
curl -H "Authorization: Bearer $ADMIN_TOKEN" \
  http://localhost:8000/admin/users

# ユーザーロール変更
curl -X PUT http://localhost:8000/admin/users/alice@example.com/role \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '"moderator"'
```

## 🔒 セキュリティ強化

### 1. 環境変数での設定

```python
# config.py
import os
from datetime import timedelta

class Config:
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
    if not JWT_SECRET_KEY:
        raise ValueError("JWT_SECRET_KEY environment variable is required")
    
    JWT_EXPIRATION = int(os.getenv("JWT_EXPIRATION", 3600))
    
    # パスワード要件
    PASSWORD_MIN_LENGTH = int(os.getenv("PASSWORD_MIN_LENGTH", 8))
    PASSWORD_REQUIRE_UPPERCASE = os.getenv("PASSWORD_REQUIRE_UPPERCASE", "false").lower() == "true"
    PASSWORD_REQUIRE_DIGIT = os.getenv("PASSWORD_REQUIRE_DIGIT", "true").lower() == "true"
    PASSWORD_REQUIRE_SPECIAL = os.getenv("PASSWORD_REQUIRE_SPECIAL", "false").lower() == "true"
```

### 2. より強固なパスワード要件

```python
auth = DynamoDBAuth(
    # ... other params
    password_min_length=12,
    password_require_uppercase=True,
    password_require_lowercase=True,
    password_require_digit=True,
    password_require_special=True
)
```

### 3. レート制限

```python
from lambapi.exceptions import RateLimitError
import time

# シンプルなレート制限（メモリベース）
login_attempts = {}

@app.post("/auth/login")
def login(data: LoginRequest = Body(...)):
    # IP アドレス取得
    client_ip = app.request.headers.get("x-forwarded-for", "unknown")
    
    # レート制限チェック
    now = time.time()
    attempts = login_attempts.get(client_ip, [])
    
    # 過去1分間の試行回数をカウント
    recent_attempts = [t for t in attempts if now - t < 60]
    if len(recent_attempts) >= 5:
        raise RateLimitError("ログイン試行回数が上限に達しました")
    
    try:
        token = auth.email_login(data.email, data.password)
        # 成功時は記録をクリア
        login_attempts.pop(client_ip, None)
        return {"token": token}
    except AuthenticationError:
        # 失敗時は記録を追加
        login_attempts[client_ip] = recent_attempts + [now]
        raise
```

## 🚀 デプロイ設定

### SAM テンプレート

```yaml
# template.yaml
AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31

Parameters:
  JwtSecretKey:
    Type: String
    NoEcho: true
    Description: JWT Secret Key

Resources:
  AuthApiFunction:
    Type: AWS::Serverless::Function
    Properties:
      CodeUri: src/
      Handler: app.lambda_handler
      Runtime: python3.10
      Environment:
        Variables:
          JWT_SECRET_KEY: !Ref JwtSecretKey
          AWS_REGION: !Ref AWS::Region
      Policies:
        - DynamoDBCrudPolicy:
            TableName: !Ref UsersTable
        - DynamoDBCrudPolicy:
            TableName: !Ref SessionsTable
      Events:
        AuthApi:
          Type: Api
          Properties:
            Path: /{proxy+}
            Method: ANY

  UsersTable:
    Type: AWS::DynamoDB::Table
    Properties:
      TableName: auth_users
      AttributeDefinitions:
        - AttributeName: id
          AttributeType: S
        - AttributeName: email
          AttributeType: S
      KeySchema:
        - AttributeName: id
          KeyType: HASH
      GlobalSecondaryIndexes:
        - IndexName: email-index
          KeySchema:
            - AttributeName: email
              KeyType: HASH
          Projection:
            ProjectionType: ALL
          BillingMode: PAY_PER_REQUEST
      BillingMode: PAY_PER_REQUEST

  SessionsTable:
    Type: AWS::DynamoDB::Table
    Properties:
      TableName: auth_sessions
      AttributeDefinitions:
        - AttributeName: id
          AttributeType: S
      KeySchema:
        - AttributeName: id
          KeyType: HASH
      TimeToLiveSpecification:
        AttributeName: ttl
        Enabled: true
      BillingMode: PAY_PER_REQUEST
```

### デプロイコマンド

```bash
# パラメータファイル作成
echo 'JwtSecretKey=$(python -c "import secrets; print(secrets.token_urlsafe(32))")' > .env

# デプロイ
sam build
sam deploy --guided --parameter-overrides JwtSecretKey="$(cat .env | cut -d= -f2)"
```

## 📚 次のステップ

- [高度な使用例](advanced.md) - より複雑な認証パターン  
- [デプロイガイド](../guides/deployment.md) - 本番環境でのベストプラクティス
- [CORS 設定](../guides/cors.md) - フロントエンドとの統合