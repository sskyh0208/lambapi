# Lambda ECR デプロイ例

このディレクトリには、lambapi アプリケーションを ECR コンテナイメージとして AWS Lambda にデプロイするための完全な例が含まれています。

## ファイル構成

```
lambda-ecr-deploy/
├── app.py                 # 大規模アプリケーション例
├── Dockerfile             # 基本的なコンテナ設定
├── Dockerfile.optimized   # マルチステージビルド版
├── requirements.txt       # Python 依存関係
├── deploy.sh             # ECR デプロイスクリプト
└── README.md             # このファイル
```

## Lambda 関数の設定

### ECR デプロイでの重要な設定

#### 1. パッケージタイプ

**AWS コンソール設定:**
```
パッケージタイプ: Image
```

#### 2. コンテナイメージ URI

```
123456789012.dkr.ecr.ap-northeast-1.amazonaws.com/my-lambapi-app:latest
```

#### 3. CMD の設定

**Dockerfile で指定:**
```dockerfile
CMD ["app.lambda_handler"]
```

**Lambda 設定で上書き可能:**
- AWS コンソール → 設定 → イメージ設定
- CMD: `["app.lambda_handler"]`

### アプリケーションコードの構成

```python title="app.py"
from lambapi import API, create_lambda_handler

def create_app(event, context):
    app = API(event, context)
    
    @app.get("/")
    def root():
        return {"message": "Hello from ECR Container!"}
    
    return app

# ★重要: この関数名が CMD 設定に対応
lambda_handler = create_lambda_handler(create_app)
```

## 前提条件

1. **Docker のインストール**
   ```bash
   docker --version
   ```

2. **AWS CLI の設定**
   ```bash
   aws configure
   aws sts get-caller-identity
   ```

3. **ECR リポジトリの作成権限**

## デプロイ方法

### 1. 自動デプロイ

```bash
# このディレクトリに移動
cd examples/lambda-ecr-deploy

# デプロイスクリプトを実行
./deploy.sh my-repo-name ap-northeast-1 latest my-function-name
```

### 2. 手動デプロイ

```bash
# 変数設定
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION=ap-northeast-1
REPO_NAME=my-lambapi-app
IMAGE_URI=${AWS_ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${REPO_NAME}

# ECR リポジトリ作成
aws ecr create-repository --repository-name ${REPO_NAME} --region ${REGION}

# ECR ログイン
aws ecr get-login-password --region ${REGION} | \
docker login --username AWS --password-stdin ${IMAGE_URI}

# イメージビルド
docker build -t ${REPO_NAME} .

# タグ付けとプッシュ
docker tag ${REPO_NAME}:latest ${IMAGE_URI}:latest
docker push ${IMAGE_URI}:latest

# Lambda 関数作成
aws lambda create-function \
    --function-name my-lambapi-container \
    --package-type Image \
    --code ImageUri=${IMAGE_URI}:latest \
    --role arn:aws:iam::${AWS_ACCOUNT_ID}:role/lambda-execution-role \
    --timeout 30 \
    --memory-size 512
```

## Lambda 関数設定の詳細

### 基本設定

```
関数名: my-lambapi-container
パッケージタイプ: Image
コンテナイメージ URI: 123456789012.dkr.ecr.region.amazonaws.com/repo:tag
アーキテクチャ: x86_64
```

### 実行設定

```
メモリ: 512 MB (ECR は最低 512MB 推奨)
タイムアウト: 30 秒 (API Gateway 使用時)
一時ストレージ: 512 MB (デフォルト)
```

### 環境変数

```bash
ENVIRONMENT=production
LOG_LEVEL=INFO
LOG_FORMAT=json
```

### コンテナ設定

**イメージ設定:**
- CMD: `["app.lambda_handler"]` (Dockerfile で指定)
- 作業ディレクトリ: `/var/task` (自動設定)
- ENTRYPOINT: Lambda ランタイムが自動設定

## Dockerfile の設定パターン

### 基本版

```dockerfile title="Dockerfile"
FROM public.ecr.aws/lambda/python:3.13

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app.py ${LAMBDA_TASK_ROOT}/

CMD ["app.lambda_handler"]
```

### 最適化版（マルチステージビルド）

```dockerfile title="Dockerfile.optimized"
# ビルドステージ
FROM public.ecr.aws/lambda/python:3.13 as builder
RUN yum update -y && yum install -y gcc python3-devel
COPY requirements.txt .
RUN pip install -r requirements.txt -t /opt/python

# 本番ステージ
FROM public.ecr.aws/lambda/python:3.13
COPY --from=builder /opt/python ${LAMBDA_TASK_ROOT}/
COPY app.py ${LAMBDA_TASK_ROOT}/
CMD ["app.lambda_handler"]
```

### 複雑な構成の例

```dockerfile title="Dockerfile.complex"
FROM public.ecr.aws/lambda/python:3.13

# システム依存関係
RUN yum update -y && yum install -y \
    gcc \
    postgresql-devel \
    && yum clean all

# Python 依存関係
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーション構造
COPY app.py ${LAMBDA_TASK_ROOT}/
COPY api/ ${LAMBDA_TASK_ROOT}/api/
COPY models/ ${LAMBDA_TASK_ROOT}/models/
COPY config/ ${LAMBDA_TASK_ROOT}/config/

# 環境変数
ENV PYTHONPATH="${LAMBDA_TASK_ROOT}:${PYTHONPATH}"
ENV ENVIRONMENT=production

# ハンドラー指定
CMD ["app.lambda_handler"]
```

## 異なるハンドラー設定の例

### パターン 1: サブディレクトリ構成

```
コンテナ構造:
/var/task/
├── src/
│   └── main.py
└── requirements.txt
```

```dockerfile
COPY src/main.py ${LAMBDA_TASK_ROOT}/src/
CMD ["src.main.lambda_handler"]
```

### パターン 2: モジュール化構成

```
コンテナ構造:
/var/task/
├── handlers/
│   ├── __init__.py
│   └── api.py
```

```python title="handlers/api.py"
from lambapi import API, create_lambda_handler

def create_app(event, context):
    app = API(event, context)
    # ... API 定義
    return app

lambda_handler = create_lambda_handler(create_app)
```

```dockerfile
CMD ["handlers.api.lambda_handler"]
```

## ローカルテスト

### Docker でのローカルテスト

```bash
# イメージをビルド
docker build -t my-lambapi-app .

# ローカルでテスト実行
docker run -p 9000:8080 my-lambapi-app

# 別ターミナルでテスト
curl -X POST "http://localhost:9000/2015-03-31/functions/function/invocations" \
  -d '{
    "httpMethod": "GET",
    "path": "/",
    "headers": {},
    "body": null
  }'
```

### AWS SAM でのテスト

```yaml title="template.yaml"
AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31

Resources:
  lambapiFunction:
    Type: AWS::Serverless::Function
    Properties:
      PackageType: Image
      ImageUri: my-lambapi-app:latest
      Events:
        ApiGateway:
          Type: Api
          Properties:
            Path: /{proxy+}
            Method: ANY
```

```bash
sam local start-api
curl http://localhost:3000/
```

## API Gateway との統合

### プロキシ統合設定

Lambda 関数作成後、API Gateway を設定：

```bash
# API 作成
aws apigateway create-rest-api --name my-lambapi-container-api

# リソース設定
aws apigateway create-resource \
    --rest-api-id YOUR-API-ID \
    --parent-id YOUR-PARENT-ID \
    --path-part '{proxy+}'

# Lambda 統合設定
aws apigateway put-integration \
    --rest-api-id YOUR-API-ID \
    --resource-id YOUR-RESOURCE-ID \
    --http-method ANY \
    --type AWS_PROXY \
    --integration-http-method POST \
    --uri arn:aws:apigateway:region:lambda:path/2015-03-31/functions/arn:aws:lambda:region:account:function:my-lambapi-container/invocations
```

## パフォーマンス最適化

### イメージサイズの最小化

```dockerfile
# 不要ファイルを除外
.dockerignore:
.git
tests/
docs/
*.md
__pycache__/
```

### マルチステージビルドの活用

```dockerfile
# ビルド専用ステージでコンパイル
FROM python:3.13 as builder
RUN pip install --user package

# 本番ステージで必要なもののみコピー
FROM public.ecr.aws/lambda/python:3.13
COPY --from=builder /root/.local ${LAMBDA_TASK_ROOT}
```

### Cold Start の軽減

```python title="app.py"
# グローバルスコープで初期化
import boto3
dynamodb = boto3.resource('dynamodb')  # コンテナ再利用時に初期化省略

def create_app(event, context):
    # 既存の接続を再利用
    app = API(event, context)
    return app
```

## トラブルシューティング

### よくある問題

1. **CMD 設定エラー**
   ```
   エラー: Handler 'app.lambda_handler' missing on image
   解決: Dockerfile の CMD を確認
   ```

2. **イメージサイズエラー**
   ```
   エラー: Image size too large
   解決: マルチステージビルドを使用
   ```

3. **権限エラー**
   ```
   エラー: Access denied to ECR
   解決: aws ecr get-login-password を実行
   ```

4. **メモリ不足**
   ```
   エラー: Task timed out
   解決: メモリサイズを 512MB 以上に設定
   ```

### デバッグ用設定

```python title="app.py"
import os
import logging

# デバッグモード
if os.getenv('DEBUG') == 'true':
    logging.basicConfig(level=logging.DEBUG)
    
def create_app(event, context):
    app = API(event, context)
    
    @app.get("/debug")
    def debug_info():
        return {
            "container_info": {
                "image_uri": os.getenv('AWS_LAMBDA_FUNCTION_NAME'),
                "memory_limit": context.memory_limit_in_mb,
                "remaining_time": context.get_remaining_time_in_millis()
            },
            "environment": dict(os.environ)
        }
    
    return app
```

この設定により、ECR コンテナイメージでの lambapi 実行が可能になります。