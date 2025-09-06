# lambapi

**モダンな AWS Lambda 用 API フレームワーク**

![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![Version](https://img.shields.io/badge/version-0.2.3-green.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

---

## 概要

lambapi は、AWS Lambda で**直感的でモダンな API**を構築できる軽量フレームワークです。
依存性注入システム、自動型変換・バリデーション、CORS サポートなど、モダンな Web API 開発に必要な機能を標準で提供します。

!!! example "シンプルな例"
    ```python
    from lambapi import API, create_lambda_handler, Query, Path, Body
    from dataclasses import dataclass

    @dataclass
    class User:
        name: str
        email: str
        age: int = 25

    def create_app(event, context):
        app = API(event, context)

        @app.get("/hello/{name}")
        def hello(
            name: str = Path(..., description="ユーザー名"),
            greeting: str = Query("こんにちは", description="挨拶")
        ):
            return {"message": f"{greeting}, {name}さん!"}

        @app.post("/users")
        def create_user(user: User = Body(...)):
            return {"message": "ユーザーを作成しました", "user": user}

        return app

    lambda_handler = create_lambda_handler(create_app)
    ```

---

## ✨ 主な特徴

### 🚀 直感的なモダンな記法
デコレータベースのシンプルなルート定義で、素早く API を構築

### 💉 依存性注入システム
Query, Path, Body, Authenticated による型安全なパラメータ取得

### 🔄 自動型変換・バリデーション
データクラスと型ヒントによる自動型変換とリクエストバリデーション

### 🛡️ 豊富なバリデーション機能
数値範囲、文字列長、正規表現などの制約チェック

### 🌐 CORS サポート
プリフライトリクエストの自動処理と柔軟な CORS 設定

### 🔐 認証・認可システム
DynamoDB + JWT による完全な認証・認可機能を内蔵

### 🛡️ 構造化エラーハンドリング
本番運用に適した統一されたエラーレスポンス

### 📦 軽量設計
標準ライブラリベース、外部依存を最小化

### 🔒 完全な型安全
mypy 対応の型ヒントで開発体験を向上

---

## 🚀 クイックスタート

### 1. インストール

```bash
# 基本インストール
pip install lambapi

# ローカル開発環境（uvicorn 付き）
pip install lambapi[dev]
```

### 2. 基本的な API の作成

```python
from lambapi import API, create_lambda_handler, Query, Path, Body
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
    def get_user(user_id: str = Path(..., description="ユーザー ID")):
        return {"user_id": user_id, "name": f"User {user_id}"}

    @app.get("/search")
    def search(
        q: str = Query(..., min_length=1, description="検索クエリ"),
        limit: int = Query(10, ge=1, le=100, description="結果数")
    ):
        return {
            "query": q,
            "limit": limit,
            "results": [f"result-{i}" for i in range(1, min(limit, 5) + 1)]
        }

    @app.post("/users")
    def create_user(user_data: CreateUserRequest = Body(...)):
        return {
            "message": "ユーザーが作成されました",
            "user": {"name": user_data.name, "email": user_data.email, "age": user_data.age}
        }

    return app

lambda_handler = create_lambda_handler(create_app)
```

### 3. ローカル開発

```bash
# 新しいプロジェクトを作成
lambapi create my-api --template basic

# uvicorn ベースの高性能ローカルサーバーを起動
lambapi serve app

# API 動作確認
curl "http://localhost:8000/search?q=python&limit=5"
curl -X POST http://localhost:8000/users \
  -H "Content-Type: application/json" \
  -d '{"name":"John","email":"john@example.com","age":30}'
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
# 従来の Lambda ハンドラー
import json

def lambda_handler(event, context):
    # リクエストデータの解析が煩雑
    method = event['httpMethod']
    path = event['path']
    query_params = event.get('queryStringParameters', {}) or {}
    
    # 手動でパラメータ取得・型変換・バリデーション
    try:
        limit = int(query_params.get('limit', 10))
        if limit <= 0 or limit > 100:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Invalid limit'})
            }
    except ValueError:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Invalid limit format'})
        }

    # ルーティングが複雑
    if method == 'GET' and path == '/users':
        # ... 処理
        pass

    # レスポンス形式が統一されない
    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({'users': []})
    }
```

### lambapi なら

```python
from lambapi import API, create_lambda_handler, Query

def create_app(event, context):
    app = API(event, context)

    @app.get("/users")
    def get_users(limit: int = Query(10, ge=1, le=100, description="取得件数")):
        # パラメータは自動で型変換・バリデーション済み
        return {"users": [f"user-{i}" for i in range(limit)]}

    return app

lambda_handler = create_lambda_handler(create_app)
```

**80% のボイラープレートコードを削減** - パラメータ取得、型変換、バリデーション、エラーハンドリングがすべて自動化されます。

---

## 🏗️ アーキテクチャ

lambapi は以下の設計原則に基づいて構築されています：

- **シンプリシティ**: 複雑な設定なしで即座に開始
- **パフォーマンス**: Lambda の cold start を考慮した軽量設計
- **拡張性**: ミドルウェアとエラーハンドラーによる柔軟な拡張
- **型安全性**: TypeScript のような型推論の恩恵

---

## 🤝 コミュニティ

質問や提案がありましたら、お気軽にお声がけください：

- [GitHub Issues](https://github.com/sskyh0208/lambapi/issues) - バグ報告や機能要求
- [GitHub Discussions](https://github.com/sskyh0208/lambapi/discussions) - 質問や議論
- [Examples](https://github.com/sskyh0208/lambapi/tree/main/examples) - 実用的な例

---

## 📄 ライセンス

lambapi は [MIT ライセンス](https://github.com/sskyh0208/lambapi/blob/main/LICENSE) の下で公開されています。
