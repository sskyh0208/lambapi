# ローカル開発

lambapi はローカル開発を簡単にするためのツールを提供しています。pip install 後すぐに使用できます。

## CLI コマンド

### 新しいプロジェクトの作成

```bash
# 基本的なプロジェクト
lambapi create my-api --template basic

# CRUD API プロジェクト
lambapi create todo-api --template crud
```

### ローカルサーバーの起動

```bash
# デフォルト設定（localhost:8000）
lambapi serve app

# カスタム設定
lambapi serve app --host 0.0.0.0 --port 3000

# 異なるファイル名
lambapi serve my_application
```

## Python API

CLI コマンドに加えて、Python から直接ローカルサーバーを起動することも可能です：

```python
from lambapi import serve

# 基本的な使用
serve('app')

# カスタム設定
serve('app', host='localhost', port=8000)
```

## 機能

### 完全な Lambda 互換性

ローカル開発サーバーは実際の AWS Lambda + API Gateway 環境と完全に互換性があります：

- ✅ **HTTP メソッド**: GET, POST, PUT, DELETE, PATCH, OPTIONS
- ✅ **パスパラメータ**: `/users/{user_id}` 形式
- ✅ **クエリパラメータ**: `?name=value&age=25` 形式
- ✅ **リクエストボディ**: JSON データの送受信
- ✅ **レスポンス形式**: 本番環境と同一
- ✅ **エラーハンドリング**: 同じ例外処理

### 自動 CORS 対応

開発環境では自動的に CORS ヘッダーが追加されます：

```
Access-Control-Allow-Origin: *
Access-Control-Allow-Methods: GET, POST, PUT, DELETE, PATCH, OPTIONS
Access-Control-Allow-Headers: Content-Type, Authorization
```

### ホットリロード機能

ファイルの変更を自動的に検知してサーバーを再起動します：

- ✅ **自動ファイル監視**: Python ファイルの変更を検知
- ✅ **ポート競合解決**: サーバー再起動時のポート競合を自動処理
- ✅ **エラー時継続**: アプリケーション読み込みエラー時もサーバーは継続稼働

```bash
# ホットリロード付きで起動
lambapi serve app --hot-reload

# ファイル変更時の出力例
⏳ ポート 8000 の解放を待機中...
✅ ポート 8000 が解放されました
🚀 サーバーを再起動しました
```

### リアルタイムログ

サーバーはリクエストとレスポンスをリアルタイムで表示します：

```
GET / -> 200
POST /users -> 201
GET /users/123 -> 404
```

## プロジェクトテンプレート

### Basic テンプレート

シンプルな Hello World API：

```bash
lambapi create hello-api --template basic
cd hello-api
lambapi serve app
```

生成されるファイル：
- `app.py` - メインアプリケーション
- `requirements.txt` - 依存関係
- `template.yaml` - SAM テンプレート
- `README.md` - プロジェクト説明

### CRUD テンプレート

完全な CRUD API：

```bash
lambapi create todo-api --template crud
cd todo-api
lambapi serve app
```

追加機能：
- 完全な CRUD 操作
- バリデーション
- エラーハンドリング
- 検索・フィルタリング

## 使用例

### 最小構成のアプリケーション

```python
# app.py
from lambapi import API, create_lambda_handler

def create_app(event, context):
    app = API(event, context)
    
    @app.get("/")
    def hello():
        return {"message": "Hello, lambapi!"}
    
    @app.get("/users/{user_id}")
    def get_user(user_id: str):
        return {"user_id": user_id, "name": f"User {user_id}"}
    
    return app

lambda_handler = create_lambda_handler(create_app)
```

```bash
lambapi serve app
curl http://localhost:8000/
curl http://localhost:8000/users/123
```

### 実践的なアプリケーション

```python
# practical_app.py
from lambapi import API, Response, create_lambda_handler
from lambapi.exceptions import ValidationError, NotFoundError

def create_app(event, context):
    app = API(event, context)
    
    # データストア
    items = {}
    
    @app.get("/items")
    def list_items(limit: int = 10, search: str = ""):
        filtered = [
            item for item in items.values()
            if not search or search.lower() in item["name"].lower()
        ]
        return {"items": filtered[:limit], "total": len(filtered)}
    
    @app.post("/items")
    def create_item(request):
        data = request.json()
        
        if not data.get("name"):
            raise ValidationError("Name is required", field="name")
        
        item_id = str(len(items) + 1)
        item = {"id": item_id, "name": data["name"]}
        items[item_id] = item
        
        return Response({"item": item}, status_code=201)
    
    @app.get("/items/{item_id}")
    def get_item(item_id: str):
        if item_id not in items:
            raise NotFoundError("Item", item_id)
        return {"item": items[item_id]}
    
    return app

lambda_handler = create_lambda_handler(create_app)
```

## テスト方法

### 基本的なテスト

```bash
# ヘルスチェック
curl http://localhost:8000/

# パスパラメータ
curl http://localhost:8000/users/123

# クエリパラメータ
curl http://localhost:8000/search?q=test&limit=10
```

### POST/PUT/DELETE テスト

```bash
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

### エラーテスト

```bash
# バリデーションエラー
curl -X POST http://localhost:8000/users \
  -H "Content-Type: application/json" \
  -d '{}'

# Not Found エラー
curl http://localhost:8000/users/999
```

## デバッグ

### Lambda イベントの確認

実際に送信される Lambda イベント形式を確認：

```python
@app.get("/debug")
def debug_info():
    return {
        "event": event,  # Lambda イベント
        "context_info": {
            "request_id": context.aws_request_id,
            "function_name": context.function_name
        }
    }
```

### リクエスト詳細の表示

```python
@app.get("/request-info")
def request_info(request):
    return {
        "method": request.method,
        "path": request.path,
        "headers": dict(request.headers),
        "query_params": request.query_params,
        "path_params": request.path_params
    }
```

## トラブルシューティング

### よくある問題

1. **アプリケーション読み込みエラー**
   
   アプリケーションファイルの読み込みに失敗した場合、エラーページが表示されます。
   ファイルを修正して保存すると、ホットリロード機能により自動的に更新されます。
   
   ```python
   # app.py の最後に必ず追加
   lambda_handler = create_lambda_handler(create_app)
   ```

2. **ポートが使用中**
   ```bash
   lambapi serve app --port 8001
   ```
   
   ホットリロード使用時は、ポートが自動的に解放されるまで待機します。

3. **モジュールが見つからない**
   ```bash
   # ファイルの存在確認
   ls app.py
   
   # 正しいファイル名を指定
   lambapi serve your_app_file
   ```

4. **CORS エラー**
   
   ローカル開発では自動的に CORS が有効になりますが、カスタム設定が必要な場合：
   
   ```python
   app.enable_cors(
       origins=["http://localhost:3000"],
       methods=["GET", "POST"],
       headers=["Content-Type"]
   )
   ```

### パフォーマンステスト

```bash
# ApacheBench を使用
ab -n 1000 -c 10 http://localhost:8000/

# curl でレスポンス時間測定
curl -w "@curl-format.txt" -o /dev/null -s http://localhost:8000/users
```

## 本番デプロイとの比較

| 項目 | ローカル開発 | 本番環境 |
|------|--------------|----------|
| ホスト | localhost:8000 | API Gateway URL |
| CORS | 自動で `*` 許可 | 明示的な設定が必要 |
| ログ | コンソール出力 | CloudWatch Logs |
| タイムアウト | なし | Lambda の制限（最大 15 分） |
| リクエストサイズ | HTTP サーバーの制限 | API Gateway の制限（10MB） |
| コールドスタート | なし | Lambda の初回実行で発生 |

## 次のステップ

ローカル開発が完了したら：

1. [デプロイメント](../guides/deployment.md) - 本番環境へのデプロイ
2. [テスト](../guides/testing.md) - 自動テストの作成
3. [パフォーマンス](../guides/performance.md) - パフォーマンス最適化
4. [セキュリティ](../guides/security.md) - セキュリティ対策

ローカル開発環境は本番環境と完全に互換性があるため、ローカルで動作するコードはそのまま Lambda にデプロイできます。