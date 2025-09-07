# 基本 API の作成

lambapi を使って基本的な REST API を作成する方法を学びましょう。

## 🎯 このガイドで作るもの

ユーザー管理のシンプルな REST API：
- ユーザー一覧取得
- 特定ユーザー取得
- ユーザー作成
- ユーザー更新
- ユーザー削除

## 📋 前提条件

```bash
pip install lambapi
```

## 🚀 基本的な API

### 1. 最小限の API

```python
# app.py
from lambapi import API, create_lambda_handler

def create_app(event, context):
    app = API(event, context)
    
    @app.get("/")
    def hello():
        return {"message": "Hello, lambapi!"}
    
    return app

lambda_handler = create_lambda_handler(create_app)

# ローカルテスト用
if __name__ == "__main__":
    from lambapi import serve
    serve("app.py")
```

### 2. ユーザー管理 API（メモリ版）

```python
# app.py
from lambapi import API, Query, Path, Body, Response, create_lambda_handler
from lambapi.exceptions import NotFoundError, ValidationError
from pydantic import BaseModel, EmailStr
from typing import List, Optional

# データモデル定義
class User(BaseModel):
    id: int
    name: str
    email: EmailStr
    age: Optional[int] = None
    active: bool = True

class CreateUserRequest(BaseModel):
    name: str
    email: EmailStr
    age: Optional[int] = None

class UpdateUserRequest(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    age: Optional[int] = None
    active: Optional[bool] = None

def create_app(event, context):
    app = API(event, context)
    
    # インメモリストレージ（実際の実装では DB を使用）
    users = [
        User(id=1, name="Alice", email="alice@example.com", age=30),
        User(id=2, name="Bob", email="bob@example.com", age=25),
        User(id=3, name="Charlie", email="charlie@example.com", age=35),
    ]
    next_id = 4
    
    @app.get("/users")
    def list_users(
        limit: int = Query(10, ge=1, le=100, description="取得件数"),
        offset: int = Query(0, ge=0, description="オフセット"),
        active: Optional[bool] = Query(None, description="アクティブユーザーのみ")
    ):
        \"\"\"ユーザー一覧を取得\"\"\"
        filtered_users = users
        
        # アクティブフィルタ
        if active is not None:
            filtered_users = [u for u in filtered_users if u.active == active]
        
        # ページング
        paginated_users = filtered_users[offset:offset + limit]
        
        return {
            "users": [u.dict() for u in paginated_users],
            "total": len(filtered_users),
            "limit": limit,
            "offset": offset
        }
    
    @app.get("/users/{user_id}")
    def get_user(user_id: int = Path(..., ge=1, description="ユーザー ID")):
        \"\"\"特定のユーザーを取得\"\"\"
        user = next((u for u in users if u.id == user_id), None)
        if not user:
            raise NotFoundError(f"ユーザー ID {user_id} が見つかりません")
        
        return {"user": user.dict()}
    
    @app.post("/users")
    def create_user(user_data: CreateUserRequest = Body(..., description="ユーザー作成データ")):
        \"\"\"新しいユーザーを作成\"\"\"
        nonlocal next_id
        
        # メールアドレスの重複チェック
        if any(u.email == user_data.email for u in users):
            raise ValidationError(f"メールアドレス {user_data.email} は既に使用されています")
        
        # 新しいユーザーを作成
        new_user = User(
            id=next_id,
            name=user_data.name,
            email=user_data.email,
            age=user_data.age
        )
        users.append(new_user)
        next_id += 1
        
        return Response(
            {"message": "ユーザーを作成しました", "user": new_user.dict()},
            status_code=201
        )
    
    @app.put("/users/{user_id}")
    def update_user(
        user_id: int = Path(..., ge=1, description="ユーザー ID"),
        user_data: UpdateUserRequest = Body(..., description="更新データ")
    ):
        \"\"\"ユーザー情報を更新\"\"\"
        user = next((u for u in users if u.id == user_id), None)
        if not user:
            raise NotFoundError(f"ユーザー ID {user_id} が見つかりません")
        
        # フィールドを更新
        update_data = user_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(user, field, value)
        
        return {"message": "ユーザー情報を更新しました", "user": user.dict()}
    
    @app.delete("/users/{user_id}")
    def delete_user(user_id: int = Path(..., ge=1, description="ユーザー ID")):
        \"\"\"ユーザーを削除\"\"\"
        user_index = next((i for i, u in enumerate(users) if u.id == user_id), None)
        if user_index is None:
            raise NotFoundError(f"ユーザー ID {user_id} が見つかりません")
        
        deleted_user = users.pop(user_index)
        return {"message": f"ユーザー {deleted_user.name} を削除しました"}
    
    @app.get("/users/search")
    def search_users(
        q: str = Query(..., min_length=1, description="検索クエリ"),
        field: str = Query("name", regex="^(name|email)$", description="検索対象フィールド")
    ):
        \"\"\"ユーザー検索\"\"\"
        if field == "name":
            results = [u for u in users if q.lower() in u.name.lower()]
        else:  # email
            results = [u for u in users if q.lower() in u.email.lower()]
        
        return {
            "query": q,
            "field": field,
            "results": [u.dict() for u in results],
            "count": len(results)
        }
    
    return app

lambda_handler = create_lambda_handler(create_app)

# ローカル開発用
if __name__ == "__main__":
    from lambapi import serve
    serve("app.py", port=8000)
```

## 🧪 ローカルテスト

### サーバー起動

```bash
python app.py
# または
lambapi serve app.py
```

### API テスト

```bash
# ユーザー一覧取得
curl http://localhost:8000/users

# 特定ユーザー取得
curl http://localhost:8000/users/1

# ユーザー作成
curl -X POST http://localhost:8000/users \
  -H "Content-Type: application/json" \
  -d '{"name": "David", "email": "david@example.com", "age": 28}'

# ユーザー更新
curl -X PUT http://localhost:8000/users/1 \
  -H "Content-Type: application/json" \
  -d '{"age": 31}'

# ユーザー削除
curl -X DELETE http://localhost:8000/users/1

# ユーザー検索
curl "http://localhost:8000/users/search?q=Alice&field=name"

# ページング
curl "http://localhost:8000/users?limit=2&offset=1"

# フィルタリング
curl "http://localhost:8000/users?active=true"
```

## 📝 レスポンス例

### GET /users

```json
{
  "users": [
    {
      "id": 1,
      "name": "Alice",
      "email": "alice@example.com",
      "age": 30,
      "active": true
    },
    {
      "id": 2,
      "name": "Bob", 
      "email": "bob@example.com",
      "age": 25,
      "active": true
    }
  ],
  "total": 3,
  "limit": 10,
  "offset": 0
}
```

### POST /users

```json
{
  "message": "ユーザーを作成しました",
  "user": {
    "id": 4,
    "name": "David",
    "email": "david@example.com", 
    "age": 28,
    "active": true
  }
}
```

### エラーレスポンス

```json
{
  "error": "not_found",
  "message": "ユーザー ID 999 が見つかりません"
}
```

## 🔧 データベース統合版

実際のプロジェクトでは DynamoDB や RDS を使用します：

```python
from lambapi import API, Query, Path, Body, create_lambda_handler
import boto3

def create_app(event, context):
    app = API(event, context)
    
    # DynamoDB クライアント
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('users')
    
    @app.get("/users")
    def list_users(limit: int = Query(10, ge=1, le=100)):
        response = table.scan(Limit=limit)
        return {
            "users": response['Items'],
            "count": response['Count']
        }
    
    @app.get("/users/{user_id}")
    def get_user(user_id: str = Path(...)):
        response = table.get_item(Key={'id': user_id})
        if 'Item' not in response:
            raise NotFoundError("ユーザーが見つかりません")
        return {"user": response['Item']}
    
    @app.post("/users")
    def create_user(user_data: dict = Body(...)):
        table.put_item(Item=user_data)
        return {"message": "ユーザーを作成しました", "user": user_data}
    
    return app
```

## 🚀 デプロイ

### requirements.txt

```txt
lambapi[auth]==0.2.14
pydantic[email]==2.5.0
```

### SAM テンプレート

```yaml
# template.yaml
AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31

Resources:
  UserApiFunction:
    Type: AWS::Serverless::Function
    Properties:
      CodeUri: src/
      Handler: app.lambda_handler
      Runtime: python3.10
      Events:
        UserApi:
          Type: Api
          Properties:
            Path: /{proxy+}
            Method: ANY
      Environment:
        Variables:
          DYNAMODB_TABLE: !Ref UserTable
  
  UserTable:
    Type: AWS::DynamoDB::Table
    Properties:
      TableName: users
      AttributeDefinitions:
        - AttributeName: id
          AttributeType: S
      KeySchema:
        - AttributeName: id
          KeyType: HASH
      BillingMode: PAY_PER_REQUEST
```

### デプロイ実行

```bash
sam build
sam deploy --guided
```

## 📚 次のステップ

- [認証機能の追加](authentication.md) - ユーザー認証の実装
- [高度な使用例](advanced.md) - より複雑な API パターン
- [デプロイガイド](../guides/deployment.md) - 本番環境への展開

## 💡 ベストプラクティス

### 1. エラーハンドリング

```python
@app.error_handler(ValidationError)
def handle_validation_error(error):
    return {"error": "validation_error", "message": str(error)}, 400

@app.error_handler(NotFoundError)
def handle_not_found(error):
    return {"error": "not_found", "message": str(error)}, 404
```

### 2. ログ記録

```python
import logging

logger = logging.getLogger(__name__)

@app.post("/users")
def create_user(user_data: CreateUserRequest = Body(...)):
    logger.info(f"Creating user: {user_data.email}")
    # ... user creation logic
    logger.info(f"User created with ID: {new_user.id}")
    return Response(new_user.dict(), status_code=201)
```

### 3. バリデーション強化

```python
from pydantic import validator

class CreateUserRequest(BaseModel):
    name: str
    email: EmailStr
    age: Optional[int] = None
    
    @validator('name')
    def name_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError('名前は必須です')
        return v.strip()
    
    @validator('age')
    def age_must_be_positive(cls, v):
        if v is not None and v < 0:
            raise ValueError('年齢は0以上である必要があります')
        return v
```