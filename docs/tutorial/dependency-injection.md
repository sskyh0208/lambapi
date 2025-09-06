# 依存性注入（Dependency Injection）

lambapi では、FastAPI 風の依存性注入システムを提供しており、クエリパラメータ、パスパラメータ、リクエストボディ、認証ユーザー情報を型安全に取得できます。

## 🎯 依存性注入とは？

従来の Web フレームワークでは、リクエストデータを手動で取得・変換・バリデーションする必要がありました：

```python
# 従来の方法 ❌ 
def get_products(request):
    # 手動でパラメータ取得
    limit = request.query_params.get('limit', '10')
    try:
        limit = int(limit)
        if limit <= 0 or limit > 100:
            raise ValueError("Invalid limit")
    except ValueError:
        return {"error": "Invalid limit parameter"}
    
    # ...その他のパラメータも同様に処理
```

lambapi の依存性注入なら、これが一行で済みます：

```python
# lambapi の方法 ✅
def get_products(limit: int = Query(10, ge=1, le=100)):
    # limit は自動的に int に変換され、1-100 の範囲でバリデーション済み
    return {"products": [], "limit": limit}
```

## 🚀 メリット

- **型安全**: 型ヒントにより、IDE の補完とエラー検出が可能
- **自動バリデーション**: 不正な値は自動的にエラーレスポンスを返す
- **コード削減**: 手動のパラメータ処理が不要
- **テスト容易性**: 関数の引数として直接テスト値を渡せる
- **ドキュメント化**: description により自動的に API 仕様が明確になる

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

## 💡 実践的な使用例

実際の Web アプリケーションでよくある機能を依存性注入で実装してみましょう。

### 商品検索 API

```python
from lambapi import API, Query, Path, create_lambda_handler
from typing import Optional, List

def create_app(event, context):
    app = API(event, context)
    
    @app.get("/products/search")
    def search_products(
        # 検索条件
        q: str = Query(..., min_length=1, max_length=100, description="検索キーワード"),
        category: str = Query("all", description="商品カテゴリ"),
        
        # 価格フィルタ
        min_price: float = Query(0, ge=0, description="最低価格"),
        max_price: float = Query(999999, ge=0, description="最高価格"),
        
        # ソート・ページング
        sort_by: str = Query("relevance", regex=r"^(relevance|price|rating|newest)$", description="ソート順"),
        page: int = Query(1, ge=1, description="ページ番号"),
        per_page: int = Query(20, ge=1, le=100, description="1 ページあたりの件数")
    ):
        """商品検索 - 複数の条件で絞り込み可能"""
        
        # すべてのパラメータは既にバリデーション済み
        results = {
            "query": q,
            "filters": {
                "category": category,
                "price_range": {"min": min_price, "max": max_price}
            },
            "sort": sort_by,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total_pages": 10,  # 実際は DB から取得
                "total_count": 200
            },
            "products": [
                {"id": i, "name": f"Product {i}", "price": min_price + i * 10}
                for i in range(1, per_page + 1)
            ]
        }
        
        return results
    
    return app
```

### ユーザー管理 API

```python
from lambapi import API, Query, Path, Body, create_lambda_handler
from dataclasses import dataclass
from typing import Optional

@dataclass
class UserCreateRequest:
    username: str
    email: str
    full_name: str
    age: Optional[int] = None

@dataclass  
class UserUpdateRequest:
    full_name: Optional[str] = None
    age: Optional[int] = None

def create_app(event, context):
    app = API(event, context)
    
    @app.post("/users")
    def create_user(user_data: UserCreateRequest = Body(..., description="新規ユーザー情報")):
        """ユーザー作成"""
        # dataclass の恩恵で型安全にアクセス
        new_user = {
            "id": "generated-uuid",
            "username": user_data.username,
            "email": user_data.email,
            "full_name": user_data.full_name,
            "age": user_data.age,
            "created_at": "2024-01-01T00:00:00Z"
        }
        
        return {"message": "ユーザーを作成しました", "user": new_user}
    
    @app.get("/users/{user_id}")
    def get_user(
        user_id: str = Path(..., description="ユーザー ID"),
        include_stats: bool = Query(False, description="統計情報を含めるか")
    ):
        """ユーザー詳細取得"""
        user = {
            "id": user_id,
            "username": f"user_{user_id}",
            "email": f"user_{user_id}@example.com",
            "full_name": f"User {user_id}"
        }
        
        if include_stats:
            user["stats"] = {
                "login_count": 42,
                "last_login": "2024-01-01T12:00:00Z"
            }
        
        return {"user": user}
    
    @app.patch("/users/{user_id}")
    def update_user(
        user_id: str = Path(..., description="ユーザー ID"),
        user_data: UserUpdateRequest = Body(..., description="更新データ"),
        notify: bool = Query(True, description="更新通知を送るか")
    ):
        """ユーザー情報更新"""
        updates = {}
        
        if user_data.full_name is not None:
            updates["full_name"] = user_data.full_name
        if user_data.age is not None:
            updates["age"] = user_data.age
            
        return {
            "message": "ユーザー情報を更新しました",
            "user_id": user_id,
            "updates": updates,
            "notification_sent": notify
        }
    
    return app
```

## エラーハンドリング

依存性注入でバリデーションエラーが発生した場合、適切なエラーレスポンスが自動的に返されます：

```python
# 🚫 クエリパラメータが不正な場合
# GET /products/search?per_page=200  (per_page は 1-100 の範囲)
# -> 400 Bad Request: {
#      "error": "validation_error",
#      "message": "query parameter 'per_page' は 100 以下である必要があります"
#    }

# 🚫 必須パラメータが不足した場合  
# POST /users  (body が空)
# -> 400 Bad Request: {
#      "error": "validation_error", 
#      "message": "必須フィールド 'username' が不足しています"
#    }

# 🚫 型変換エラーの場合
# GET /products/search?page=abc  (page は int 型)
# -> 400 Bad Request: {
#      "error": "validation_error",
#      "message": "query parameter 'page' を int に変換できません"
#    }
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