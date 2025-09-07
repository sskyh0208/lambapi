# lambapi

**モダンな AWS Lambda 用 API フレームワーク**

![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![Version](https://img.shields.io/badge/version-0.2.3-green.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

AWS Lambda で直感的でモダンな API を構築できる軽量フレームワーク。依存性注入システム、自動型変換、バリデーション、CORS サポートを標準提供。

## ✨ 主な特徴

- 🚀 **モダンな API** - デコレータベースの直感的なルート定義
- 💉 **依存性注入** - Query, Path, Body, Authenticated による型安全なパラメータ取得
- 🔄 **自動型変換・バリデーション** - データクラスと型ヒントによる自動処理
- 🛡️ **豊富なバリデーション** - 数値範囲、文字列長、正規表現などの制約チェック
- 🌐 **CORS サポート** - プリフライトリクエストの自動処理
- 🔐 **認証システム** - DynamoDB + JWT による完全な認証・認可機能
- 🛡️ **構造化エラーハンドリング** - 専用例外クラスによる詳細なエラー情報
- 📦 **軽量設計** - 標準ライブラリベース、外部依存最小化
- 🔒 **完全な型安全** - mypy 対応の型ヒントで開発体験を向上

## 🚀 クイックスタート

### インストール

```bash
# 基本インストール
pip install lambapi

# ローカル開発環境（uvicorn 付き）
pip install lambapi[dev]

# または uvicorn を個別にインストール
pip install lambapi uvicorn[standard]
```

### 基本的な使用例

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

    @app.get("/search")
    def search(
        query: str = Query(..., description="検索クエリ", min_length=1),
        limit: int = Query(10, ge=1, le=100, description="結果数"),
        category: str = Query("all", description="カテゴリー")
    ):
        return {"query": query, "limit": limit, "category": category}

    @app.post("/users")
    def create_user(user_data: CreateUserRequest = Body(...)):
        return {
            "message": "ユーザーが作成されました", 
            "user": {"name": user_data.name, "email": user_data.email, "age": user_data.age}
        }

    @app.get("/users/{user_id}")
    def get_user(user_id: str = Path(..., description="ユーザー ID")):
        return {"user_id": user_id, "name": f"User {user_id}"}

    return app

lambda_handler = create_lambda_handler(create_app)
```

### ローカル開発

lambapi は uvicorn を使用した高性能なローカル開発サーバーを提供します。AWS Lambda と API Gateway の環境を完全に再現し、本番環境と同等の動作を保証します。

```bash
# 新しいプロジェクトを作成
lambapi create my-api --template basic

# 高性能ローカルサーバーを起動（uvicorn + ホットリロード付き）
lambapi serve app

# カスタムポート・ホスト設定
lambapi serve app --host 0.0.0.0 --port 8080

# 詳細ログでデバッグ
lambapi serve app --debug --log-level debug

# API 動作確認
curl http://localhost:8000/
curl -X POST http://localhost:8000/users -H "Content-Type: application/json" -d '{"name":"test"}'
```

**uvicorn 統合の利点**:
- 🚀 **高性能** - 非同期 ASGI ベースで高速レスポンス
- 🔄 **ホットリロード** - コード変更を即座に反映
- 🌐 **API Gateway 互換** - 本番環境と同等のリクエスト/レスポンス形式
- 📊 **詳細ログ** - リクエスト詳細とエラー情報の表示
- ⚙️ **豊富な設定** - ワーカー数、ログレベル等のカスタマイズ可能

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
    
    # 複雑なルーティング...
    if method == 'GET' and path == '/users':
        # ビジネスロジック
        pass

    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({'users': []})
    }
```

### lambapi なら

```python
# lambapi 版（シンプルで型安全）
@app.get("/users")
def get_users(limit: int = Query(10, ge=1, le=100, description="取得件数")):
    return {"users": [f"user-{i}" for i in range(limit)]}
```

**削減できるコード**: パラメータ取得、型変換、バリデーション、エラーハンドリングが自動化され、**約 80% のボイラープレートコードを削減**。

## 🤝 コミュニティ

- 📁 **[GitHub](https://github.com/sskyh0208/lambapi)** - ソースコード・ Issues ・ Discussions
- 📦 **[PyPI](https://pypi.org/project/lambapi/)** - パッケージダウンロード
- 📚 **[ドキュメント](https://sskyh0208.github.io/lambapi/)** - 完全な使用ガイド

## 📄 ライセンス

MIT License - 詳細は [LICENSE](LICENSE) ファイルを参照

<!-- Generated by Claude 🤖 -->
