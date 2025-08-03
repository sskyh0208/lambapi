# ドキュメント

このディレクトリには lambapi の公式ドキュメントが含まれています。

## 開発

```bash
# 依存関係のインストール
pip install -r ./requirements.txt

# ローカルプレビュー
mkdocs serve

# 本番ビルド
mkdocs build

# GitHub Pages デプロイ
mkdocs gh-deploy
```

## 構成

- `index.md` - ホームページ
- `getting-started/` - インストールとクイックスタート
- `tutorial/` - 実践的なチュートリアル
- `api/` - API リファレンス
- `guides/` - 実践ガイド
- `examples/` - サンプルコード

## 編集

マークダウンファイルを編集後、`mkdocs serve` で変更を確認できます。