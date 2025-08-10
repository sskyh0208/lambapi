# lambapi

**モダンな AWS Lambda 用 API フレームワーク**

![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![Version](https://img.shields.io/badge/version-0.2.1-green.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

---

## 概要

lambapi は、AWS Lambda で**FastAPI 風の直感的でモダンな API**を構築できる軽量フレームワークです。
アノテーションベースのパラメータ注入、自動バリデーション、統合認証システムなど、モダンな Web API 開発に必要な機能を提供します。

!!! example "シンプルな例"
    ```python
    from lambapi import API, create_lambda_handler
    from lambapi.annotations import Path, Query
    from dataclasses import dataclass

    @dataclass
    class User:
        name: str
        email: str

    def create_app(event, context):
        app = API(event, context)

        @app.get("/hello/{name}")
        def hello(name: str = Path(), greeting: str = Query(default="こんにちは")):
            return {"message": f"{greeting}, {name}さん!"}

        @app.post("/users")
        def create_user(user: User):  # 自動バリデーション
            return {"message": "Created", "user": user}

        return app

    lambda_handler = create_lambda_handler(create_app)
    ```

---

## ✨ 主な特徴

### 🚀 FastAPI 風記法
アノテーションベースの直感的なパラメータ注入で、素早く型安全な API を構築

### 📋 統合アノテーションシステム
Body, Path, Query, Header を統一的に処理し、コードの一貫性を保持

### 🔒 統合認証システム
CurrentUser, RequireRole, OptionalAuth で認証処理を簡潔に記述

### 🔄 自動バリデーション
Pydantic モデルとデータクラスの自動バリデーションでデータ整合性を保証

### 🎯 FastAPI 風自動推論
型アノテーションから自動的にパラメータソースを判定

### 🌐 CORS サポート
プリフライトリクエストの自動処理と柔軟な CORS 設定

### 🛡️ 構造化エラーハンドリング
本番運用に適した統一されたエラーレスポンス

### 📦 軽量
シンプルな API で最小限の学習コスト

### 🔒 型安全
完全な型ヒント対応で IDE の支援を最大活用

---

## 🚀 クイックスタート

### 1. インストール

```bash
pip install lambapi
```

### 2. 基本的な API の作成

```python
from lambapi import API, create_lambda_handler
from lambapi.annotations import Body, Path, Query
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
        return {"message": "Hello, lambapi!"}

    @app.get("/users/{user_id}")
    def get_user(user_id: int = Path()):
        return {"user_id": user_id, "name": f"User {user_id}"}

    @app.post("/users")
    def create_user(user: CreateUserRequest = Body()):
        return {"message": "Created", "user": user}

    @app.get("/search")
    def search(
        q: str = Query(default=""),
        limit: int = Query(default=10),
        sort: str = Query(default="id")
    ):
        return {
            "query": q,
            "limit": limit,
            "sort": sort,
            "results": [f"result-{i}" for i in range(1, min(limit, 5) + 1)]
        }

    return app

lambda_handler = create_lambda_handler(create_app)
```

### 3. FastAPI 風の自動推論

```python
from lambapi import API
from dataclasses import dataclass

@dataclass
class User:
    name: str
    email: str

def create_app(event, context):
    app = API(event, context)

    # 自動推論：User は自動的に Body として扱われる
    @app.post("/users")
    def create_user(user: User):
        return {"id": f"user_{hash(user.email)}", "name": user.name}

    # パスパラメータも自動推論
    @app.get("/users/{user_id}")
    def get_user(user_id: int):
        return {"user_id": user_id}

    # クエリパラメータも自動推論
    @app.get("/users")
    def list_users(limit: int = 10, offset: int = 0):
        return {"limit": limit, "offset": offset}

    return app
```

### 4. Lambda にデプロイ

SAM、Serverless Framework、CDK など、お好みのデプロイツールでデプロイできます。

---

## 📚 次のステップ

<div class="grid cards" markdown>

-   🚀 **はじめに**

    ---

    lambapi の基本概念とセットアップ方法を学ぶ

    [→ クイックスタート](getting-started/quickstart.md)

-   📖 **チュートリアル**

    ---

    実際のコード例とともに機能を学ぶ

    [→ 基本的な API](tutorial/basic-api.md)

-   📚 **API リファレンス**

    ---

    すべてのクラスとメソッドの詳細

    [→ API クラス](api/api.md)

-   ⚙️ **実践ガイド**

    ---

    本番環境での運用とベストプラクティス

    [→ デプロイメント](guides/deployment.md)

</div>

---

## 💡 なぜ lambapi？

### 従来の問題

```python
# 従来の Lambda ハンドラー（煩雑）
import json

def lambda_handler(event, context):
    # リクエストデータの解析が煩雑
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

    # レスポンス形式が統一されない
    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({'result': 'success'})
    }
```

### lambapi なら

```python
# lambapi 版（シンプル・型安全）
from lambapi import API, create_lambda_handler
from dataclasses import dataclass

@dataclass
class CreateUserRequest:
    name: str
    email: str

def create_app(event, context):
    app = API(event, context)

    @app.post("/users")
    def create_user(user: CreateUserRequest):  # 自動バリデーション・型変換
        return {"message": "Created", "user": user}

    return app

lambda_handler = create_lambda_handler(create_app)
```

---

## 🔄 v0.2.x の新機能

### 統合アノテーションシステム

すべてのパラメータタイプを統一的に処理：

```python
from lambapi.annotations import Body, Path, Query, Header, CurrentUser

@app.post("/users/{user_id}/posts")
def create_post(
    user_id: int = Path(),
    post_data: PostModel = Body(),
    version: str = Query(default="v1"),
    user_agent: str = Header(alias="User-Agent"),
    current_user: User = CurrentUser()
):
    return {"created": "success"}
```

### 認証システムの統合

認証もパラメータの一種として統一的に処理：

```python
from lambapi.annotations import CurrentUser, RequireRole, OptionalAuth

@app.get("/profile")
def get_profile(user: User = CurrentUser()):
    return {"user": user}

@app.delete("/admin/users/{user_id}")
def delete_user(
    user_id: int = Path(),
    admin: User = RequireRole(roles=["admin"])
):
    return {"deleted": user_id}
```

---

## 🏗️ アーキテクチャ

lambapi は以下の設計原則に基づいて構築されています：

- **統一性**: すべてのパラメータを同じ方式で処理
- **型安全性**: Pydantic と dataclass による自動バリデーション
- **直感性**: FastAPI 風の自然な記法
- **パフォーマンス**: Lambda の cold start を考慮した軽量設計
- **拡張性**: ミドルウェアとエラーハンドラーによる柔軟な拡張

---

## 🤝 コミュニティ

質問や提案がありましたら、お気軽にお声がけください：

- [GitHub Issues](https://github.com/sskyh0208/lambapi/issues) - バグ報告や機能要求
- [GitHub Discussions](https://github.com/sskyh0208/lambapi/discussions) - 質問や議論
- [Examples](https://github.com/sskyh0208/lambapi/tree/main/examples) - 実用的な例

---

## 📄 ライセンス

lambapi は [MIT ライセンス](https://github.com/sskyh0208/lambapi/blob/main/LICENSE) の下で公開されています。
