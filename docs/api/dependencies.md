# Dependencies API リファレンス

lambapi の依存性注入システムで使用する各種クラスと関数の詳細なリファレンスです。

## Query

クエリパラメータを定義するファクトリ関数です。

```python
def Query(
    default: Any = ...,
    alias: Optional[str] = None,
    description: Optional[str] = None,
    gt: Optional[float] = None,
    ge: Optional[float] = None,
    lt: Optional[float] = None,
    le: Optional[float] = None,
    min_length: Optional[int] = None,
    max_length: Optional[int] = None,
    regex: Optional[str] = None,
) -> QueryInfo
```

### パラメータ

- **default** (`Any`): デフォルト値。`...` は必須パラメータを意味する
- **alias** (`Optional[str]`): パラメータ名のエイリアス
- **description** (`Optional[str]`): パラメータの説明文
- **gt** (`Optional[float]`): 値が指定値より大きいこと（>）
- **ge** (`Optional[float]`): 値が指定値以上であること（>=）
- **lt** (`Optional[float]`): 値が指定値より小さいこと（<）
- **le** (`Optional[float]`): 値が指定値以下であること（<=）
- **min_length** (`Optional[int]`): 文字列の最小長
- **max_length** (`Optional[int]`): 文字列の最大長
- **regex** (`Optional[str]`): 正規表現パターン

### 使用例

```python
from lambapi import API, Query

@app.get("/search")
def search_items(
    # 必須パラメータ
    query: str = Query(..., description="検索クエリ"),
    
    # デフォルト値付き
    limit: int = Query(10, ge=1, le=100, description="結果の上限数"),
    
    # エイリアス使用
    sort_order: str = Query("asc", alias="sort", regex=r"^(asc|desc)$"),
    
    # 文字列長制限
    category: str = Query("all", min_length=2, max_length=20)
):
    return {"query": query, "limit": limit}
```

## Path

パスパラメータを定義するファクトリ関数です。

```python
def Path(
    default: Any = ...,
    alias: Optional[str] = None,
    description: Optional[str] = None,
    gt: Optional[float] = None,
    ge: Optional[float] = None,
    lt: Optional[float] = None,
    le: Optional[float] = None,
    min_length: Optional[int] = None,
    max_length: Optional[int] = None,
    regex: Optional[str] = None,
) -> PathInfo
```

### パラメータ

`Query` と同じパラメータを受け取ります。パスパラメータは通常必須のため、`default` には `...` を使用することを推奨します。

### 使用例

```python
from lambapi import API, Path

@app.get("/users/{user_id}/posts/{post_id}")
def get_user_post(
    # 文字列パスパラメータ
    user_id: str = Path(..., min_length=1, description="ユーザー ID"),
    
    # 数値パスパラメータ（バリデーション付き）
    post_id: int = Path(..., gt=0, description="投稿 ID"),
    
    # UUID 形式のパスパラメータ
    session_id: str = Path(
        ..., 
        regex=r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
        description="セッション ID（UUID 形式）"
    )
):
    return {"user_id": user_id, "post_id": post_id}
```

## Body

リクエストボディを定義するファクトリ関数です。

```python
def Body(
    default: Any = ...,
    alias: Optional[str] = None,
    description: Optional[str] = None,
) -> BodyInfo
```

### パラメータ

- **default** (`Any`): デフォルト値。`...` は必須を意味する
- **alias** (`Optional[str]`): パラメータ名のエイリアス
- **description** (`Optional[str]`): パラメータの説明文

### 使用例

```python
from lambapi import API, Body
from dataclasses import dataclass
from typing import Optional

@dataclass
class CreateUserRequest:
    name: str
    email: str
    age: Optional[int] = None

@dataclass 
class UpdatePostRequest:
    title: str
    content: str
    published: bool = False

@app.post("/users")
def create_user(
    # dataclass を使用したボディ
    user_data: CreateUserRequest = Body(..., description="ユーザー作成データ")
):
    return {"message": f"ユーザー {user_data.name} を作成しました"}

@app.put("/posts/{post_id}")
def update_post(
    post_id: int = Path(..., gt=0),
    # リクエストボディ
    post_data: UpdatePostRequest = Body(..., description="投稿更新データ"),
    # 辞書型のボディも可能
    metadata: dict = Body({}, description="メタデータ")
):
    return {"post_id": post_id, "title": post_data.title}
```

## Authenticated

認証されたユーザー情報を注入するファクトリ関数です。

```python
def Authenticated(
    default: Any = ...,
    alias: Optional[str] = None,
    description: Optional[str] = None,
) -> AuthenticatedInfo
```

### パラメータ

- **default** (`Any`): デフォルト値。認証は通常必須のため `...` を使用
- **alias** (`Optional[str]`): パラメータ名のエイリアス
- **description** (`Optional[str]`): パラメータの説明文

### 使用例

```python
from lambapi import API, Authenticated, DynamoDBAuth, BaseUser

class CustomUser(BaseUser):
    def __init__(self, id: str = None, password: str = None):
        super().__init__(id, password)
        self.role = "user"

def create_app(event, context):
    app = API(event, context)
    auth = DynamoDBAuth(CustomUser, secret_key="your-secret-key")
    
    @app.get("/profile")
    @auth.require_role("user")
    def get_profile(
        # 認証されたユーザー情報を自動注入
        user: CustomUser = Authenticated(..., description="認証されたユーザー")
    ):
        return {
            "user_id": user.id,
            "role": user.role,
            "created_at": user.created_at.isoformat() if user.created_at else None
        }
    
    @app.post("/admin/users") 
    @auth.require_role("admin")
    def create_user_as_admin(
        admin_user: CustomUser = Authenticated(..., description="管理者ユーザー"),
        user_data: CreateUserRequest = Body(..., description="作成するユーザーデータ")
    ):
        return {
            "message": f"管理者 {admin_user.id} がユーザーを作成しました",
            "new_user": user_data.name
        }
    
    return app
```

## バリデーションエラー

依存性注入でバリデーションエラーが発生した場合、`ValidationError` 例外が発生し、適切な HTTP エラーレスポンスに変換されます。

### エラーの種類

#### 必須パラメータエラー
```python
# クエリパラメータが不足
# GET /search （query パラメータなし）
# -> 400 Bad Request: "必須のクエリパラメータ 'query' が不足しています"
```

#### 型変換エラー
```python  
# 数値型に文字列が渡された場合
# GET /posts/abc （post_id は数値である必要）
# -> 400 Bad Request: "path parameter 'post_id': 'abc' を int に変換できません"
```

#### 範囲制限エラー
```python
# 範囲外の値が渡された場合  
# GET /search?limit=200 （limit の上限は 100）
# -> 400 Bad Request: "query parameter 'limit' は 100 以下である必要があります"
```

#### 文字列長エラー
```python
# 文字列の長さが制限を超えた場合
# GET /search?query=a （最小長が 2 文字）
# -> 400 Bad Request: "query parameter 'query' は最低 2 文字必要です"
```

#### 正規表現エラー
```python
# パターンにマッチしない場合
# GET /search?sort=invalid （sort は "asc" または "desc" のみ）
# -> 400 Bad Request: "query parameter 'sort' は指定されたパターンにマッチしません"
```

## 内部クラス

### FieldInfo

依存性注入パラメータのメタデータを保持するベースクラス。

```python
class FieldInfo:
    def __init__(
        self,
        default: Any = ...,
        alias: Optional[str] = None,
        description: Optional[str] = None,
        gt: Optional[float] = None,
        ge: Optional[float] = None,
        lt: Optional[float] = None,
        le: Optional[float] = None,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        regex: Optional[str] = None,
    ): ...
```

### 特化クラス

- **QueryInfo**: クエリパラメータ用（`source = "query"`）
- **PathInfo**: パスパラメータ用（`source = "path"`）
- **BodyInfo**: リクエストボディ用（`source = "body"`）
- **AuthenticatedInfo**: 認証ユーザー用（`source = "authenticated"`）

## 💡 実用的なパターン集

### RESTful API の標準パターン

```python
from lambapi import API, Query, Path, Body, create_lambda_handler
from dataclasses import dataclass
from typing import Optional, List

@dataclass
class Product:
    id: Optional[str] = None
    name: str
    price: float
    category: str
    in_stock: bool = True

def create_app(event, context):
    app = API(event, context)
    
    # コレクション取得（検索・フィルタ・ページング）
    @app.get("/products")
    def list_products(
        # 検索とフィルタ
        q: str = Query("", description="商品名検索"),
        category: str = Query("", description="カテゴリフィルタ"),
        in_stock: bool = Query(True, description="在庫有無フィルタ"),
        
        # 価格範囲
        min_price: float = Query(0, ge=0, description="最低価格"),
        max_price: float = Query(999999, ge=0, description="最高価格"),
        
        # ソート
        sort_by: str = Query("name", regex=r"^(name|price|created_at)$", description="ソートフィールド"),
        sort_order: str = Query("asc", regex=r"^(asc|desc)$", description="ソート順"),
        
        # ページング
        page: int = Query(1, ge=1, description="ページ番号"),
        per_page: int = Query(20, ge=1, le=100, description="1 ページあたりの件数")
    ):
        """商品一覧の取得"""
        return {
            "products": [],
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": 0,
                "total_pages": 0
            },
            "filters": {
                "q": q,
                "category": category,
                "price_range": [min_price, max_price]
            }
        }
    
    # 単一リソース取得
    @app.get("/products/{product_id}")
    def get_product(
        product_id: str = Path(..., description="商品 ID"),
        include_reviews: bool = Query(False, description="レビューを含めるか")
    ):
        """商品詳細の取得"""
        product = {"id": product_id, "name": f"Product {product_id}"}
        
        if include_reviews:
            product["reviews"] = [
                {"rating": 5, "comment": "Great product!"}
            ]
            
        return {"product": product}
    
    # 作成
    @app.post("/products")
    def create_product(product: Product = Body(..., description="作成する商品データ")):
        """商品の作成"""
        return {
            "message": "商品を作成しました",
            "product": {
                "id": "generated-id",
                "name": product.name,
                "price": product.price,
                "category": product.category
            }
        }
    
    # 更新
    @app.put("/products/{product_id}")
    def update_product(
        product_id: str = Path(..., description="更新対象の商品 ID"),
        product: Product = Body(..., description="更新データ")
    ):
        """商品の完全更新"""
        return {
            "message": f"商品 {product_id} を更新しました",
            "product": {"id": product_id, **product.__dict__}
        }
    
    # 部分更新
    @app.patch("/products/{product_id}")
    def patch_product(
        product_id: str = Path(..., description="更新対象の商品 ID"),
        updates: dict = Body(..., description="部分更新データ")
    ):
        """商品の部分更新"""
        return {
            "message": f"商品 {product_id} の一部を更新しました",
            "updated_fields": list(updates.keys())
        }
    
    # 削除
    @app.delete("/products/{product_id}")
    def delete_product(
        product_id: str = Path(..., description="削除対象の商品 ID"),
        soft_delete: bool = Query(True, description="論理削除するか")
    ):
        """商品の削除"""
        action = "論理削除" if soft_delete else "物理削除"
        return {"message": f"商品 {product_id} を{action}しました"}
    
    return app
```

### 入力バリデーションのベストプラクティス

```python
from lambapi import API, Query, Path, Body
from dataclasses import dataclass, field
from typing import Optional, List
import re

@dataclass
class UserRegistration:
    username: str = field(metadata={"min_length": 3, "max_length": 20})
    email: str = field(metadata={"pattern": r"^[\w\.-]+@[\w\.-]+\.\w+$"})
    password: str = field(metadata={"min_length": 8})
    age: Optional[int] = field(default=None, metadata={"ge": 13, "le": 120})

@app.get("/users/search")
def search_users(
    # 複数の検索条件を組み合わせ
    username: str = Query("", min_length=0, max_length=20, description="ユーザー名で検索"),
    email_domain: str = Query("", regex=r"^[\w\.-]+$", description="メールドメインで検索"),
    
    # 年齢範囲
    min_age: int = Query(0, ge=0, le=120, description="最小年齢"),
    max_age: int = Query(120, ge=0, le=120, description="最大年齢"),
    
    # アクティビティフィルタ
    is_active: Optional[bool] = Query(None, description="アクティブユーザーのみ（null は全て）"),
    last_login_days: int = Query(30, ge=1, le=365, description="最終ログイン日数以内"),
    
    # 地域フィルタ
    country: str = Query("", regex=r"^[A-Z]{0,2}$", description="国コード（ISO 3166-1）"),
    timezone: str = Query("", description="タイムゾーン"),
    
    # 結果制御
    fields: str = Query("basic", regex=r"^(basic|full|minimal)$", description="返却フィールド"),
    sort: str = Query("username", regex=r"^(username|created_at|last_login)$"),
    order: str = Query("asc", regex=r"^(asc|desc)$"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """高度なユーザー検索機能"""
    return {
        "users": [],
        "search_criteria": {
            "username": username,
            "age_range": [min_age, max_age],
            "location": {"country": country, "timezone": timezone}
        },
        "pagination": {"limit": limit, "offset": offset}
    }
```

## ユーティリティ関数

### get_function_dependencies

```python
def get_function_dependencies(func: callable) -> Dict[str, FieldInfo]:
    """関数から全ての依存性情報を抽出する"""
```

関数の依存性注入パラメータを解析し、パラメータ名をキーとした依存性情報の辞書を返します。

### is_dependency_parameter

```python
def is_dependency_parameter(param: inspect.Parameter) -> bool:
    """パラメータが依存性注入パラメータかどうかを判定する"""
```

指定されたパラメータが依存性注入パラメータかどうかを判定します。

## パフォーマンス考慮事項

- 関数シグネチャはキャッシュされるため、同じ関数の繰り返し呼び出しは高速です
- 型変換関数もキャッシュされ、再利用されます
- バリデーション結果は必要に応じてキャッシュされます
- 依存性解決は Lambda のコールドスタートを最小化するよう最適化されています

## 制限事項

- 依存性注入パラメータと従来のパラメータ（引数名による自動マッピング）を同一関数内で混在させることは推奨されません
- ネストした依存性注入（依存性の中に別の依存性を含む）は現在サポートされていません
- `Body` パラメータは 1 つの関数につき 1 つまでです