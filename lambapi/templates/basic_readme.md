# {project_name}

lambapi を使用した基本的な API プロジェクトです。

## 開発

### ローカルサーバーの起動

```bash
lambapi serve app
```

### テスト

```bash
curl http://localhost:8000/
curl http://localhost:8000/hello/world
```

## デプロイ

### SAM

```bash
sam build
sam deploy --guided
```

### Serverless Framework

```bash
serverless deploy
```

## 構成

- `app.py` - メインアプリケーション
- `requirements.txt` - Python 依存関係
- `template.yaml` - SAM テンプレート（オプション）