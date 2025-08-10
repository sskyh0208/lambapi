# lambapi v0.2.x Examples

このディレクトリには lambapi v0.2.x の統合アノテーションシステムを使用した実例が含まれています。

## ファイル構成

### 1. `usage_example.py`
基本的な lambapi の使用方法を示すサンプルアプリケーション。

**機能:**
- ユーザー管理 API (GET, POST)
- パスパラメータとクエリパラメータの使用
- エラーハンドリング

**使用方法:**
```bash
# ライブラリインストール後
lambapi serve examples/usage_example

# または Python から直接
python examples/usage_example.py --serve
```

**テスト:**
```bash
curl http://localhost:8000/
curl http://localhost:8000/users
curl -X POST http://localhost:8000/users -H "Content-Type: application/json" -d '{"name":"Test User"}'
```

### 2. `example_app.py`
より実践的な CRUD API の例。

**機能:**
- 完全な CRUD 操作
- 多言語対応 (日本語/英語/スペイン語)
- 検索・フィルタリング
- バリデーション

**使用方法:**
```bash
lambapi serve examples/example_app
```

**テスト:**
```bash
curl http://localhost:8000/hello/世界?lang=ja
curl http://localhost:8000/users?search=Alice
curl -X PUT http://localhost:8000/users/1 -H "Content-Type: application/json" -d '{"name":"Updated Alice"}'
curl -X DELETE http://localhost:8000/users/1
```

### 3. `local_server.py`
standalone 版のローカル開発サーバー（参考用）。

**注意:** pip install lambapi 後は `lambapi serve` コマンドを使用することを推奨します。

## その他の例

### 最小構成の例（v0.2.x）

```python
# minimal.py
from lambapi import API, create_lambda_handler
from lambapi.annotations import Path, Query
from dataclasses import dataclass

@dataclass
class User:
    name: str
    email: str

def create_app(event, context):
    app = API(event, context)

    @app.get("/")
    def hello():
        return {"message": "Hello, lambapi v0.2.x!"}

    # 自動推論：User は自動的に Body として扱われる
    @app.post("/users")
    def create_user(user: User):
        return {"message": "Created", "user": user}

    # 自動推論：user_id は自動的に Path として扱われる
    @app.get("/users/{user_id}")
    def get_user(user_id: int):
        return {"user_id": user_id}

    return app

lambda_handler = create_lambda_handler(create_app)
```

### CORS 対応の例（v0.2.x）

```python
# cors_example.py
from lambapi import API, create_lambda_handler
from lambapi.annotations import Query, Header
from dataclasses import dataclass
from typing import Optional

@dataclass
class ApiRequest:
    data: str
    category: Optional[str] = None

def create_app(event, context):
    app = API(event, context)

    # グローバル CORS 設定
    app.enable_cors(
        origins=["https://example.com"],
        methods=["GET", "POST"],
        headers=["Content-Type", "Authorization"]
    )

    # アノテーション版：ヘッダーとクエリを明示的に処理
    @app.get("/api/data")
    def get_data(
        filter_type: str = Query(default="all"),
        authorization: Optional[str] = Header(alias="Authorization", default=None)
    ):
        return {
            "data": "This endpoint supports CORS",
            "filter": filter_type,
            "authenticated": authorization is not None
        }

    # 自動推論版：データクラスを Body として自動処理
    @app.post("/api/data")
    def create_data(request: ApiRequest):
        return {"message": "Data created", "data": request}

    return app

lambda_handler = create_lambda_handler(create_app)
```

### 高度なバリデーションの例（v0.2.x）

```python
# validation_example.py
from lambapi import API, Response, create_lambda_handler
from lambapi.annotations import Body, Path, Query
from lambapi.exceptions import ValidationError
from dataclasses import dataclass
from typing import Optional

# Pydantic を使った高度なバリデーション（オプション）
try:
    from pydantic import BaseModel, field_validator, EmailStr

    class PydanticUser(BaseModel):
        name: str
        email: EmailStr
        age: int

        @field_validator('age')
        @classmethod
        def validate_age(cls, v):
            if v < 0 or v > 150:
                raise ValueError('Age must be between 0 and 150')
            return v

        @field_validator('name')
        @classmethod
        def validate_name(cls, v):
            if len(v.strip()) == 0:
                raise ValueError('Name cannot be empty')
            return v.strip()
except ImportError:
    PydanticUser = None

# データクラス版（基本バリデーション）
@dataclass
class DataclassUser:
    name: str
    email: str
    age: int

def create_app(event, context):
    app = API(event, context)

    # データクラス版：手動バリデーション
    @app.post("/users/dataclass")
    def create_user_dataclass(user: DataclassUser = Body()):
        # カスタムバリデーション
        if not user.email or "@" not in user.email:
            raise ValidationError(
                "Valid email is required",
                field="email",
                value=user.email
            )

        if user.age < 0 or user.age > 150:
            raise ValidationError(
                "Age must be between 0 and 150",
                field="age",
                value=user.age
            )

        return Response({
            "message": "User created successfully",
            "user": {
                "name": user.name,
                "email": user.email,
                "age": user.age
            }
        }, status_code=201)

    # Pydantic 版：自動バリデーション（利用可能な場合）
    if PydanticUser:
        @app.post("/users/pydantic")
        def create_user_pydantic(user: PydanticUser):  # 自動推論で Body
            return Response({
                "message": "User created with Pydantic validation",
                "user": user.model_dump()
            }, status_code=201)

    # 混合アノテーション版
    @app.put("/users/{user_id}")
    def update_user(
        user_id: int = Path(),
        user: DataclassUser = Body(),
        version: str = Query(default="v1")
    ):
        # バリデーション済みデータを使用
        return {
            "message": f"User {user_id} updated",
            "user": user,
            "version": version
        }

    return app

lambda_handler = create_lambda_handler(create_app)
```

## 実行方法

1. **CLI コマンド使用**
   ```bash
   lambapi serve examples/usage_example
   lambapi serve examples/example_app --port 3000
   ```

2. **Python から直接**
   ```python
   from lambapi import serve
   serve('examples/usage_example')
   ```

3. **Lambda ハンドラーとして**
   ```python
   from examples.usage_example import lambda_handler

   # AWS Lambda でのテスト
   event = {'httpMethod': 'GET', 'path': '/', ...}
   context = {...}
   result = lambda_handler(event, context)
   ```

## デプロイ

これらの例は AWS Lambda にそのままデプロイできます：

```bash
# SAM でのデプロイ
cp examples/usage_example.py app.py
sam build
sam deploy --guided

# Serverless Framework でのデプロイ
cp examples/example_app.py handler.py
serverless deploy
```

## 学習の進め方

1. `usage_example.py` で基本概念を理解
2. `example_app.py` で実践的な機能を学習
3. 独自のアプリケーションを作成
4. 本番環境にデプロイ

各例には詳細なコメントが含まれているので、コードを読みながら lambapi の機能を学習できます。
