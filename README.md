# lambapi

**モダンな AWS Lambda 用 API フレームワーク**

![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![Version](https://img.shields.io/badge/version-0.2.2-green.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

AWS Lambda で直感的でモダンな API を構築できる軽量フレームワーク。パスパラメータとクエリパラメータの自動注入、型変換、CORS サポートを標準提供。

## ✨ 主な特徴

- 🚀 **直感的な記法** - デコレータベースのシンプルなルート定義
- 📋 **自動パラメータ注入** - パス・クエリパラメータを関数引数として直接受け取り
- 🔄 **型自動変換** - `int`、`float`、`bool`、`str` の自動型変換
- 🛡️ **バリデーション機能** - リクエストパラメータの自動バリデーションとエラーレスポンス
- 🌐 **CORS サポート** - プリフライトリクエストの自動処理
- 🔐 **認証システム** - DynamoDB + JWT による完全な認証・認可機能
- 🛡️ **構造化エラーハンドリング** - 本番運用に適した統一エラーレスポンス
- 📦 **軽量** - 標準ライブラリのみ、外部依存なし（認証機能は別途）
- 🔒 **型安全** - 完全な型ヒント対応

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
            "user": {"name": user_data.name, "email": user_data.email}
        }

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
    limit = int(query_params.get('limit', 10))  # 手動型変換

    if method == 'GET' and path == '/users':
        # 複雑なルーティング...
        pass

    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({'data': 'result'})
    }
```

### lambapi なら

```python
# lambapi 版（シンプル）
@app.get("/users")
def get_users(limit: int):
    return {"users": [f"user-{i}" for i in range(limit)]}
```



## 🤝 コミュニティ

- 📁 **[GitHub](https://github.com/sskyh0208/lambapi)** - ソースコード・ Issues ・ Discussions
- 📦 **[PyPI](https://pypi.org/project/lambapi/)** - パッケージダウンロード
- 📚 **[ドキュメント](https://sskyh0208.github.io/lambapi/)** - 完全な使用ガイド

## 📄 ライセンス

MIT License - 詳細は [LICENSE](LICENSE) ファイルを参照

<!-- Generated by Claude 🤖 -->
