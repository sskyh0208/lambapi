# 依存性注入

FastAPI 風の型安全な依存性注入システムです。クエリパラメータ、パスパラメータ、リクエストボディ、認証情報を自動的に解析・変換・検証します。

## 🎯 メリット

- **型安全**: 型ヒントにより IDE の補完とエラー検出
- **自動バリデーション**: 不正な値は自動的にエラーレスポンス  
- **コード削減**: 手動のパラメータ処理が不要
- **テスト容易性**: 関数の引数として直接テスト値を渡せる

## 📖 基本的な使用方法

### Query（クエリパラメータ）

```python
from lambapi import API, Query

@app.get("/search")
def search(
    q: str = Query(..., description="検索クエリ"),
    limit: int = Query(10, ge=1, le=100, description="結果数"),
    offset: int = Query(0, ge=0, description="オフセット")
):
    return {"query": q, "limit": limit, "offset": offset}

# GET /search?q=python&limit=20&offset=10
```

### Path（パスパラメータ）

```python
from lambapi import API, Path

@app.get("/users/{user_id}/posts/{post_id}")
def get_user_post(
    user_id: str = Path(..., description="ユーザー ID"),
    post_id: int = Path(..., gt=0, description="投稿 ID")
):
    return {"user_id": user_id, "post_id": post_id}

# GET /users/alice/posts/123
```

### Body（リクエストボディ）

```python
from lambapi import API, Body
from pydantic import BaseModel

class CreateUserRequest(BaseModel):
    name: str
    email: str
    age: Optional[int] = None

@app.post("/users")
def create_user(
    user_data: CreateUserRequest = Body(..., description="ユーザー作成データ")
):
    return {"message": f"ユーザー {user_data.name} を作成しました"}

# POST /users {"name": "Alice", "email": "alice@example.com"}
```

### Authenticated（認証ユーザー）

```python
from lambapi import API, Authenticated
from lambapi.auth import DynamoDBAuth

@app.get("/profile")
@auth.require_role("user")
def get_profile(
    user: User = Authenticated(..., description="認証されたユーザー")
):
    return {"user_id": user.id, "name": user.name}
```

## 🔧 バリデーション機能

### 数値バリデーション

```python
@app.get("/products")
def get_products(
    min_price: float = Query(0, ge=0, description="最小価格"),
    max_price: float = Query(1000000, le=1000000, description="最大価格"), 
    rating: int = Query(5, gt=0, le=5, description="評価")
):
    return {"min_price": min_price, "max_price": max_price, "rating": rating}
```

| パラメータ | 説明 |
|------------|------|
| `ge` | 以上（greater equal） |
| `gt` | より大きい（greater than） |
| `le` | 以下（less equal） |
| `lt` | より小さい（less than） |

### 文字列バリデーション

```python
@app.get("/search")
def search(
    query: str = Query(..., min_length=1, max_length=100, description="検索クエリ"),
    category: str = Query("all", regex=r"^(books|electronics|clothing|all)$")
):
    return {"query": query, "category": category}
```

| パラメータ | 説明 |
|------------|------|
| `min_length` | 最小文字数 |
| `max_length` | 最大文字数 |
| `regex` | 正規表現パターン |

### 配列・リストのバリデーション

```python
from typing import List

@app.post("/tags")
def create_tags(
    tags: List[str] = Query([], description="タグリスト"),
    ids: List[int] = Query([], description="ID リスト")
):
    return {"tags": tags, "ids": ids}

# GET /tags?tags=python&tags=web&ids=1&ids=2&ids=3
```

## 🔄 複合的な使用例

全ての依存性注入を組み合わせた例：

```python
from lambapi import API, Query, Path, Body, Authenticated
from pydantic import BaseModel
from typing import Optional

class UpdatePostRequest(BaseModel):
    title: str
    content: str
    published: bool = False

@app.put("/users/{user_id}/posts/{post_id}")
@auth.require_role(["admin", "moderator"])
def update_user_post(
    # 認証ユーザー
    admin: User = Authenticated(..., description="管理者"),
    
    # パスパラメータ
    user_id: str = Path(..., description="対象ユーザー ID"),
    post_id: int = Path(..., gt=0, description="投稿 ID"),
    
    # クエリパラメータ  
    notify: bool = Query(True, description="通知を送信するか"),
    
    # リクエストボディ
    post_data: UpdatePostRequest = Body(..., description="投稿更新データ")
):
    return {
        "message": f"管理者 {admin.id} が投稿 {post_id} を更新しました",
        "user_id": user_id,
        "title": post_data.title,
        "notification_sent": notify
    }
```

## ⚡ パフォーマンス特性

### 関数シグネチャキャッシュ

```python
# 関数シグネチャは起動時にキャッシュされる
@app.get("/cached")
def cached_handler(
    param1: str = Query(...),
    param2: int = Query(default=10)
):
    return {"param1": param1, "param2": param2}
```

### 型変換キャッシュ

```python
# 型変換関数もキャッシュされ高速処理
@app.get("/converted")
def converted_handler(
    user_id: int = Path(...),  # str → int 変換
    active: bool = Query(True)  # str → bool 変換
):
    return {"user_id": user_id, "active": active}
```

## 🚨 エラーハンドリング

### 自動バリデーションエラー

```python
# 不正なリクエスト例
# GET /products?limit=200  (limit は 1-100 の範囲)
# → 400 Bad Request: {"error": "validation_error", "message": "limit は 100 以下である必要があります"}

# POST /users  (body が空)
# → 400 Bad Request: {"error": "validation_error", "message": "必須フィールド 'name' が不足しています"}

# GET /users/abc/posts/0  (post_id は 1以上)
# → 400 Bad Request: {"error": "validation_error", "message": "post_id は 0 より大きい値である必要があります"}
```

### カスタムバリデーション

```python
from lambapi import ValidationError

@app.post("/custom-validation")
def custom_validation(data: dict = Body(...)):
    if data.get("age", 0) < 0:
        raise ValidationError("年齢は0以上である必要があります")
    
    return {"message": "バリデーション成功"}
```

## 🔄 従来システムとの互換性

新しい依存性注入と従来の方式を混在できます：

```python
# 従来の書き方（引き続きサポート）
@app.get("/legacy")
def legacy_handler(request):
    query_param = request.query_params.get("q", "default")
    return {"query": query_param}

# 新しい依存性注入
@app.get("/modern")
def modern_handler(q: str = Query("default", description="クエリパラメータ")):
    return {"query": q}
```

## 📚 実用的な例

### 商品検索 API

```python
@app.get("/products/search")
def search_products(
    # 検索条件
    q: str = Query(..., min_length=1, max_length=100, description="検索キーワード"),
    category: str = Query("all", description="商品カテゴリ"),
    
    # 価格フィルタ
    min_price: float = Query(0, ge=0, description="最低価格"),
    max_price: float = Query(999999, ge=0, description="最高価格"),
    
    # ソート・ページング
    sort_by: str = Query("relevance", regex=r"^(relevance|price|rating|newest)$"),
    page: int = Query(1, ge=1, description="ページ番号"),
    per_page: int = Query(20, ge=1, le=100, description="1ページあたりの件数")
):
    return {
        "query": q,
        "filters": {"category": category, "price_range": [min_price, max_price]},
        "sort": sort_by,
        "pagination": {"page": page, "per_page": per_page},
        "products": []  # 実際の商品データ
    }
```

### ユーザー管理 API

```python
from pydantic import BaseModel, EmailStr
from typing import Optional

class UserCreateRequest(BaseModel):
    username: str
    email: EmailStr
    full_name: str
    age: Optional[int] = None

class UserUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    age: Optional[int] = None

@app.post("/users")
def create_user(user_data: UserCreateRequest = Body(...)):
    return {
        "message": "ユーザーを作成しました",
        "user": {
            "username": user_data.username,
            "email": user_data.email,
            "full_name": user_data.full_name,
            "age": user_data.age
        }
    }

@app.patch("/users/{user_id}")
def update_user(
    user_id: str = Path(..., description="ユーザー ID"),
    user_data: UserUpdateRequest = Body(...),
    notify: bool = Query(True, description="更新通知を送るか")
):
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
```

## 🔧 デバッグとテスト

### テスト用の関数呼び出し

```python
# 依存性注入を使った関数は直接テストできる
def test_search():
    result = search_products(
        q="laptop",
        category="electronics", 
        min_price=500,
        max_price=2000,
        sort_by="price",
        page=1,
        per_page=10
    )
    assert result["query"] == "laptop"
    assert result["filters"]["category"] == "electronics"
```

### デバッグ用パラメータ出力

```python
@app.get("/debug")
def debug_params(
    param1: str = Query("default"),
    param2: int = Query(0),
    param3: bool = Query(False)
):
    return {
        "received_params": {
            "param1": {"value": param1, "type": type(param1).__name__},
            "param2": {"value": param2, "type": type(param2).__name__},
            "param3": {"value": param3, "type": type(param3).__name__}
        }
    }
```