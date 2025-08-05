# Pre-commit フック

コミット前に自動的にコード品質チェックを実行し、CI での失敗を防ぎます。

## セットアップ

### 自動セットアップ

```bash
# セットアップスクリプトを実行
./scripts/setup-pre-commit.sh
```

### 手動セットアップ

```bash
# 依存関係のインストール
pip install -e ".[dev]"

# pre-commit フックのインストール
pre-commit install

# 初回実行
pre-commit run --all-files
```

## 実行されるチェック

Pre-commit フックでは以下のチェックが実行されます：

### コード品質
- **Black**: コードフォーマッター
- **Flake8**: コードリンター
- **MyPy**: 型チェック

### 基本チェック
- 行末の空白除去
- ファイル末尾の改行
- YAML ファイル構文チェック
- 大きなファイルの検出
- マージコンフリクトの検出

### セキュリティ
- **Bandit**: セキュリティ脆弱性スキャン

### テスト
- **pytest**: 高速テスト実行（重要なテストのみ）

## 使用方法

### 通常のコミット
```bash
git add .
git commit -m "feat: 新機能追加"
# ↑ 自動的に pre-commit チェックが実行される
```

### 手動実行
```bash
# 全ファイルをチェック
pre-commit run --all-files

# 特定のファイルをチェック
pre-commit run --files file1.py file2.py

# 特定のフックのみ実行
pre-commit run black
pre-commit run flake8
```

### チェックをスキップ
```bash
# 緊急時のみ使用（非推奨）
git commit --no-verify -m "hotfix: 緊急修正"
```

## CI との違い

| 項目 | Pre-commit | CI |
|------|------------|-----|
| 実行タイミング | コミット前 | PR 作成後 |
| テスト範囲 | 高速テストのみ | 全テスト（複数 Python 版） |
| フィードバック速度 | 即座 | 数分 |
| 目的 | 事前防止 | 品質保証 |

## トラブルシューティング

### フックの更新
```bash
pre-commit autoupdate
```

### キャッシュクリア
```bash
pre-commit clean
```

### フックの無効化
```bash
# 一時的に無効化
pre-commit uninstall

# 再有効化
pre-commit install
```

## 推奨ワークフロー

1. **初回設定**: `./scripts/setup-pre-commit.sh` を実行
2. **開発**: 通常通りコードを書く
3. **コミット**: `git commit` で自動チェック
4. **修正**: エラーがあれば修正して再コミット
5. **PR 作成**: CI で最終確認

これにより、CI での失敗を大幅に減らすことができます。
