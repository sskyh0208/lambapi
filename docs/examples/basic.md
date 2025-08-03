# 基本例

lambapi の基本的な使用例を紹介します。これらの例は実際のコードをコピー&ペーストして試すことができます。

## Hello World

最もシンプルな例から始めましょう。

```python title="hello_world.py"
from lambapi import API, create_lambda_handler

def create_app(event, context):
    app = API(event, context)
    
    @app.get("/")
    def hello():
        return {"message": "Hello, World!"}
    
    return app

lambda_handler = create_lambda_handler(create_app)
```

## パスパラメータ

URL の一部をパラメータとして受け取る例です。

```python title="path_parameters.py"
from lambapi import API, create_lambda_handler

def create_app(event, context):
    app = API(event, context)
    
    @app.get("/hello/{name}")
    def hello_name(name: str):
        return {"message": f"Hello, {name}!"}
    
    @app.get("/users/{user_id}")
    def get_user(user_id: str):
        return {
            "user_id": user_id,
            "name": f"User {user_id}",
            "profile_url": f"/users/{user_id}/profile"
        }
    
    @app.get("/users/{user_id}/posts/{post_id}")
    def get_user_post(user_id: str, post_id: str):
        return {
            "user_id": user_id,
            "post_id": post_id,
            "title": f"Post {post_id} by User {user_id}"
        }
    
    return app

lambda_handler = create_lambda_handler(create_app)
```

## クエリパラメータ

URL のクエリパラメータを関数引数として受け取る例です。

```python title="query_parameters.py"
from lambapi import API, create_lambda_handler

def create_app(event, context):
    app = API(event, context)
    
    @app.get("/search")
    def search(q: str = "", limit: int = 10, sort: str = "relevance"):
        return {
            "query": q,
            "limit": limit,
            "sort": sort,
            "results": [f"result-{i}" for i in range(1, min(limit, 5) + 1)]
        }
    
    @app.get("/products")
    def get_products(
        category: str = "all",
        min_price: float = 0.0,
        max_price: float = 1000.0,
        in_stock: bool = True,
        page: int = 1
    ):
        return {
            "category": category,
            "price_range": {"min": min_price, "max": max_price},
            "in_stock_only": in_stock,
            "page": page,
            "products": []
        }
    
    return app

lambda_handler = create_lambda_handler(create_app)
```

## HTTP メソッド

すべての HTTP メソッドの使用例です。

```python title="http_methods.py"
from lambapi import API, Response, create_lambda_handler

def create_app(event, context):
    app = API(event, context)
    
    # データストア（実際にはデータベースを使用）
    items = {}
    
    @app.get("/items")
    def list_items():
        return {"items": list(items.values())}
    
    @app.get("/items/{item_id}")
    def get_item(item_id: str):
        if item_id not in items:
            return Response({"error": "Item not found"}, status_code=404)
        return {"item": items[item_id]}
    
    @app.post("/items")
    def create_item(request):
        data = request.json()
        item_id = str(len(items) + 1)
        
        item = {
            "id": item_id,
            "name": data.get("name"),
            "description": data.get("description"),
            "price": data.get("price")
        }
        
        items[item_id] = item
        
        return Response(
            {"message": "Item created", "item": item},
            status_code=201
        )
    
    @app.put("/items/{item_id}")
    def update_item(item_id: str, request):
        if item_id not in items:
            return Response({"error": "Item not found"}, status_code=404)
        
        data = request.json()
        items[item_id].update(data)
        
        return {"message": "Item updated", "item": items[item_id]}
    
    @app.delete("/items/{item_id}")
    def delete_item(item_id: str):
        if item_id not in items:
            return Response({"error": "Item not found"}, status_code=404)
        
        deleted_item = items.pop(item_id)
        return {"message": "Item deleted", "deleted_item": deleted_item}
    
    @app.patch("/items/{item_id}")
    def patch_item(item_id: str, request):
        if item_id not in items:
            return Response({"error": "Item not found"}, status_code=404)
        
        data = request.json()
        
        # PATCH は部分更新
        for key, value in data.items():
            if key in items[item_id]:
                items[item_id][key] = value
        
        return {"message": "Item patched", "item": items[item_id]}
    
    return app

lambda_handler = create_lambda_handler(create_app)
```

## レスポンスのカスタマイズ

さまざまなレスポンス形式の例です。

```python title="custom_responses.py"
from lambapi import API, Response, create_lambda_handler
import json

def create_app(event, context):
    app = API(event, context)
    
    @app.get("/simple")
    def simple_response():
        # 辞書はそのまま JSON になる
        return {"message": "Simple response"}
    
    @app.get("/custom-status")
    def custom_status():
        # カスタムステータスコード
        return Response(
            {"message": "Created successfully"},
            status_code=201
        )
    
    @app.get("/custom-headers")
    def custom_headers():
        # カスタムヘッダー
        return Response(
            {"message": "Response with custom headers"},
            headers={
                "X-Custom-Header": "Custom Value",
                "Cache-Control": "no-cache"
            }
        )
    
    @app.get("/text-response")
    def text_response():
        # テキストレスポンス
        return Response(
            "This is a plain text response",
            headers={"Content-Type": "text/plain"}
        )
    
    @app.get("/xml-response")
    def xml_response():
        xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<response>
    <message>This is XML response</message>
    <status>success</status>
</response>'''
        
        return Response(
            xml_content,
            headers={"Content-Type": "application/xml"}
        )
    
    @app.get("/download")
    def download_file():
        # ファイルダウンロード
        file_content = "Hello, this is a downloadable file!"
        
        return Response(
            file_content,
            headers={
                "Content-Type": "application/octet-stream",
                "Content-Disposition": "attachment; filename=sample.txt"
            }
        )
    
    @app.get("/redirect")
    def redirect_response():
        # リダイレクト
        return Response(
            "",
            status_code=302,
            headers={"Location": "https://example.com"}
        )
    
    return app

lambda_handler = create_lambda_handler(create_app)
```

## エラーハンドリング

エラー処理の基本例です。

```python title="error_handling.py"
from lambapi import API, Response, create_lambda_handler
from lambapi.exceptions import ValidationError, NotFoundError

def create_app(event, context):
    app = API(event, context)
    
    @app.get("/error-demo/{error_type}")
    def error_demo(error_type: str):
        if error_type == "validation":
            raise ValidationError(
                "Invalid input data",
                field="name",
                value="invalid_value"
            )
        elif error_type == "not-found":
            raise NotFoundError("Resource", "123")
        elif error_type == "custom":
            return Response(
                {"error": "CUSTOM_ERROR", "message": "This is a custom error"},
                status_code=422
            )
        elif error_type == "server":
            raise Exception("Simulated server error")
        else:
            return {"message": f"No error for type: {error_type}"}
    
    # カスタムエラーハンドラー
    class BusinessError(Exception):
        def __init__(self, message: str, code: str):
            self.message = message
            self.code = code
    
    @app.error_handler(BusinessError)
    def handle_business_error(error, request, context):
        return Response({
            "error": "BUSINESS_ERROR",
            "message": error.message,
            "code": error.code,
            "request_id": context.aws_request_id
        }, status_code=400)
    
    @app.get("/business-error")
    def trigger_business_error():
        raise BusinessError("Insufficient funds", "INSUFFICIENT_FUNDS")
    
    return app

lambda_handler = create_lambda_handler(create_app)
```

## データバリデーション

データクラスを使用したバリデーションの例です。

```python title="validation.py"
from lambapi import API, Response, create_lambda_handler
from dataclasses import dataclass
from typing import Optional

@dataclass
class CreateUserRequest:
    name: str
    email: str
    age: int
    bio: Optional[str] = None

@dataclass
class UserResponse:
    id: str
    name: str
    email: str
    age: int
    bio: Optional[str] = None

def create_app(event, context):
    app = API(event, context)
    
    users = {}
    
    @app.post("/users", request_format=CreateUserRequest, response_format=UserResponse)
    def create_user(user_data: CreateUserRequest):
        # user_data は自動的に CreateUserRequest インスタンスに変換される
        user_id = str(len(users) + 1)
        
        user = {
            "id": user_id,
            "name": user_data.name,
            "email": user_data.email,
            "age": user_data.age,
            "bio": user_data.bio
        }
        
        users[user_id] = user
        
        # 戻り値は UserResponse として検証される
        return user
    
    @app.get("/users/{user_id}", response_format=UserResponse)
    def get_user(user_id: str):
        if user_id not in users:
            return Response({"error": "User not found"}, status_code=404)
        
        return users[user_id]
    
    return app

lambda_handler = create_lambda_handler(create_app)
```

## ミドルウェア

ミドルウェアを使用した横断的関心事の処理例です。

```python title="middleware.py"
from lambapi import API, Response, create_lambda_handler
import time
import json

def create_app(event, context):
    app = API(event, context)
    
    # ログミドルウェア
    def logging_middleware(request, response):
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {request.method} {request.path}")
        
        # レスポンスのログ
        if isinstance(response, Response):
            print(f"Response: {response.status_code}")
        
        return response
    
    # CORS ミドルウェア
    def cors_middleware(request, response):
        if isinstance(response, Response):
            response.headers.update({
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type, Authorization'
            })
        return response
    
    # セキュリティヘッダーミドルウェア
    def security_headers_middleware(request, response):
        if isinstance(response, Response):
            response.headers.update({
                'X-Content-Type-Options': 'nosniff',
                'X-Frame-Options': 'DENY',
                'X-XSS-Protection': '1; mode=block'
            })
        return response
    
    # ミドルウェアを追加
    app.add_middleware(logging_middleware)
    app.add_middleware(cors_middleware)
    app.add_middleware(security_headers_middleware)
    
    @app.get("/")
    def hello():
        return {"message": "Hello with middleware!"}
    
    @app.get("/protected")
    def protected_endpoint():
        return {"message": "This endpoint has security headers"}
    
    return app

lambda_handler = create_lambda_handler(create_app)
```

## ローカルでのテスト方法

### CLI コマンドでのテスト

```bash
# ファイルを保存してローカルサーバーで起動
lambapi serve hello_world

# テスト
curl http://localhost:8000/
curl http://localhost:8000/hello/world
curl "http://localhost:8000/search?q=test&limit=5"

# POST リクエスト
curl -X POST http://localhost:8000/items \
  -H "Content-Type: application/json" \
  -d '{"name":"Test Item","price":100}'
```

### Python での直接テスト

```python title="test_examples.py"
import json

def test_api(lambda_handler, method, path, body=None, query_params=None):
    """API をテストするヘルパー関数"""
    event = {
        'httpMethod': method,
        'path': path,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps(body) if body else None,
        'queryStringParameters': query_params
    }
    
    context = type('Context', (), {'aws_request_id': 'test-123'})()
    
    result = lambda_handler(event, context)
    
    print(f"{method} {path}")
    print(f"Status: {result['statusCode']}")
    print(f"Response: {result['body']}")
    print("-" * 50)
    
    return result

# 使用例
if __name__ == "__main__":
    from path_parameters import lambda_handler as path_handler
    from query_parameters import lambda_handler as query_handler
    
    # パスパラメータのテスト
    test_api(path_handler, 'GET', '/hello/world')
    test_api(path_handler, 'GET', '/users/123')
    
    # クエリパラメータのテスト
    test_api(query_handler, 'GET', '/search', query_params={'q': 'python', 'limit': '5'})
    test_api(query_handler, 'GET', '/products', query_params={
        'category': 'electronics',
        'min_price': '100',
        'in_stock': 'true'
    })
```

## SAM でのローカル実行

SAM Local を使用してローカルでテストする場合の設定例です。

```yaml title="template.yaml"
AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31

Resources:
  lambapiFunction:
    Type: AWS::Serverless::Function
    Properties:
      CodeUri: .
      Handler: hello_world.lambda_handler
      Runtime: python3.13
      Events:
        ApiGateway:
          Type: Api
          Properties:
            Path: /{proxy+}
            Method: ANY
```

```bash
# SAM Local を起動
sam local start-api

# テスト
curl http://localhost:3000/
curl http://localhost:3000/hello/world
curl "http://localhost:3000/search?q=test&limit=5"
```

これらの例を参考に、lambapi の様々な機能を試してみてください。各例は独立しているので、必要な部分だけを選んで使用することも可能です。