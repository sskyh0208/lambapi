# API

::: lambapi.core.API
    options:
      members:
        - __init__
        - get
        - post
        - put
        - delete
        - patch
        - include_router
        - add_middleware
        - enable_cors
        - error_handler
        - default_error_handler
        - handle_request

lambapi のメインクラスです。すべての API 機能はこのクラスを通じて提供されます。

## 基本的な使用法

### 従来の方法
```python
from lambapi import API, create_lambda_handler

def create_app(event, context):
    app = API(event, context)
    
    @app.get("/")
    def hello():
        return {"message": "Hello, World!"}
    
    return app

lambda_handler = create_lambda_handler(create_app)
```

### 依存性注入を使った方法（推奨）
```python
from lambapi import API, create_lambda_handler, Query, Path, Body
from dataclasses import dataclass

@dataclass
class UserData:
    name: str
    email: str

def create_app(event, context):
    app = API(event, context)
    
    @app.get("/users/{user_id}")
    def get_user(
        user_id: str = Path(..., description="ユーザー ID"),
        include_details: bool = Query(False, description="詳細情報を含める")
    ):
        return {
            "user_id": user_id,
            "name": f"User {user_id}",
            "details": "詳細情報" if include_details else None
        }
    
    @app.post("/users")
    def create_user(user: UserData = Body(...)):
        return {"message": "User created", "user": user}
    
    return app

lambda_handler = create_lambda_handler(create_app)
```

## 初期化

### API(event, context)

Lambda から渡されるイベントとコンテキストで API インスタンスを初期化します。

**パラメータ:**

- `event` (Dict[str, Any]): Lambda イベントオブジェクト
- `context` (Any): Lambda コンテキストオブジェクト

**例:**

```python
def lambda_handler(event, context):
    app = API(event, context)
    # ルート定義...
    return app.handle_request()
```

## HTTP メソッドデコレータ

### get(path, request_format=None, response_format=None, cors=None)

GET リクエストのエンドポイントを定義します。

**パラメータ:**

- `path` (str): エンドポイントのパス（デフォルト: "/"）
- `request_format` (Type, optional): リクエストのバリデーション用データクラス
- `response_format` (Type, optional): レスポンスのバリデーション用データクラス
- `cors` (Union[bool, CORSConfig, None]): CORS 設定

**例:**

```python
@app.get("/")
def root():
    return {"message": "Root endpoint"}

@app.get("/users/{user_id}")
def get_user(user_id: str):
    return {"id": user_id, "name": f"User {user_id}"}

@app.get("/search")
def search(q: str = "", limit: int = 10):
    return {"query": q, "results": [], "limit": limit}
```

### post(path, request_format=None, response_format=None, cors=None)

POST リクエストのエンドポイントを定義します。

**例:**

```python
@app.post("/users")
def create_user(request):
    user_data = request.json()
    return {"message": "User created", "user": user_data}
```

### put(path, request_format=None, response_format=None, cors=None)

PUT リクエストのエンドポイントを定義します。

### delete(path, request_format=None, response_format=None, cors=None)

DELETE リクエストのエンドポイントを定義します。

### patch(path, request_format=None, response_format=None, cors=None)

PATCH リクエストのエンドポイントを定義します。

## ルーター統合

### include_router(router, prefix="", tags=None)

Router インスタンスを API に統合します。

**パラメータ:**

- `router` (Router): 統合する Router インスタンス
- `prefix` (str): すべてのルートに追加するプレフィックス
- `tags` (List[str], optional): ルートに付与するタグ

**例:**

```python
from lambapi import Router

# ユーザー関連のルーター
user_router = Router(prefix="/users")

@user_router.get("/")
def list_users():
    return {"users": []}

@user_router.get("/{id}")
def get_user(id: str):
    return {"id": id}

# メインアプリに統合
app.include_router(user_router)
# /users/ と /users/{id} が利用可能になる
```

## ミドルウェア

### add_middleware(middleware)

ミドルウェア関数を追加します。

**パラメータ:**

- `middleware` (Callable): ミドルウェア関数

ミドルウェア関数のシグネチャ:
```python
def middleware(request: Request, response: Any) -> Any:
    # 前処理（任意）
    
    # 後処理
    return response
```

**例:**

```python
def logging_middleware(request, response):
    print(f"{request.method} {request.path}")
    return response

def cors_middleware(request, response):
    if isinstance(response, Response):
        response.headers.update({
            'Access-Control-Allow-Origin': '*'
        })
    return response

app.add_middleware(logging_middleware)
app.add_middleware(cors_middleware)
```

## CORS 設定

### enable_cors(origins="*", methods=None, headers=None, allow_credentials=False, max_age=None, expose_headers=None)

グローバル CORS 設定を有効にします。

**パラメータ:**

- `origins` (Union[str, List[str]]): 許可するオリジン（デフォルト: "*"）
- `methods` (List[str], optional): 許可する HTTP メソッド
- `headers` (List[str], optional): 許可するヘッダー
- `allow_credentials` (bool): 認証情報の送信を許可（デフォルト: False）
- `max_age` (int, optional): プリフライトキャッシュ時間（秒）
- `expose_headers` (List[str], optional): ブラウザに公開するレスポンスヘッダー

**例:**

```python
# 基本的な CORS 設定
app.enable_cors()

# 詳細な CORS 設定
app.enable_cors(
    origins=["https://example.com", "https://app.example.com"],
    methods=["GET", "POST", "PUT", "DELETE"],
    headers=["Content-Type", "Authorization"],
    allow_credentials=True,
    max_age=3600
)
```

## エラーハンドリング

### error_handler(exception_type)

特定の例外タイプに対するカスタムエラーハンドラーを登録します。

**パラメータ:**

- `exception_type` (Type[Exception]): 処理する例外タイプ

**例:**

```python
class BusinessError(Exception):
    def __init__(self, message: str, code: str):
        self.message = message
        self.code = code

@app.error_handler(BusinessError)
def handle_business_error(error, request, context):
    return Response({
        "error": "BUSINESS_ERROR",
        "message": error.message,
        "code": error.code
    }, status_code=422)
```

### default_error_handler(handler_func)

すべての未処理例外に対するデフォルトエラーハンドラーを設定します。

**例:**

```python
@app.default_error_handler
def handle_unknown_error(error, request, context):
    return Response({
        "error": "INTERNAL_ERROR",
        "message": "An unexpected error occurred",
        "request_id": context.aws_request_id
    }, status_code=500)
```

## リクエスト処理

### handle_request()

メインのリクエスト処理メソッド。Lambda ハンドラーから呼び出されます。

**戻り値:**

Dict[str, Any]: Lambda レスポンス形式の辞書

**例:**

```python
def lambda_handler(event, context):
    app = API(event, context)
    
    @app.get("/")
    def hello():
        return {"message": "Hello!"}
    
    return app.handle_request()
```

## バリデーション

### リクエストバリデーション

`request_format` パラメータを使用してリクエストボディを自動検証できます：

```python
from dataclasses import dataclass

@dataclass
class CreateUserRequest:
    name: str
    email: str
    age: int = 0

@app.post("/users", request_format=CreateUserRequest)
def create_user(request: CreateUserRequest):
    # request は自動的に CreateUserRequest インスタンスに変換される
    return {
        "message": f"User {request.name} created",
        "email": request.email
    }
```

### レスポンスバリデーション

`response_format` パラメータを使用してレスポンスを自動検証できます：

```python
@dataclass
class UserResponse:
    id: str
    name: str
    email: str

@app.get("/users/{id}", response_format=UserResponse)
def get_user(id: str) -> UserResponse:
    # 戻り値は UserResponse として検証される
    return {
        "id": id,
        "name": f"User {id}",
        "email": f"user{id}@example.com"
    }
```

## パラメータ注入

lambapi は関数シグネチャを解析して、自動的にパラメータを注入します：

### パスパラメータ

```python
@app.get("/users/{user_id}/posts/{post_id}")
def get_post(user_id: str, post_id: str):
    return {"user_id": user_id, "post_id": post_id}
```

### クエリパラメータ

```python
@app.get("/items")
def get_items(limit: int = 10, offset: int = 0, active: bool = True):
    return {
        "limit": limit,     # 自動的に int に変換
        "offset": offset,   # 自動的に int に変換
        "active": active    # 自動的に bool に変換
    }
```

### 型変換

| 型注釈 | 変換動作 |
|--------|----------|
| `str` | そのまま文字列 |
| `int` | `int()` で変換、失敗時は 0 |
| `float` | `float()` で変換、失敗時は 0.0 |
| `bool` | `'true'`, `'1'`, `'yes'`, `'on'` を True として認識 |

### Request オブジェクトの使用

従来の方式で Request オブジェクトを直接使用することも可能です：

```python
@app.post("/upload")
def upload_file(request):
    # 全リクエスト情報にアクセス
    content_type = request.headers.get("content-type")
    body = request.body
    method = request.method
    path = request.path
    
    return {"uploaded": True}
```

## 高度な使用例

### 条件付きルート

```python
@app.get("/admin/users")
def admin_users(request):
    # 認証チェック
    auth_header = request.headers.get("authorization")
    if not auth_header:
        raise AuthenticationError("Authentication required")
    
    return {"users": ["admin_user1", "admin_user2"]}
```

### カスタムレスポンス

```python
from lambapi import Response

@app.get("/download")
def download_file():
    return Response(
        "file content",
        status_code=200,
        headers={
            "Content-Type": "application/octet-stream",
            "Content-Disposition": "attachment; filename=file.txt"
        }
    )
```

### 非同期処理（シミュレート）

```python
import time

@app.post("/process")
def start_processing(request):
    # 非同期処理のシミュレート
    task_id = f"task_{int(time.time())}"
    
    return Response(
        {"task_id": task_id, "status": "processing"},
        status_code=202
    )
```

## 関連項目

- [Router](router.md) - ルーターによるエンドポイントのグループ化
- [Request](request.md) - リクエストオブジェクトの詳細
- [Response](response.md) - レスポンスオブジェクトの詳細
- [Exceptions](exceptions.md) - エラーハンドリングと例外クラス