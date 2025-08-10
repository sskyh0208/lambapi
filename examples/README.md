# lambapi Examples

このディレクトリには lambapi の使用例が含まれています。

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

### 最小構成の例

```python
# minimal.py
from lambapi import API, create_lambda_handler

def create_app(event, context):
    app = API(event, context)

    @app.get("/")
    def hello():
        return {"message": "Hello, lambapi!"}

    return app

lambda_handler = create_lambda_handler(create_app)
```

### CORS 対応の例

```python
# cors_example.py
from lambapi import API, create_lambda_handler, create_cors_config

def create_app(event, context):
    app = API(event, context)

    # グローバル CORS 設定
    app.enable_cors(
        origins=["https://example.com"],
        methods=["GET", "POST"],
        headers=["Content-Type", "Authorization"]
    )

    @app.get("/api/data")
    def get_data():
        return {"data": "This endpoint supports CORS"}

    return app

lambda_handler = create_lambda_handler(create_app)
```

### 高度なバリデーションの例

```python
# validation_example.py
from lambapi import API, Response, create_lambda_handler
from lambapi.exceptions import ValidationError

def create_app(event, context):
    app = API(event, context)

    @app.post("/users")
    def create_user(request):
        data = request.json()

        # 詳細なバリデーション
        if not data.get("email") or "@" not in data["email"]:
            raise ValidationError(
                "Valid email is required",
                field="email",
                value=data.get("email")
            )

        if not data.get("age") or data["age"] < 0:
            raise ValidationError(
                "Age must be a positive number",
                field="age",
                value=data.get("age")
            )

        return Response({
            "message": "User created successfully",
            "user": data
        }, status_code=201)

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
