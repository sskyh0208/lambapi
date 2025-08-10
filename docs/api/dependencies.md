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