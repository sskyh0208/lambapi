# lambapi

モダンな AWS Lambda 用 API フレームワーク

## 概要

lambapi は、AWS Lambda で直感的でモダンな API を構築できる軽量フレームワークです。パスパラメータとクエリパラメータの自動注入、型変換、デフォルト値サポートなど、モダンな Web API 開発の機能を提供します。
ドキュメントは [https://sskyh0208.github.io/lambapi/](https://sskyh0208.github.io/lambapi/) で公開されています。

## 特徴

- 🚀 **直感的な記法**: デコレータベースのルート定義
- 📋 **自動パラメータ注入**: パスパラメータとクエリパラメータを関数引数として直接受け取り
- 🔄 **型自動変換**: `int`, `float`, `bool`, `str` の自動型変換
- 🎯 **デフォルト値サポート**: クエリパラメータのデフォルト値設定
- 🔧 **ミドルウェア対応**: CORS など、カスタムミドルウェアの追加
- 📦 **軽量**: 標準ライブラリのみを使用、外部依存なし
- 🔒 **型安全**: 型ヒント完全対応

## インストール

```bash
pip install lambapi
```

## クイックスタート

### 基本的な使用例

```python
from lambapi import API, Response, create_lambda_handler

def create_app(event, context):
    app = API(event, context)
    
    @app.get("/")
    def hello():
        return {"message": "Hello, lambapi!"}
    
    @app.get("/users/{user_id}")
    def get_user(user_id: str):
        return {"user_id": user_id, "name": f"User {user_id}"}
    
    @app.get("/search")
    def search(q: str = "", limit: int = 10):
        return {"query": q, "limit": limit, "results": []}
    
    return app

lambda_handler = create_lambda_handler(create_app)
```

### パスパラメータ + クエリパラメータ

```python
@app.get("/users/{user_id}/posts")
def get_user_posts(user_id: str, limit: int = 10, sort: str = "created_at"):
    return {
        "user_id": user_id,
        "limit": limit,
        "sort": sort,
        "posts": [f"post-{i}" for i in range(1, limit + 1)]
    }
```

### POST リクエストの処理

```python
@app.post("/users")
def create_user(request):
    user_data = request.json()
    return Response(
        {"message": "User created", "user": user_data},
        status_code=201
    )
```

### 型変換とデフォルト値

```python
@app.get("/items")
def get_items(limit: int = 10, offset: int = 0, active: bool = True):
    # limit と offset は自動的に int に変換
    # active は自動的に bool に変換（'true', '1', 'yes', 'on' → True）
    return {
        "limit": limit,       # int 型
        "offset": offset,     # int 型  
        "active": active      # bool 型
    }
```

## API リファレンス

### API クラス

メインの API クラスです。

```python
app = API(event, context)
```

### デコレータ

- `@app.get(path)` - GET リクエスト
- `@app.post(path)` - POST リクエスト  
- `@app.put(path)` - PUT リクエスト
- `@app.delete(path)` - DELETE リクエスト
- `@app.patch(path)` - PATCH リクエスト

### Request オブジェクト

従来の方式でリクエスト情報にアクセスする場合：

```python
@app.get("/legacy")
def legacy_handler(request):
    method = request.method
    path = request.path
    query_params = request.query_params
    headers = request.headers
    body = request.body
    json_data = request.json()
    path_params = request.path_params
```

### Response オブジェクト

カスタムレスポンスを返す場合：

```python
from lambapi import Response

@app.get("/custom")
def custom_response():
    return Response(
        {"message": "Custom response"},
        status_code=201,
        headers={"Custom-Header": "value"}
    )
```

### ミドルウェア

```python
def cors_middleware(request, response):
    if isinstance(response, Response):
        response.headers.update({
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization'
        })
    return response

app.add_middleware(cors_middleware)
```

## CORS サポート

### 自動 OPTIONS ハンドリング

lambapi は CORS プリフライトリクエスト（OPTIONS）を自動的に処理します：

```python
from lambapi import API, create_cors_config

def create_app(event, context):
    app = API(event, context)
    
    # グローバル CORS 設定
    app.enable_cors(
        origins=["https://example.com", "https://app.example.com"],
        methods=["GET", "POST", "PUT", "DELETE"],
        headers=["Content-Type", "Authorization"],
        allow_credentials=True,
        max_age=3600
    )
    
    @app.get("/users")
    def get_users():
        return {"users": []}
    
    # OPTIONS /users が自動的に処理される
    return app
```

### ルートレベル CORS 設定

個別のルートに異なる CORS 設定を適用できます：

```python
# デフォルト CORS 設定
@app.get("/public", cors=True)
def public_endpoint():
    return {"message": "Public API"}

# カスタム CORS 設定
strict_cors = create_cors_config(
    origins=["https://trusted.example.com"],
    methods=["GET"],
    allow_credentials=False
)

@app.get("/admin", cors=strict_cors)
def admin_endpoint():
    return {"message": "Admin API"}
```

### CORS 設定オプション

| パラメータ | 説明 | デフォルト |
|-----------|------|-----------|
| `origins` | 許可するオリジン | `"*"` |
| `methods` | 許可する HTTP メソッド | `["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]` |
| `headers` | 許可するヘッダー | `["Content-Type", "Authorization", "X-Requested-With"]` |
| `allow_credentials` | 認証情報の送信を許可 | `False` |
| `max_age` | プリフライトキャッシュ時間（秒） | `None` |
| `expose_headers` | ブラウザに公開するレスポンスヘッダー | `None` |

### CORS の優先度

1. **ルートレベル設定** - `@app.get("/", cors=config)`
2. **グローバル設定** - `app.enable_cors()`
3. **設定なし** - CORS ヘッダーなし

## 構造化エラーハンドリング

### 統一されたエラーレスポンス

lambapi は、本番運用に適した構造化されたエラーハンドリングを提供します：

```python
from lambapi import API, ValidationError, NotFoundError

def create_app(event, context):
    app = API(event, context)
    
    @app.get("/users/{user_id}")
    def get_user(user_id: str):
        # バリデーション
        if not user_id.isdigit():
            raise ValidationError(
                "User ID must be numeric", 
                field="user_id", 
                value=user_id
            )
        
        # 存在チェック
        if int(user_id) > 1000:
            raise NotFoundError("User", user_id)
        
        return {"id": user_id, "name": f"User {user_id}"}
    
    return app
```

### エラーレスポンス形式

すべてのエラーは統一された形式で返されます：

```json
{
  "error": "VALIDATION_ERROR",
  "message": "User ID must be numeric",
  "status_code": 400,
  "field": "user_id",
  "value": "abc",
  "request_id": "12345678-1234-1234-1234-123456789012"
}
```

### 利用可能な例外クラス

| 例外クラス | HTTP ステータス | 用途 |
|-----------|----------------|------|
| `ValidationError` | 400 | 入力データのバリデーションエラー |
| `NotFoundError` | 404 | リソースが見つからない |
| `AuthenticationError` | 401 | 認証が必要・失敗 |
| `AuthorizationError` | 403 | 権限不足 |
| `ConflictError` | 409 | データの競合 |
| `RateLimitError` | 429 | レート制限に達した |
| `TimeoutError` | 408 | 処理がタイムアウト |
| `InternalServerError` | 500 | 内部サーバーエラー |
| `ServiceUnavailableError` | 503 | サービス利用不可 |

### カスタムエラーハンドラー

独自のエラーハンドリングロジックを定義できます：

```python
class BusinessLogicError(Exception):
    def __init__(self, message: str, business_code: str):
        self.message = message
        self.business_code = business_code

@app.error_handler(BusinessLogicError)
def handle_business_error(error, request, context):
    return Response({
        "error": "BUSINESS_ERROR",
        "message": error.message,
        "business_code": error.business_code,
        "request_id": context.aws_request_id
    }, status_code=422)

@app.get("/business-operation")
def business_operation():
    raise BusinessLogicError("Insufficient inventory", "INV001")
```

## サポートされる型変換

| 型注釈 | 変換動作 |
|--------|----------|
| `str` | そのまま文字列として渡される |
| `int` | `int()` で変換、失敗時は `0` |
| `float` | `float()` で変換、失敗時は `0.0` |
| `bool` | `'true'`, `'1'`, `'yes'`, `'on'` を `True` として認識 |

## ローカル開発

### CLI コマンドでの開発

```bash
# 新しいプロジェクトを作成
lambapi create my-api --template basic
lambapi create my-crud-api --template crud

# ローカルサーバーを起動
lambapi serve app
lambapi serve app --host 0.0.0.0 --port 3000
```

### Python から直接使用

```python
from lambapi import serve

# ローカルサーバーを起動
serve('app')  # app.py を起動
serve('my_app', host='0.0.0.0', port=3000)
```

### ローカル開発の特徴

- ✅ **完全な HTTP メソッド対応**: GET, POST, PUT, DELETE, PATCH, OPTIONS
- ✅ **パスパラメータ**: `/users/{user_id}` 形式をサポート
- ✅ **クエリパラメータ**: `?name=value&age=25` 形式をサポート
- ✅ **リクエストボディ**: JSON データの送受信
- ✅ **CORS サポート**: 開発用に自動で CORS ヘッダーを追加
- ✅ **Lambda 互換**: 実際の Lambda 環境と同じイベント・コンテキスト形式
- ✅ **エラーハンドリング**: 例外の適切な HTTP レスポンス変換

### プロジェクトテンプレート

#### Basic テンプレート
```bash
lambapi create hello-api --template basic
cd hello-api
lambapi serve app

# テスト
curl http://localhost:8000/
curl http://localhost:8000/hello/world
```

#### CRUD テンプレート
```bash
lambapi create todo-api --template crud
cd todo-api
lambapi serve app

# テスト
curl http://localhost:8000/items
curl -X POST http://localhost:8000/items -H "Content-Type: application/json" -d '{"name":"テスト項目"}'
```

### ローカルでのテスト

```bash
# 基本的なテスト
curl http://localhost:8000/
curl http://localhost:8000/users/123
curl http://localhost:8000/search?q=test&limit=5

# POST リクエスト
curl -X POST http://localhost:8000/users \
  -H "Content-Type: application/json" \
  -d '{"name":"Test User","email":"test@example.com"}'

# PUT リクエスト
curl -X PUT http://localhost:8000/users/1 \
  -H "Content-Type: application/json" \
  -d '{"name":"Updated Name"}'

# DELETE リクエスト
curl -X DELETE http://localhost:8000/users/1
```

### 本番デプロイとの互換性

ローカル開発サーバーは実際の Lambda + API Gateway 環境と完全に互換性があります：

| 機能 | ローカル | 本番 |
|------|----------|------|
| HTTP メソッド | ✅ 全対応 | ✅ 全対応 |
| パスパラメータ | ✅ `/users/{id}` | ✅ `/users/{id}` |
| クエリパラメータ | ✅ `?name=value` | ✅ `?name=value` |
| リクエストボディ | ✅ JSON | ✅ JSON |
| レスポンス形式 | ✅ 同一 | ✅ 同一 |
| エラーハンドリング | ✅ 同一 | ✅ 同一 |

### トラブルシューティング

#### よくある問題

1. **lambda_handler が見つからない**
   ```python
   # app.py の最後に必ず追加
   lambda_handler = create_lambda_handler(create_app)
   ```

2. **ポートが使用中**
   ```bash
   lambapi serve app --port 8001
   ```

3. **モジュールが見つからない**
   ```bash
   # 現在のディレクトリを確認
   ls app.py
   
   # 正しいファイル名を指定
   lambapi serve your_app_file
   ```

## 開発

### 開発環境のセットアップ

```bash
git clone https://github.com/your-username/lambapi.git
cd lambapi
pip install -e ".[dev]"
```

### テスト実行

```bash
pytest
```

### コードフォーマット

```bash
black lambapi tests examples
```

### 型チェック

```bash
mypy lambapi
```

## ライセンス

MIT License - 詳細は [LICENSE](LICENSE) ファイルを参照してください。

## 貢献

プルリクエストや Issue は歓迎します！詳細は [CONTRIBUTING.md](CONTRIBUTING.md) を参照してください。

## 関連プロジェクト

- [AWS Lambda Python Runtime](https://docs.aws.amazon.com/lambda/latest/dg/python-programming-model.html)