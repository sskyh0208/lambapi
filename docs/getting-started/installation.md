# インストール

このページでは、lambapi をプロジェクトにインストールする方法について説明します。

## システム要件

### Python バージョン

lambapi は以下の Python バージョンをサポートしています：

- **Python 3.10** 以上
- **推奨**: Python 3.13 以上（AWS Lambda の推奨ランタイム）

### 依存関係

lambapi は**外部依存なし**で動作します。Python 標準ライブラリのみを使用しているため、軽量で高速です。

## インストール方法

### pip を使用したインストール

```bash
pip install lambapi
```

### 開発版のインストール

最新の開発版を使用したい場合：

```bash
pip install git+https://github.com/sskyh0208/lambapi.git
```

### 特定のバージョンのインストール

```bash
# 特定のバージョンを指定
pip install lambapi==1.0.0

# バージョン範囲を指定
pip install "lambapi>=1.0.0,<2.0.0"
```

## 仮想環境での使用

プロジェクトごとに独立した環境を作成することを強く推奨します。

### venv を使用

```bash
# 仮想環境の作成
python -m venv lambapi-env

# 仮想環境の有効化
# Linux/macOS:
source lambapi-env/bin/activate
# Windows:
lambapi-env\Scripts\activate

# lambapi のインストール
pip install lambapi
```

### poetry を使用

```bash
# 新しいプロジェクトの作成
poetry new my-lambapi-project
cd my-lambapi-project

# lambapi を依存関係に追加
poetry add lambapi

# 開発用依存関係も追加（オプション）
poetry add --group dev pytest black mypy
```

```toml title="pyproject.toml"
[tool.poetry.dependencies]
python = "^3.7"
lambapi = "^1.0.0"

[tool.poetry.group.dev.dependencies]
pytest = "^7.0.0"
black = "^22.0.0"
mypy = "^0.991"
```

### pipenv を使用

```bash
# 新しいプロジェクトの初期化
pipenv install lambapi

# 開発用パッケージも追加
pipenv install --dev pytest black mypy
```

## インストールの確認

インストールが正常に完了したか確認します：

```python
import lambapi
print(lambapi.__version__)
```

または、コマンドラインから：

```bash
python -c "import lambapi; print(lambapi.__version__)"
```

## トラブルシューティング

## AWS Lambda での使用

### Lambda Layer の作成

lambapi を Lambda Layer として作成することで、複数の関数で共有できます：

```bash
# 依存関係をインストール
mkdir python
pip install lambapi -t python/

# Layer パッケージを作成
zip -r lambapi-layer.zip python/
```

### 容量の最適化

Lambda のデプロイパッケージサイズを最小化するために：

```bash
# wheel を使用してインストール
pip install --only-binary=all lambapi

# 不要なファイルを除外
pip install lambapi --no-deps
```

## 次のステップ

インストールが完了したら：

1. [クイックスタート](quickstart.md) - 最初の API を作成
2. [基本概念](concepts.md) - lambapi の設計思想を理解
3. [チュートリアル](../tutorial/basic-api.md) - 実践的な例を学習

## サポート

インストールで問題が発生した場合：

- [GitHub Issues](https://github.com/sskyh0208/lambapi/issues) でバグ報告
- [GitHub Discussions](https://github.com/sskyh0208/lambapi/discussions) で質問
- [FAQ](../guides/troubleshooting.md) も確認してください