# lambapi Examples - 段階的学習サンプル集

lambapi v0.2.x の統合アノテーションシステムを段階的に学習できるサンプル集です。

## 📚 学習の進め方

**段階的に学習することをおすすめします：**

1. **[01_quickstart.py](01_quickstart.py)** - まずはここから！
2. **[02_basic_crud.py](02_basic_crud.py)** - 実用的な API を作る
3. **[03_authentication.py](03_authentication.py)** - 認証機能を理解する
4. **[04_advanced_features.py](04_advanced_features.py)** - 高度な機能を活用する

---

## 01. クイックスタート 🚀

**最初に実行するサンプル**

```bash
python examples/01_quickstart.py
```

**学習内容：**
- シンプルな Hello World API
- 自動パラメータ推論の基本
- パスパラメータとクエリパラメータ

**ファイル：** `01_quickstart.py`
**実行時間：** 5 分
**前提知識：** Python の基本構文のみ

---

## 02. 基本的な CRUD API 📝

**実用的なデータ操作を学ぶ**

```bash
python examples/02_basic_crud.py
```

**学習内容：**
- データクラスによるバリデーション
- CREATE, READ, UPDATE, DELETE 操作
- エラーレスポンスの処理
- 混合パラメータ（Path + Body）

**ファイル：** `02_basic_crud.py`
**実行時間：** 10 分
**前提知識：** 01 を完了していること

---

## 03. 認証機能 🔐

**セキュアな API を作る**

```bash
python examples/03_authentication.py
```

**学習内容：**
- CurrentUser, RequireRole, OptionalAuth アノテーション
- JWT 認証の統合
- ロールベースアクセス制御
- パブリック・プライベートエンドポイント

**ファイル：** `03_authentication.py`
**実行時間：** 15 分
**前提知識：** 01, 02 を完了していること
**注意：** DynamoDB なしでもデモ実行可能

---

## 04. 高度な機能 ⚡

**本番環境レベルの構成**

```bash
python examples/04_advanced_features.py
```

**学習内容：**
- CORS 設定
- Header アノテーション
- カスタムエラーハンドリング
- Pydantic 連携（オプション）
- 複雑な検索・フィルタリング

**ファイル：** `04_advanced_features.py`
**実行時間：** 20 分
**前提知識：** 01, 02, 03 を完了していること

---

## 🎯 各サンプルの特徴

| サンプル | 複雑度 | 学習目標 | 実行方法 |
|---------|--------|----------|---------|
| **01_quickstart** | ⭐ | API の基本を理解 | `python 01_quickstart.py` |
| **02_basic_crud** | ⭐⭐ | 実用的な API 設計 | `python 02_basic_crud.py` |
| **03_authentication** | ⭐⭐⭐ | セキュリティ機能 | `python 03_authentication.py` |
| **04_advanced_features** | ⭐⭐⭐⭐ | 本番環境レベル | `python 04_advanced_features.py` |

---

## 🚀 実行方法

### ローカルでのテスト実行

```bash
# 各サンプルを直接実行
python examples/01_quickstart.py
python examples/02_basic_crud.py
python examples/03_authentication.py
python examples/04_advanced_features.py
```

### ローカルサーバーで実行

```bash
# lambapi CLI を使用（開発サーバー起動）
lambapi serve examples/01_quickstart
lambapi serve examples/02_basic_crud
lambapi serve examples/03_authentication
lambapi serve examples/04_advanced_features
```

### AWS Lambda にデプロイ

```bash
# SAM でのデプロイ例
cp examples/02_basic_crud.py app.py
sam build
sam deploy --guided
```

---

## 📖 学習のポイント

### 01 → 02 で学ぶこと
- 自動推論から明示的アノテーションへ
- データクラスによる型安全性
- エラーハンドリングのベストプラクティス

### 02 → 03 で学ぶこと
- 認証システムの統合方法
- 統合アノテーション（認証もパラメータ）
- セキュリティを考慮した API 設計

### 03 → 04 で学ぶこと
- 本番環境に必要な機能（CORS, Header）
- 高度なバリデーション（Pydantic）
- パフォーマンスとスケーラビリティ

---

## 🔧 オプション設定

### Pydantic を使用する場合

```bash
pip install pydantic[email]
```

### DynamoDB 認証を使用する場合

```bash
# AWS 認証情報の設定
aws configure

# 環境変数の設定
export DYNAMODB_TABLE_NAME="your-users-table"
export AWS_REGION="ap-northeast-1"
```

---

## 📚 さらに学習したい場合

- **[公式ドキュメント](https://sskyh0208.github.io/lambapi/)** - 完全な API リファレンス
- **[チュートリアル](../docs/tutorial/basic-api.md)** - 詳細なチュートリアル
- **[認証ガイド](../docs/guides/authentication.md)** - 認証機能の詳細

---

## 💡 よくある質問

**Q: どのサンプルから始めればよいですか？**
A: 必ず `01_quickstart.py` から始めてください。基本概念の理解が重要です。

**Q: 認証機能を使うには DynamoDB が必要ですか？**
A: `03_authentication.py` はデモモードで実行できます。実際の認証には DynamoDB 設定が必要です。

**Q: Pydantic がなくても動作しますか？**
A: はい。Pydantic はオプションです。ない場合はデータクラスのみ使用します。

**Q: 本番環境で使用できますか？**
A: サンプルは学習用です。本番環境では適切なセキュリティ設定を行ってください。

---

## 🎉 学習完了後

すべてのサンプルを理解できたら：

1. **独自の API を作成** - 学んだ機能を組み合わせる
2. **本番環境にデプロイ** - AWS Lambda で実際に運用
3. **コミュニティに参加** - GitHub で質問・議論

**Happy Coding with lambapi! 🚀**
