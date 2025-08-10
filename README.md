# lambapi

**モダンな AWS Lambda 用 API フレームワーク**

![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![Version](https://img.shields.io/badge/version-0.2.1-green.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

AWS Lambda で FastAPI 風の直感的でモダンな API を構築できる軽量フレームワーク。アノテーションベースのパラメータ注入、自動バリデーション、認証機能を統合サポート。

## ✨ 主な特徴

- 🚀 **FastAPI 風記法** - アノテーションベースの直感的なパラメータ注入
- 📋 **統合アノテーションシステム** - Body, Path, Query, Header を統一的に処理
- 🔒 **統合認証システム** - CurrentUser, RequireRole, OptionalAuth で認証を簡潔に
- 🔄 **自動バリデーション** - Pydantic モデルとデータクラスの自動バリデーション
- 🎯 **型安全性** - 完全な型ヒント対応と自動型変換
- 🌐 **CORS サポート** - プリフライトリクエストの自動処理
- 🛡️ **構造化エラーハンドリング** - 本番運用に適した統一エラーレスポンス
- 📦 **軽量** - シンプルな API で最小限の学習コスト

## 🚀 クイックスタート

### インストール

```bash
pip install lambapi
```

### 基本的な使用例

```python
from lambapi import API, create_lambda_handler
from lambapi.annotations import Body, Path, Query, Header
from dataclasses import dataclass
from typing import Optional

@dataclass
class User:
    name: str
    email: str
    age: Optional[int] = None

def create_app(event, context):
    app = API(event, context)

    @app.get("/")
    def hello():
        return {"message": "Hello, lambapi!"}

    @app.get("/users/{user_id}")
    def get_user(user_id: int = Path()):
        return {"user_id": user_id, "name": f"User {user_id}"}

    @app.post("/users")
    def create_user(user: User = Body()):
        return {"message": "Created", "user": user}

    @app.get("/search")
    def search(
        q: str = Query(),
        limit: int = Query(default=10),
        sort: str = Query(default="id")
    ):
        return {"query": q, "limit": limit, "sort": sort, "results": []}

    return app

lambda_handler = create_lambda_handler(create_app)
```

### FastAPI 風の自動推論

```python
from lambapi import API
from dataclasses import dataclass

@dataclass
class CreateUserRequest:
    name: str
    email: str

def create_app(event, context):
    app = API(event, context)

    # 自動推論：user パラメータは自動的に Body として扱われる
    @app.post("/users")
    def create_user(user: CreateUserRequest):
        return {"id": f"user_{hash(user.email)}", "name": user.name}

    # パスパラメータも自動推論
    @app.get("/users/{user_id}")
    def get_user(user_id: int):  # 自動的に Path パラメータとして扱われる
        return {"user_id": user_id}

    # クエリパラメータも自動推論
    @app.get("/users")
    def list_users(limit: int = 10, offset: int = 0):
        return {"limit": limit, "offset": offset}

    return app
```

### 認証システムの統合

```python
from lambapi import API
from lambapi.annotations import CurrentUser, RequireRole, OptionalAuth
from lambapi.auth import DynamoDBAuth, BaseUser

@dataclass
class User(BaseUser):
    name: str
    email: str
    role: str

def create_app(event, context):
    app = API(event, context)

    # 認証設定
    auth = DynamoDBAuth(
        table_name="users",
        user_model=User,
        region_name="ap-northeast-1"
    )
    app.include_auth(auth)

    # 認証が必要なエンドポイント
    @app.get("/profile")
    def get_profile(current_user: User = CurrentUser()):
        return {"user": current_user}

    # ロール制限
    @app.delete("/admin/users/{user_id}")
    def delete_user(
        user_id: int = Path(),
        admin_user: User = RequireRole(roles=["admin"])
    ):
        return {"deleted": user_id, "by": admin_user.name}

    # オプショナル認証
    @app.get("/posts")
    def list_posts(user: Optional[User] = OptionalAuth()):
        if user:
            return {"posts": "personalized", "user": user.name}
        return {"posts": "public"}

    return app
```

### ローカル開発

```bash
# 新しいプロジェクトを作成
lambapi create my-api --template basic

# ローカルサーバーを起動（ホットリロード付き）
lambapi serve app

# ブラウザで確認
curl http://localhost:8000/
```

## 📚 ドキュメント

完全なドキュメントは **[https://sskyh0208.github.io/lambapi/](https://sskyh0208.github.io/lambapi/)** で公開されています。

<div class="grid cards" markdown>

-   🚀 **[クイックスタート](https://sskyh0208.github.io/lambapi/getting-started/quickstart/)**

    5 分で最初の API を構築

-   📖 **[チュートリアル](https://sskyh0208.github.io/lambapi/tutorial/basic-api/)**

    実際のコード例で機能を学習

-   🔧 **[API リファレンス](https://sskyh0208.github.io/lambapi/api/api/)**

    すべてのクラスとメソッドの詳細

-   🏗️ **[デプロイメント](https://sskyh0208.github.io/lambapi/guides/deployment/)**

    本番環境での運用とベストプラクティス

</div>

## 💡 なぜ lambapi？

### 従来の問題

```python
# 従来の Lambda ハンドラー（煩雑）
def lambda_handler(event, context):
    method = event['httpMethod']
    path = event['path']
    body = json.loads(event.get('body', '{}'))
    query_params = event.get('queryStringParameters', {}) or {}

    # 手動バリデーション、型変換、エラーハンドリング...
    if method == 'POST' and path == '/users':
        try:
            name = body['name']
            email = body['email']
            # バリデーション処理...
        except KeyError:
            return {'statusCode': 400, 'body': '{"error": "Missing field"}'}

    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({'result': 'success'})
    }
```

### lambapi なら

```python
# lambapi 版（シンプル・型安全）
from dataclasses import dataclass

@dataclass
class CreateUserRequest:
    name: str
    email: str

@app.post("/users")
def create_user(request: CreateUserRequest):  # 自動バリデーション・型変換
    return {"message": "Created", "name": request.name}
```

## 🔄 アップグレードガイド

v0.1.x から v0.2.x へのアップグレード：

**旧バージョン (v0.1.x)**
```python
@app.post("/users", request_format=UserModel)
def create_user(request):
    user_data = request.json()
    return {"user": user_data}

@auth.require_role(["admin"])
@app.delete("/users/{user_id}")
def delete_user(request, user_id: str):
    return {"deleted": user_id}
```

**新バージョン (v0.2.x)**
```python
@app.post("/users")
def create_user(user: UserModel):  # 自動推論またはアノテーション
    return {"user": user}

@app.delete("/users/{user_id}")
def delete_user(
    user_id: str = Path(),
    admin_user: User = RequireRole(roles=["admin"])
):
    return {"deleted": user_id}
```

## 🛠️ 開発

### 開発環境のセットアップ

```bash
git clone https://github.com/sskyh0208/lambapi.git
cd lambapi
pip install -e ".[dev]"
```

### Pre-commit フックのセットアップ

```bash
# CI と同じチェックをコミット前に実行
./scripts/setup-pre-commit.sh
```

### テスト・品質チェック

```bash
pytest              # テスト実行
black .             # コードフォーマット
mypy lambapi        # 型チェック

# または一括実行
pre-commit run --all-files
```

## 🤝 コミュニティ

- 📁 **[GitHub](https://github.com/sskyh0208/lambapi)** - ソースコード・ Issues ・ Discussions
- 📦 **[PyPI](https://pypi.org/project/lambapi/)** - パッケージダウンロード
- 📚 **[ドキュメント](https://sskyh0208.github.io/lambapi/)** - 完全な使用ガイド

## 📄 ライセンス

MIT License - 詳細は [LICENSE](LICENSE) ファイルを参照

<!-- Generated by Claude 🤖 -->
