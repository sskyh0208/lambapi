# lambapi

**モダンな AWS Lambda 用 API フレームワーク**

![Python](https://img.shields.io/badge/python-3.7+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg)

---

## 概要

lambapi は、AWS Lambda で**直感的でモダンな API**を構築できる軽量フレームワークです。  
パスパラメータとクエリパラメータの自動注入、型変換、CORS サポートなど、モダンな Web API 開発に必要な機能を標準で提供します。

!!! example "シンプルな例"
    ```python
    from lambapi import API, create_lambda_handler

    def create_app(event, context):
        app = API(event, context)
        
        @app.get("/hello/{name}")
        def hello(name: str, greeting: str = "こんにちは"):
            return {"message": f"{greeting}, {name}さん!"}
        
        return app

    lambda_handler = create_lambda_handler(create_app)
    ```

---

## ✨ 主な特徴

### 🚀 直感的な記法
デコレータベースのシンプルなルート定義で、素早く API を構築

### 📋 自動パラメータ注入
パスパラメータとクエリパラメータを関数引数として直接受け取り

### 🔄 型自動変換
`int`、`float`、`bool`、`str` の自動型変換でタイプセーフな開発

### 🎯 デフォルト値サポート
クエリパラメータのデフォルト値設定で柔軟な API 設計

### 🌐 CORS サポート
プリフライトリクエストの自動処理と柔軟な CORS 設定

### 🛡️ 構造化エラーハンドリング
本番運用に適した統一されたエラーレスポンス

### 📦 軽量
標準ライブラリのみを使用、外部依存なし

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

def create_app(event, context):
    app = API(event, context)
    
    @app.get("/")
    def hello():
        return {"message": "Hello, lambapi!"}
    
    @app.get("/users/{user_id}")
    def get_user(user_id: str):
        return {"user_id": user_id, "name": f"User {user_id}"}
    
    @app.get("/search")
    def search(q: str = "", limit: int = 10):
        return {
            "query": q,
            "limit": limit,
            "results": [f"result-{i}" for i in range(1, limit + 1)]
        }
    
    return app

lambda_handler = create_lambda_handler(create_app)
```

### 3. Lambda にデプロイ

SAM、Serverless Framework、CDK など、お好みのデプロイツールでデプロイできます。

---

## 📚 次のステップ

<div class="grid cards" markdown>

-   :material-rocket-launch:{ .lg .middle } **はじめに**

    ---

    lambapi の基本概念とセットアップ方法を学ぶ

    [:octicons-arrow-right-24: クイックスタート](getting-started/quickstart.md)

-   :material-book-open-page-variant:{ .lg .middle } **チュートリアル**

    ---

    実際のコード例とともに機能を学ぶ

    [:octicons-arrow-right-24: 基本的な API](tutorial/basic-api.md)

-   :material-api:{ .lg .middle } **API リファレンス**

    ---

    すべてのクラスとメソッドの詳細

    [:octicons-arrow-right-24: API クラス](api/api.md)

-   :material-application-cog:{ .lg .middle } **実践ガイド**

    ---

    本番環境での運用とベストプラクティス

    [:octicons-arrow-right-24: デプロイメント](guides/deployment.md)

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
    
    # パラメータの型変換が面倒
    limit = int(query_params.get('limit', 10))
    
    # ルーティングが複雑
    if method == 'GET' and path == '/users':
        # ... 処理
        pass
    
    # レスポンス形式が統一されない
    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({'data': 'result'})
    }
```

### lambapi なら

```python
from lambapi import API, create_lambda_handler

def create_app(event, context):
    app = API(event, context)
    
    @app.get("/users")
    def get_users(limit: int = 10):
        # パラメータは自動で型変換される
        return {"users": [f"user-{i}" for i in range(limit)]}
    
    return app

lambda_handler = create_lambda_handler(create_app)
```

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