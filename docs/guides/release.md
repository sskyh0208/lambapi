# リリースガイド

このガイドでは、lambapi プロジェクトのリリース作成方法について説明します。

## リリース方法

### 1. GitHub Actions でのリリース作成

最も簡単で推奨される方法です。

#### 手順

1. GitHub の **Actions** タブに移動
2. **リリース作成** ワークフローを選択
3. **Run workflow** をクリック
4. 以下のオプションを設定：

| オプション | 説明 | 例 |
|-----------|------|-----|
| **バージョンアップの種類** | セマンティックバージョニング | `patch`, `minor`, `major` |
| **カスタムバージョン** | 手動でバージョンを指定 | `1.2.3` |
| **ドラフトリリース** | リリースを非公開で作成 | ☑️ または ☐ |
| **プレリリース** | ベータ版として作成 | ☑️ または ☐ |

5. **Run workflow** を実行

#### 実行内容

ワークフローが以下を自動実行します：

- ✅ バージョン番号の自動計算・更新
- ✅ 変更ログの自動生成
- ✅ Git タグの作成
- ✅ GitHub リリースの作成
- ✅ パッケージファイルのビルド・添付
- ✅ ドキュメントの自動更新

### 2. 手動リリース作成

より細かい制御が必要な場合。

#### 手順

```bash
# 1. バージョン更新スクリプトを実行
python scripts/update_version.py --type patch
# または
python scripts/update_version.py 1.2.3

# 2. 変更をコミット
git add .
git commit -m "chore: バージョンを v1.2.3 に更新"

# 3. タグを作成
git tag v1.2.3
git push origin main --tags

# 4. GitHub でリリースを手動作成
```

## バージョニング戦略

### セマンティックバージョニング

```
MAJOR.MINOR.PATCH
```

| 種類 | いつ上げるか | 例 |
|------|-------------|-----|
| **MAJOR** | 破壊的変更があるとき | API の大幅変更 |
| **MINOR** | 後方互換性のある機能追加 | 新機能追加 |
| **PATCH** | 後方互換性のあるバグ修正 | バグ修正、ドキュメント更新 |

### バージョン例

```bash
# バグ修正: 0.1.0 → 0.1.1
python scripts/update_version.py --type patch

# 新機能: 0.1.1 → 0.2.0
python scripts/update_version.py --type minor

# 破壊的変更: 0.2.0 → 1.0.0
python scripts/update_version.py --type major

# カスタム: 任意のバージョン
python scripts/update_version.py 1.5.0
```

## リリースの種類

### 通常リリース

```yaml
バージョンアップの種類: patch
ドラフトリリース: ☐
プレリリース: ☐
```

- 一般ユーザー向けの安定版
- 自動で latest タグが付与

### プレリリース

```yaml
バージョンアップの種類: minor
ドラフトリリース: ☐
プレリリース: ☑️
```

- ベータ版やアルファ版
- latest タグは付与されない
- テスター向け

### ドラフトリリース

```yaml
バージョンアップの種類: major
ドラフトリリース: ☑️
プレリリース: ☐
```

- 非公開のリリース
- レビュー後に公開

## 自動生成される内容

### 変更ログ

リリースノートには以下が自動生成されます：

```markdown
# リリース v1.2.3

## 変更内容

- feat: 新機能を追加 (a1b2c3d)
- fix: バグを修正 (d4e5f6g)
- docs: ドキュメントを更新 (g7h8i9j)

## インストール

```bash
pip install lambapi==1.2.3
```

## ドキュメント

📚 [公式ドキュメント](https://sskyh0208.github.io/lambapi/)
```

### リリースアセット

以下のファイルが自動添付されます：

- `lambapi-1.2.3-py3-none-any.whl` - Wheel パッケージ
- `lambapi-1.2.3.tar.gz` - ソースアーカイブ

## トラブルシューティング

### よくある問題

#### 1. ワークフローが失敗する

**原因**: 権限不足やバージョン形式エラー

**解決方法**:
```bash
# GitHub トークンの権限を確認
# リポジトリの Settings > Actions > General で Workflow permissions を確認
```

#### 2. バージョンが重複している

**原因**: 既に同じタグが存在

**解決方法**:
```bash
# 既存のタグを確認
git tag -l

# 必要に応じてタグを削除
git tag -d v1.2.3
git push origin :refs/tags/v1.2.3
```

#### 3. 変更ログが空

**原因**: 前回のリリースから変更がない

**解決方法**:
- コミットを確認
- 手動で変更ログを編集

### ログの確認

```bash
# ワークフローのログを確認
gh run list
gh run view [RUN_ID] --log

# 現在のバージョンを確認
python -c "import lambapi; print(lambapi.__version__)"
```

## ベストプラクティス

### リリース前チェックリスト

- [ ] CI/CD が全て成功している
- [ ] ドキュメントが最新
- [ ] 変更ログを確認
- [ ] 破壊的変更がある場合は MAJOR バージョンアップ

### リリース後の作業

- [ ] リリースノートの確認・編集
- [ ] 重要な変更は GitHub Discussions で告知
- [ ] 必要に応じてドキュメントの追加更新

## 参考資料

- [Semantic Versioning](https://semver.org/)
- [GitHub Releases](https://docs.github.com/en/repositories/releasing-projects-on-github)
- [GitHub Actions](https://docs.github.com/en/actions)