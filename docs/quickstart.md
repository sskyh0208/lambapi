# クイックスタート

5分で lambapi を始めましょう。

## 🚀 インストール

```bash
pip install lambapi[auth]  # 認証機能込み
# または
pip install lambapi       # コア機能のみ
```

## 📝 最初の API

### 1. 基本的な API

```python
from lambapi import API, create_lambda_handler

def create_app(event, context):
    app = API(event, context)
    
    @app.get("/")
    def hello():
        return {"message": "Hello, lambapi!"}
    
    @app.get("/users/{user_id}")
    def get_user(user_id: str):
        return {"user_id": user_id}
    
    return app

# Lambda エントリーポイント
lambda_handler = create_lambda_handler(create_app)
```

### 2. 依存性注入を使った API

```python
from lambapi import API, Query, Path, Body, create_lambda_handler
from pydantic import BaseModel

class CreateUserRequest(BaseModel):
    name: str
    email: str

def create_app(event, context):
    app = API(event, context)
    
    @app.get("/search")
    def search(
        q: str = Query(..., description="検索クエリ"),
        limit: int = Query(10, ge=1, le=100)
    ):
        return {"query": q, "limit": limit}
    
    @app.post("/users")
    def create_user(data: CreateUserRequest = Body(...)):
        return {"message": f"ユーザー {data.name} を作成しました"}
    
    return app

lambda_handler = create_lambda_handler(create_app)
```

### 3. 認証付き API

```python
from lambapi import API, Authenticated, create_lambda_handler
from lambapi.auth import DynamoDBAuth
from pynamodb.models import Model
from pynamodb.attributes import UnicodeAttribute, BooleanAttribute
from pynamodb.indexes import GlobalSecondaryIndex, AllProjection

# メールインデックス定義
class EmailIndex(GlobalSecondaryIndex):
    class Meta:
        index_name = 'email-index'
        projection = AllProjection()
    email = UnicodeAttribute(hash_key=True)

# ユーザーモデル定義
class User(Model):
    class Meta:
        table_name = "users"
        region = "us-east-1"
    
    id = UnicodeAttribute(hash_key=True)
    password = UnicodeAttribute()
    email = UnicodeAttribute()
    email_index = EmailIndex()
    name = UnicodeAttribute()
    role = UnicodeAttribute(default="user")
    is_active = BooleanAttribute(default=True)

# セッションモデル定義
class UserSession(Model):
    class Meta:
        table_name = "user_sessions"
        region = "us-east-1"
    
    id = UnicodeAttribute(hash_key=True)
    user_id = UnicodeAttribute()
    token = UnicodeAttribute()
    expires_at = UnicodeAttribute()
    ttl = UnicodeAttribute()

def create_app(event, context):
    app = API(event, context)
    
    # 認証システム初期化
    auth = DynamoDBAuth(
        user_model=User,
        session_model=UserSession,
        secret_key="your-secret-key",
        is_email_login=True,
        is_role_permission=True
    )
    
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
        token = auth.email_login(data["email"], data["password"])
        return {"token": token}
    
    @app.get("/profile")
    @auth.require_role("user")
    def get_profile(user: User = Authenticated(...)):
        return {
            "id": user.id,
            "name": user.name,
            "email": user.email
        }
    
    return app

lambda_handler = create_lambda_handler(create_app)
```

## 🔧 ローカル開発

```bash
# 開発サーバー起動
lambapi serve app.py

# カスタムポート指定
lambapi serve app.py --port 8080
```

## 📦 デプロイ

### AWS Lambda 用パッケージング

```bash
# 依存関係をインストール
pip install -r requirements.txt -t ./package

# コードをパッケージに追加
cp app.py ./package/

# ZIP ファイル作成
cd package && zip -r ../deployment.zip . && cd ..
```

### SAM テンプレート例

```yaml
# template.yaml
AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31

Resources:
  LambapiFunction:
    Type: AWS::Serverless::Function
    Properties:
      CodeUri: package/
      Handler: app.lambda_handler
      Runtime: python3.10
      Events:
        Api:
          Type: Api
          Properties:
            Path: /{proxy+}
            Method: ANY
```

```bash
# デプロイ
sam build && sam deploy --guided
```

## 🎯 次のステップ

- [API クラス詳細](core/api.md) - フレームワークの詳細機能
- [認証システム](auth/overview.md) - セキュリティ機能の詳細
- [サンプル集](examples/) - より多くの実用例

## 📚 主要機能

| 機能 | 説明 |
|------|------|
| **依存性注入** | FastAPI 風の型安全なパラメータ処理 |
| **認証** | DynamoDB + JWT によるセキュアな認証 |
| **バリデーション** | Pydantic モデルによる自動データ検証 |
| **ルーティング** | 直感的な URL パターンマッチング |
| **CORS** | クロスオリジン要求の柔軟な制御 |
| **エラーハンドリング** | 統一されたエラー処理システム |