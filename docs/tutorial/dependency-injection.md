# 依存性注入（Dependency Injection）

lambapi では、FastAPI 風の依存性注入システムを提供しており、クエリパラメータ、パスパラメータ、リクエストボディ、認証ユーザー情報を型安全に取得できます。

## 基本的な使い方

### クエリパラメータ

```python
from lambapi import API, Query

def create_app(event, context):
    app = API(event, context)
    
    @app.get("/search")
    def search_items(
        query: str = Query(..., description="検索クエリ"),
        limit: int = Query(10, ge=1, le=100, description="結果の上限数"),
        offset: int = Query(0, ge=0, description="オフセット")
    ):
        return {
            "query": query,
            "limit": limit,
            "offset": offset,
            "results": f"{limit}件の結果（{offset}件目から）"
        }
    
    return app
```

### パスパラメータ

```python
from lambapi import API, Path

def create_app(event, context):
    app = API(event, context)
    
    @app.get("/users/{user_id}/posts/{post_id}")
    def get_user_post(
        user_id: str = Path(..., description="ユーザー ID"),
        post_id: int = Path(..., gt=0, description="投稿 ID")
    ):
        return {
            "user_id": user_id,
            "post_id": post_id,
            "post": f"ユーザー {user_id} の投稿 {post_id}"
        }
    
    return app
```

### リクエストボディ

```python
from lambapi import API, Body
from dataclasses import dataclass
from typing import Optional

@dataclass
class CreateUserRequest:
    name: str
    email: str
    age: Optional[int] = None

def create_app(event, context):
    app = API(event, context)
    
    @app.post("/users")
    def create_user(
        user_data: CreateUserRequest = Body(..., description="ユーザー作成データ")
    ):
        return {
            "message": "ユーザーが作成されました",
            "user": {
                "name": user_data.name,
                "email": user_data.email,
                "age": user_data.age
            }
        }
    
    return app
```

### 認証ユーザー情報

```python
from lambapi import API, Authenticated, DynamoDBAuth, BaseUser

class CustomUser(BaseUser):
    def __init__(self, id: str = None, password: str = None):
        super().__init__(id, password)
        self.role = "user"  # デフォルトロール

def create_app(event, context):
    app = API(event, context)
    auth = DynamoDBAuth(CustomUser, secret_key="your-secret-key")
    
    @app.post("/profile")
    @auth.require_role("user")
    def update_profile(
        user: CustomUser = Authenticated(..., description="認証されたユーザー"),
        name: str = Query(..., description="新しい名前")
    ):
        return {
            "message": f"ユーザー {user.id} のプロフィールを更新しました",
            "new_name": name
        }
    
    return app
```

## 複合的な使用例

すべての依存性注入機能を組み合わせた例：

```python
from lambapi import API, Query, Path, Body, Authenticated, DynamoDBAuth, BaseUser
from dataclasses import dataclass
from typing import Optional

@dataclass
class UpdatePostRequest:
    title: str
    content: str
    published: bool = False

class CustomUser(BaseUser):
    def __init__(self, id: str = None, password: str = None):
        super().__init__(id, password)
        self.role = "user"

def create_app(event, context):
    app = API(event, context)
    auth = DynamoDBAuth(CustomUser, secret_key="your-secret-key")
    
    @app.put("/users/{user_id}/posts/{post_id}")
    @auth.require_role(["admin", "moderator"])
    def update_user_post(
        # 認証ユーザー
        user: CustomUser = Authenticated(..., description="認証されたユーザー"),
        
        # パスパラメータ
        user_id: str = Path(..., description="対象ユーザー ID"),
        post_id: int = Path(..., gt=0, description="投稿 ID"),
        
        # クエリパラメータ
        notify: bool = Query(True, description="更新通知を送信するか"),
        
        # リクエストボディ
        post_data: UpdatePostRequest = Body(..., description="投稿更新データ")
    ):
        return {
            "message": f"管理者 {user.id} が投稿 {post_id} を更新しました",
            "target_user_id": user_id,
            "post_id": post_id,
            "title": post_data.title,
            "published": post_data.published,
            "notification_sent": notify
        }
    
    return app
```

## バリデーション機能

各依存性注入には豊富なバリデーション機能が含まれています：

### 数値バリデーション

```python
@app.get("/products")
def get_products(
    price_min: float = Query(0, ge=0, description="最小価格"),
    price_max: float = Query(1000000, le=1000000, description="最大価格"),
    rating: int = Query(5, gt=0, le=5, description="評価")
):
    return {"price_range": [price_min, price_max], "rating": rating}
```

### 文字列バリデーション

```python
@app.get("/search")
def search_products(
    query: str = Query(..., min_length=1, max_length=100, description="検索クエリ"),
    category: str = Query("all", regex=r"^(electronics|books|clothing|all)$", description="カテゴリー")
):
    return {"query": query, "category": category}
```

## エラーハンドリング

依存性注入でバリデーションエラーが発生した場合、適切なエラーレスポンスが自動的に返されます：

```python
# クエリパラメータが不正な場合
# GET /products?rating=10  (rating は 1-5 の範囲)
# -> 400 Bad Request: "query parameter 'rating' は 5 以下である必要があります"

# 必須パラメータが不足した場合  
# POST /users  (body が空)
# -> 400 Bad Request: "必須フィールド 'name' が不足しています"
```

## 従来システムとの互換性

新しい依存性注入システムは既存コードと完全に互換性があります：

```python
# 従来の書き方（引き続きサポート）
@app.get("/legacy")
def legacy_handler(request):
    query_param = request.query_params.get("q", "default")
    return {"query": query_param}

# 新しい書き方
@app.get("/modern") 
def modern_handler(q: str = Query("default", description="クエリパラメータ")):
    return {"query": q}
```

両方のスタイルを同じアプリケーション内で混在させることも可能です。

## パフォーマンス

依存性注入システムは高いパフォーマンスを実現するため、以下の最適化を行っています：

- 関数シグネチャの事前キャッシュ
- 型変換関数のキャッシュ
- 依存性解決結果のキャッシュ
- Lambda コールドスタートの最小化

これにより、従来システムとほぼ同等のパフォーマンスを維持しています。