# {project_name}

lambapi を使用した CRUD API プロジェクトです。

## 機能

- ✅ アイテムの作成・読み取り・更新・削除 (CRUD)
- ✅ バリデーション
- ✅ エラーハンドリング
- ✅ 検索・フィルタリング

## 開発

### ローカルサーバーの起動

```bash
lambapi serve app
```

### API テスト

```bash
# 一覧取得
curl http://localhost:8000/items

# 作成
curl -X POST http://localhost:8000/items \
  -H "Content-Type: application/json" \
  -d '{{"name":"テストアイテム","description":"説明"}}'

# 取得
curl http://localhost:8000/items/{{item_id}}

# 更新
curl -X PUT http://localhost:8000/items/{{item_id}} \
  -H "Content-Type: application/json" \
  -d '{{"name":"更新されたアイテム"}}'

# 削除
curl -X DELETE http://localhost:8000/items/{{item_id}}
```

## デプロイ

### SAM

```bash
sam build
sam deploy --guided
```

## 構成

- `app.py` - メインアプリケーション
- `requirements.txt` - Python 依存関係
- `template.yaml` - SAM テンプレート