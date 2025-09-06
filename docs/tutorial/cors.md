# CORS 設定

Cross-Origin Resource Sharing (CORS) は、Web ブラウザのセキュリティ機能で、異なるオリジンからのリクエストを制御します。lambapi は CORS の設定と自動処理を簡単に行えます。

## CORS とは

CORS は、Web ページが異なるドメイン、プロトコル、ポートからリソースにアクセスすることを許可する仕組みです。

### 同一オリジンポリシー

ブラウザはセキュリティのため、デフォルトで同一オリジンからのリクエストのみを許可します：

```
https://example.com/page → https://example.com/api ✅ (同一オリジン)
https://example.com/page → https://api.example.com/data ❌ (異なるサブドメイン)
https://example.com/page → http://example.com/api ❌ (異なるプロトコル)
```

### CORS の仕組み

CORS は HTTP ヘッダーを使用して、クロスオリジンリクエストを許可します：

1. **Simple Request**: 直接リクエストを送信
2. **Preflight Request**: OPTIONS リクエストで事前確認

## lambapi での CORS 設定

### 1. グローバル CORS 設定

すべてのエンドポイントに適用される設定：

```python
from lambapi import API, create_lambda_handler

def create_app(event, context):
    app = API(event, context)
    
    # 基本的な CORS 有効化
    app.enable_cors()
    
    @app.get("/api/users")
    def get_users():
        return {"users": []}
    
    return app
```

### 2. 詳細な CORS 設定

```python
from lambapi import Query, Path, Body

def create_app(event, context):
    app = API(event, context)
    
    # 詳細な CORS 設定
    app.enable_cors(
        origins=["https://myapp.com", "https://admin.myapp.com"],
        methods=["GET", "POST", "PUT", "DELETE"],
        headers=["Content-Type", "Authorization", "X-API-Key"],
        allow_credentials=True,
        max_age=3600,  # プリフライトキャッシュ時間（秒）
        expose_headers=["X-Total-Count"]
    )
    
    @app.get("/api/data")
    def get_data(
        page: int = Query(1, ge=1, description="ページ番号"),
        per_page: int = Query(20, ge=1, le=100, description="1 ページあたりの件数")
    ):
        return {
            "data": f"secure data - page {page}",
            "pagination": {"page": page, "per_page": per_page}
        }
    
    return app
```

### 3. ルートレベル CORS 設定

個別のエンドポイントに異なる CORS 設定を適用：

```python
from lambapi import create_cors_config

def create_app(event, context):
    app = API(event, context)
    
    # パブリック API（緩い設定）
    @app.get("/api/public", cors=True)
    def public_endpoint():
        return {"message": "Public data"}
    
    # 管理者 API（厳格な設定）
    admin_cors = create_cors_config(
        origins=["https://admin.myapp.com"],
        methods=["GET", "POST"],
        allow_credentials=True
    )
    
    @app.get("/api/admin", cors=admin_cors)
    def admin_endpoint():
        return {"message": "Admin data"}
    
    # CORS 無効のエンドポイント
    @app.get("/api/internal")
    def internal_endpoint():
        return {"message": "Internal only"}
    
    return app
```

## CORS 設定オプション

### origins（オリジン設定）

```python
# すべてのオリジンを許可（開発用）
app.enable_cors(origins="*")

# 特定のオリジンのみ許可
app.enable_cors(origins="https://myapp.com")

# 複数のオリジンを許可
app.enable_cors(origins=[
    "https://myapp.com",
    "https://admin.myapp.com",
    "http://localhost:3000"  # 開発環境
])

# 正規表現パターン（実装で対応可能）
# app.enable_cors(origins=r"https://.*\.myapp\.com")
```

### methods（HTTP メソッド）

```python
# デフォルト設定
app.enable_cors(methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])

# 読み取り専用 API
app.enable_cors(methods=["GET", "OPTIONS"])

# フルアクセス
app.enable_cors(methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"])
```

### headers（許可ヘッダー）

```python
# 基本的なヘッダー
app.enable_cors(headers=["Content-Type"])

# 認証付き API
app.enable_cors(headers=[
    "Content-Type",
    "Authorization",
    "X-API-Key",
    "X-Requested-With"
])

# カスタムヘッダー
app.enable_cors(headers=[
    "Content-Type",
    "Authorization",
    "X-Custom-Header",
    "X-Client-Version"
])
```

### allow_credentials（認証情報）

```python
# Cookie や Authorization ヘッダーを許可
app.enable_cors(allow_credentials=True)

# 注意: origins="*" と allow_credentials=True は同時に使用不可
app.enable_cors(
    origins=["https://myapp.com"],  # 具体的なオリジンを指定
    allow_credentials=True
)
```

### max_age（キャッシュ時間）

```python
# プリフライトリクエストの結果を 1 時間キャッシュ
app.enable_cors(max_age=3600)

# キャッシュ無し（毎回プリフライト）
app.enable_cors(max_age=0)

# 長期キャッシュ（1 日）
app.enable_cors(max_age=86400)
```

### expose_headers（公開ヘッダー）

```python
# JavaScript からアクセス可能なレスポンスヘッダー
app.enable_cors(expose_headers=[
    "X-Total-Count",
    "X-Page-Count",
    "X-Rate-Limit-Remaining"
])
```

## プリフライトリクエストの自動処理

lambapi は OPTIONS リクエスト（プリフライト）を自動的に処理します：

```python
def create_app(event, context):
    app = API(event, context)
    
    app.enable_cors(
        origins=["https://myapp.com"],
        methods=["GET", "POST", "PUT", "DELETE"],
        headers=["Content-Type", "Authorization"]
    )
    
    @app.post("/api/users")
    def create_user(request):
        return {"message": "User created"}
    
    # OPTIONS /api/users が自動的に処理される
    # ブラウザが POST リクエスト前に自動送信
    
    return app
```

## 環境別 CORS 設定

### 開発環境

```python
import os

def create_app(event, context):
    app = API(event, context)
    
    if os.getenv("ENVIRONMENT") == "development":
        # 開発環境では緩い設定
        app.enable_cors(
            origins="*",
            methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            headers=["*"]
        )
    else:
        # 本番環境では厳格な設定
        app.enable_cors(
            origins=["https://myapp.com"],
            methods=["GET", "POST", "PUT", "DELETE"],
            headers=["Content-Type", "Authorization"],
            allow_credentials=True
        )
    
    return app
```

### 設定ファイルからの読み込み

```python
import json

def load_cors_config():
    """設定ファイルから CORS 設定を読み込み"""
    try:
        with open("cors_config.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {
            "origins": "*",
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "headers": ["Content-Type"]
        }

def create_app(event, context):
    app = API(event, context)
    
    cors_config = load_cors_config()
    app.enable_cors(**cors_config)
    
    return app
```

```json title="cors_config.json"
{
    "origins": ["https://myapp.com", "https://admin.myapp.com"],
    "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    "headers": ["Content-Type", "Authorization", "X-API-Key"],
    "allow_credentials": true,
    "max_age": 3600
}
```

## セキュリティ考慮事項

### 1. origins の設定

```python
# ❌ 本番環境では避ける
app.enable_cors(origins="*", allow_credentials=True)

# ✅ 具体的なオリジンを指定
app.enable_cors(
    origins=["https://myapp.com"],
    allow_credentials=True
)

# ✅ 環境変数から読み込み
import os
app.enable_cors(
    origins=os.getenv("ALLOWED_ORIGINS", "").split(","),
    allow_credentials=True
)
```

### 2. 機密データの保護

```python
def create_app(event, context):
    app = API(event, context)
    
    # パブリック API は緩い設定
    public_cors = create_cors_config(origins="*")
    
    @app.get("/api/public/status", cors=public_cors)
    def public_status():
        return {"status": "ok"}
    
    # プライベート API は厳格な設定
    private_cors = create_cors_config(
        origins=["https://admin.myapp.com"],
        allow_credentials=True
    )
    
    @app.get("/api/private/users", cors=private_cors)
    def private_users():
        return {"users": ["sensitive", "data"]}
    
    return app
```

## トラブルシューティング

### 1. CORS エラーの確認

```javascript
// フロントエンド（JavaScript）での確認
fetch('https://api.example.com/users', {
    method: 'GET',
    headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer token'
    },
    credentials: 'include'  // allow_credentials=True が必要
})
.then(response => response.json())
.then(data => console.log(data))
.catch(error => {
    // CORS エラーの場合、詳細なエラー情報は見えない
    console.error('CORS error:', error);
});
```

### 2. デバッグ用ログ

```python
def create_app(event, context):
    app = API(event, context)
    
    def cors_debug_middleware(request, response):
        # CORS ヘッダーをログ出力
        if isinstance(response, Response):
            cors_headers = {k: v for k, v in response.headers.items() 
                          if k.startswith('Access-Control-')}
            print(f"CORS headers: {cors_headers}")
        return response
    
    app.add_middleware(cors_debug_middleware)
    app.enable_cors(origins=["https://myapp.com"])
    
    return app
```

### 3. よくある問題と解決策

| 問題 | 原因 | 解決策 |
|------|------|--------|
| `Access-Control-Allow-Origin` エラー | オリジンが許可されていない | `origins` 設定を確認 |
| `Access-Control-Allow-Methods` エラー | HTTP メソッドが許可されていない | `methods` 設定に追加 |
| `Access-Control-Allow-Headers` エラー | ヘッダーが許可されていない | `headers` 設定に追加 |
| 認証情報が送信されない | `allow_credentials` が false | `allow_credentials=True` に設定 |
| プリフライトで失敗 | OPTIONS が処理されていない | lambapi が自動処理（確認が必要） |

## 実際のフロントエンド連携例

### React アプリケーション

```javascript
// React での API 呼び出し
const apiCall = async () => {
    try {
        const response = await fetch('https://api.example.com/users', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            credentials: 'include',
            body: JSON.stringify({
                name: 'John Doe',
                email: 'john@example.com'
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('Success:', data);
    } catch (error) {
        console.error('Error:', error);
    }
};
```

### 対応する lambapi 設定

```python
def create_app(event, context):
    app = API(event, context)
    
    # React アプリに対応する CORS 設定
    app.enable_cors(
        origins=["https://myapp.com", "http://localhost:3000"],
        methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        headers=["Content-Type", "Authorization"],
        allow_credentials=True,
        max_age=3600
    )
    
    @app.post("/users")
    def create_user(request):
        user_data = request.json()
        return {"message": "User created", "user": user_data}
    
    return app
```

CORS の適切な設定により、セキュリティを保ちながらフロントエンドアプリケーションとのスムーズな連携が可能になります。