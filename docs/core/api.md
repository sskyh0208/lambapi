# API クラス

lambapi の中心となるクラスです。HTTP リクエストの処理、ルーティング、レスポンス生成を管理します。

## 基本的な使用方法

### API インスタンスの作成

```python
from lambapi import API, create_lambda_handler

def create_app(event, context):
    app = API(event, context)
    # ルートを定義...
    return app

lambda_handler = create_lambda_handler(create_app)
```

### HTTP メソッドの定義

```python
@app.get("/users")
def get_users():
    return {"users": []}

@app.post("/users")  
def create_user():
    return {"message": "User created"}

@app.put("/users/{user_id}")
def update_user(user_id: str):
    return {"message": f"User {user_id} updated"}

@app.delete("/users/{user_id}")
def delete_user(user_id: str):
    return {"message": f"User {user_id} deleted"}

@app.patch("/users/{user_id}")
def patch_user(user_id: str):
    return {"message": f"User {user_id} patched"}
```

## 高度な機能

### カスタムレスポンス

```python
from lambapi import Response

@app.get("/custom")
def custom_response():
    return Response(
        {"data": "custom"},
        status_code=201,
        headers={"X-Custom": "header"}
    )
```

### エラーハンドリング

```python
from lambapi import ValidationError

@app.get("/error-example")
def error_example():
    # 自動的に適切な HTTP ステータスコードで返される
    raise ValidationError("Invalid input")
```

### リクエストオブジェクトへのアクセス

```python
@app.post("/upload")
def upload_file(request):
    # 生のリクエストオブジェクトにアクセス
    content_type = request.headers.get("content-type")
    body = request.body
    return {"received": len(body)}
```

## API クラスの詳細

### コンストラクタ

```python
class API:
    def __init__(self, event: dict, context: Any, cors_config: Optional[CORSConfig] = None):
        """
        Args:
            event: Lambda event オブジェクト
            context: Lambda context オブジェクト  
            cors_config: CORS 設定（オプション）
        """
```

### メソッド一覧

| メソッド | 説明 |
|----------|------|
| `get(path)` | GET リクエストのハンドラを登録 |
| `post(path)` | POST リクエストのハンドラを登録 |
| `put(path)` | PUT リクエストのハンドラを登録 |
| `delete(path)` | DELETE リクエストのハンドラを登録 |
| `patch(path)` | PATCH リクエストのハンドラを登録 |
| `route(methods, path)` | 複数の HTTP メソッドを一度に登録 |
| `include_router(router)` | Router インスタンスを追加 |
| `error_handler(exception_class)` | エラーハンドラを登録 |

### ルートパラメータ

パスパラメータは `{}` で囲みます：

```python
@app.get("/users/{user_id}")
def get_user(user_id: str):
    return {"user_id": user_id}

@app.get("/posts/{post_id}/comments/{comment_id}")  
def get_comment(post_id: str, comment_id: str):
    return {"post_id": post_id, "comment_id": comment_id}
```

## Router との組み合わせ

```python
from lambapi import Router

# 別ファイルで定義
user_router = Router()

@user_router.get("/")
def list_users():
    return {"users": []}

@user_router.get("/{user_id}")
def get_user(user_id: str):
    return {"user_id": user_id}

# メインアプリで使用
def create_app(event, context):
    app = API(event, context)
    app.include_router(user_router, prefix="/users")
    return app
```

## CORS 設定

```python
from lambapi import CORSConfig

cors_config = CORSConfig(
    allow_origins=["https://example.com"],
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
    max_age=3600
)

app = API(event, context, cors_config=cors_config)
```

## レスポンス形式

### 自動 JSON 変換

```python
@app.get("/data")
def get_data():
    # 自動的に JSON に変換される
    return {
        "message": "success",
        "data": [1, 2, 3],
        "timestamp": "2024-01-01T00:00:00Z"
    }
```

### カスタムレスポンス

```python
@app.get("/xml")
def get_xml():
    return Response(
        "<xml>data</xml>",
        status_code=200,
        headers={"Content-Type": "application/xml"}
    )
```

## パフォーマンス最適化

### 関数シグネチャキャッシュ

lambapi は関数のシグネチャ情報をキャッシュして、Lambda のコールドスタート時間を最小限に抑えます。

```python
# キャッシュの恩恵を受けるため、関数定義は一貫性を保つ
@app.get("/fast")
def fast_handler(user_id: str = Path(...)):
    return {"user_id": user_id}
```

### メモリ使用量の最適化

```python
# 大きなオブジェクトは関数外で定義してメモリを節約
LARGE_CONFIG = load_config()

@app.get("/config")
def get_config():
    return {"config": LARGE_CONFIG}
```

## デバッグとログ

### リクエスト情報の確認

```python
@app.post("/debug")
def debug_request(request):
    return {
        "method": request.method,
        "path": request.path,
        "headers": dict(request.headers),
        "query_params": dict(request.query_params),
        "body": request.body
    }
```

### カスタムログ

```python
import logging

logger = logging.getLogger(__name__)

@app.get("/logged")
def logged_handler():
    logger.info("Handler called")
    return {"status": "logged"}
```

## 実践的な例

### RESTful API

```python
from lambapi import API, Query, Path, Body, ValidationError
from typing import List, Optional

def create_app(event, context):
    app = API(event, context)
    
    # データストレージ（本来は DB）
    users = []
    
    @app.get("/users")
    def list_users(
        page: int = Query(1, ge=1),
        limit: int = Query(10, ge=1, le=100)
    ):
        start = (page - 1) * limit
        end = start + limit
        return {
            "users": users[start:end],
            "page": page,
            "limit": limit,
            "total": len(users)
        }
    
    @app.post("/users")
    def create_user(user_data: dict = Body(...)):
        if not user_data.get("name"):
            raise ValidationError("Name is required")
        
        user_id = len(users) + 1
        user = {"id": user_id, **user_data}
        users.append(user)
        
        return Response(user, status_code=201)
    
    @app.get("/users/{user_id}")
    def get_user(user_id: int = Path(..., ge=1)):
        user = next((u for u in users if u["id"] == user_id), None)
        if not user:
            return Response({"error": "User not found"}, status_code=404)
        return user
    
    return app
```