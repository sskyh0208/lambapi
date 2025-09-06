# Lambda での使用方法

lambapi アプリケーションを AWS Lambda で使用する際の設定方法について説明します。

## ZIP アーカイブでの使用

### Lambda 関数の設定

#### 必須設定項目

| 設定項目 | 値 | 説明 |
|---------|---|------|
| **ランタイム** | `Python 3.13` | Python バージョン |
| **ハンドラー** | `app.lambda_handler` | 関数の場所 |
| **パッケージタイプ** | `Zip` | デプロイ形式 |

#### アプリケーションコード

```python title="app.py"
from lambapi import API, create_lambda_handler, Query, Path, Body
from dataclasses import dataclass
from typing import Optional

@dataclass
class CreateUserRequest:
    name: str
    email: str
    age: Optional[int] = None

def create_app(event, context):
    app = API(event, context)

    @app.get("/")
    def hello():
        return {"message": "Hello from Lambda!"}

    @app.get("/users/{user_id}")
    def get_user(user_id: str = Path(..., description="ユーザー ID")):
        return {"user_id": user_id, "name": f"User {user_id}"}

    @app.get("/search")
    def search(
        q: str = Query(..., min_length=1, description="検索クエリ"),
        limit: int = Query(10, ge=1, le=100, description="結果数")
    ):
        return {
            "query": q,
            "limit": limit,
            "results": [f"result-{i}" for i in range(1, min(limit, 5) + 1)]
        }

    @app.post("/users")
    def create_user(user_data: CreateUserRequest = Body(...)):
        return {
            "message": "User created successfully",
            "user": {"name": user_data.name, "email": user_data.email, "age": user_data.age}
        }

    return app

# ★重要: この関数名がハンドラー設定に対応
lambda_handler = create_lambda_handler(create_app)
```

#### ハンドラー設定の例

**基本パターン:**
- ファイル名: `app.py` → ハンドラー: `app.lambda_handler`
- ファイル名: `main.py` → ハンドラー: `main.lambda_handler`

**関数名が異なる場合:**
```python title="app.py"
# 関数名を変更
api_handler = create_lambda_handler(create_app)
```
- ハンドラー: `app.api_handler`

**サブディレクトリ構成:**
```
ZIP 内容:
├── src/
│   └── app.py
└── requirements/
```
- ハンドラー: `src.app.lambda_handler`

#### Lambda 関数の推奨設定

```
メモリサイズ: 256MB - 1024MB
タイムアウト: 30 秒 (API Gateway 使用時の上限)
環境変数:
  ENVIRONMENT=production
  LOG_LEVEL=INFO
```

## ECR コンテナイメージでの使用

### Lambda 関数の設定

#### 必須設定項目

| 設定項目 | 値 | 説明 |
|---------|---|------|
| **パッケージタイプ** | `Image` | コンテナ形式 |
| **コンテナイメージ URI** | ECR URI | イメージの場所 |

#### Dockerfile の設定

```dockerfile title="Dockerfile"
FROM public.ecr.aws/lambda/python:3.13

# 依存関係をインストール
COPY requirements.txt .
RUN pip install -r requirements.txt

# アプリケーションコードをコピー
COPY app.py ${LAMBDA_TASK_ROOT}/

# ★重要: CMD でハンドラーを指定
CMD ["app.lambda_handler"]
```

#### CMD 設定の例

**基本パターン:**
```dockerfile
CMD ["app.lambda_handler"]
```

**異なるファイル名:**
```dockerfile
CMD ["main.lambda_handler"]
```

**サブディレクトリ構成:**
```dockerfile
COPY src/app.py ${LAMBDA_TASK_ROOT}/src/
CMD ["src.app.lambda_handler"]
```

**モジュール化された構成:**
```dockerfile
COPY handlers/ ${LAMBDA_TASK_ROOT}/handlers/
CMD ["handlers.api.lambda_handler"]
```

#### Lambda 関数の推奨設定

```
メモリサイズ: 512MB - 2048MB (コンテナは多くのメモリを推奨)
タイムアウト: 30 秒 (API Gateway 使用時の上限)
環境変数:
  ENVIRONMENT=production
  LOG_LEVEL=INFO
```

## API Gateway との統合

### プロキシ統合の設定

Lambda 関数を API として公開するには、API Gateway との統合が必要です。

#### 必要な設定

1. **API Gateway の作成**
   - REST API を作成
   - リソース: `/{proxy+}`
   - メソッド: `ANY`

2. **Lambda 統合**
   - 統合タイプ: `Lambda プロキシ統合`
   - Lambda 関数: 作成した関数を選択

3. **Lambda 関数の権限**
   - API Gateway からの実行権限を付与

#### イベント形式

lambapi は以下の形式の Lambda イベントを処理します：

```json
{
  "httpMethod": "GET",
  "path": "/users/123",
  "queryStringParameters": {"limit": "10"},
  "headers": {"Content-Type": "application/json"},
  "body": "{\"name\":\"test\"}",
  "requestContext": {
    "requestId": "12345",
    "stage": "prod"
  }
}
```

## 環境別設定

### 設定の分離

```python title="app.py"
import os
from lambapi import API, create_lambda_handler

def create_app(event, context):
    app = API(event, context)

    # 環境別設定
    if os.getenv("ENVIRONMENT") == "development":
        app.enable_cors(origins="*")
    else:
        app.enable_cors(origins=["https://myapp.com"])

    @app.get("/")
    def root():
        return {
            "message": "Hello from Lambda!",
            "environment": os.getenv("ENVIRONMENT", "development")
        }

    return app

lambda_handler = create_lambda_handler(create_app)
```

### 環境変数の設定

Lambda 関数の設定で以下の環境変数を設定：

```bash
# 基本設定
ENVIRONMENT=production
LOG_LEVEL=INFO

# アプリケーション固有の設定
DATABASE_URL=your-database-url
API_KEY=your-api-key
```

## よくある設定ミス

### ZIP デプロイでの問題

#### 1. ハンドラー設定の間違い

**❌ 間違い:**
```
ハンドラー: lambda_handler          # ファイル名なし
ハンドラー: app                     # 関数名なし
ハンドラー: app/lambda_handler      # スラッシュ使用
```

**✅ 正しい:**
```
ハンドラー: app.lambda_handler
```

#### 2. ファイル構造とハンドラーの不一致

**ZIP 内容:**
```
└── src/
    └── app.py
```

**❌ 間違い:** `ハンドラー: app.lambda_handler`
**✅ 正しい:** `ハンドラー: src.app.lambda_handler`

### ECR デプロイでの問題

#### 1. CMD 設定の間違い

**❌ 間違い:**
```dockerfile
CMD ["python", "app.py"]           # 通常の Python 実行
CMD ["app", "lambda_handler"]      # 不正な形式
```

**✅ 正しい:**
```dockerfile
CMD ["app.lambda_handler"]         # Lambda 形式
```

#### 2. ファイル配置と CMD の不一致

**コンテナ内構造:**
```
/var/task/
└── src/
    └── app.py
```

**❌ 間違い:** `CMD ["app.lambda_handler"]`
**✅ 正しい:** `CMD ["src.app.lambda_handler"]`

## デバッグとテスト

### ローカルでの動作確認

```python title="test_lambda.py"
from app import lambda_handler

# テストイベント
event = {
    'httpMethod': 'GET',
    'path': '/',
    'headers': {},
    'body': None,
    'queryStringParameters': None
}

# モックコンテキスト
class MockContext:
    aws_request_id = 'test-123'
    function_name = 'test-function'
    memory_limit_in_mb = '256'
    remaining_time_in_millis = lambda self: 30000

# テスト実行
try:
    result = lambda_handler(event, MockContext())
    print("✅ ハンドラー設定正常:", result['statusCode'])
    print("レスポンス:", result['body'])
except Exception as e:
    print("❌ ハンドラー設定エラー:", e)
```

### Lambda での動作確認

```python title="app.py"
def create_app(event, context):
    app = API(event, context)

    @app.get("/debug")
    def debug_info():
        return {
            "lambda_info": {
                "function_name": context.function_name,
                "request_id": context.aws_request_id,
                "memory_limit": context.memory_limit_in_mb,
                "remaining_time": context.get_remaining_time_in_millis()
            },
            "request_info": {
                "method": event.get('httpMethod'),
                "path": event.get('path'),
                "headers": list(event.get('headers', {}).keys())
            }
        }

    return app
```

## パフォーマンス最適化

### Cold Start の軽減

```python title="app.py"
# グローバルスコープで初期化（Lambda コンテナ再利用時に有効）
import boto3

# 接続プールなどはグローバルに配置
DATABASE_CONNECTION = None

def get_database_connection():
    global DATABASE_CONNECTION
    if DATABASE_CONNECTION is None:
        DATABASE_CONNECTION = boto3.client('dynamodb')
    return DATABASE_CONNECTION

def create_app(event, context):
    app = API(event, context)

    @app.get("/users")
    def get_users():
        db = get_database_connection()  # 既存接続を再利用
        return {"users": []}

    return app

lambda_handler = create_lambda_handler(create_app)
```

### メモリサイズの調整

| 用途 | 推奨メモリサイズ |
|------|-----------------|
| 軽量 API | 256MB - 512MB |
| 標準的な API | 512MB - 1024MB |
| データ処理含む API | 1024MB - 2048MB |
| 大規模な API | 2048MB+ |

## まとめ

### ZIP デプロイ
- ハンドラー: `{ファイル名}.{関数名}`
- ランタイム: `Python 3.13`
- 推奨メモリ: 256MB-1024MB

### ECR デプロイ
- CMD: `["ファイル名.関数名"]`
- パッケージタイプ: `Image`
- 推奨メモリ: 512MB-2048MB

### 共通設定
- API Gateway との統合にはプロキシ統合を使用
- 環境変数でアプリケーション設定を管理
- デバッグ用エンドポイントで動作確認
