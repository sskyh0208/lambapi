# Lambda ZIP デプロイ例

このディレクトリには、lambapi アプリケーションを ZIP アーカイブとして AWS Lambda にデプロイするための完全な例が含まれています。

## ファイル構成

```
lambda-zip-deploy/
├── app.py              # メインアプリケーション
├── requirements.txt    # Python 依存関係
├── deploy.sh          # デプロイスクリプト
└── README.md          # このファイル
```

## 前提条件

1. **AWS CLI の設定**
   ```bash
   aws configure
   ```

2. **Python 環境**
   ```bash
   python3 --version  # 3.13 以上推奨
   pip3 --version
   ```

3. **IAM ロールの作成**
   Lambda 実行用のロールが必要です：
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": [
           "logs:CreateLogGroup",
           "logs:CreateLogStream", 
           "logs:PutLogEvents"
         ],
         "Resource": "arn:aws:logs:*:*:*"
       }
     ]
   }
   ```

## デプロイ方法

### 1. 手動デプロイ

```bash
# このディレクトリに移動
cd examples/lambda-zip-deploy

# デプロイスクリプトを実行
./deploy.sh
```

### 2. 関数名とリージョンを指定

```bash
./deploy.sh my-custom-function us-east-1
```

### 3. 初回デプロイ（関数作成）

```bash
# Lambda 関数を作成
aws lambda create-function \
    --function-name my-lambapi-function \
    --runtime python3.13 \
    --role arn:aws:iam::YOUR-ACCOUNT-ID:role/lambda-execution-role \
    --handler app.lambda_handler \
    --zip-file fileb://lambda-deployment.zip \
    --timeout 30 \
    --memory-size 256 \
    --environment Variables='{
        "ENVIRONMENT":"production",
        "LOG_LEVEL":"INFO"
    }'

# API Gateway の設定
aws apigateway create-rest-api \
    --name my-lambapi-api \
    --description "lambapi sample API"

# プロキシ統合の設定（リソース ID は上記コマンドの結果から取得）
aws apigateway put-integration \
    --rest-api-id YOUR-API-ID \
    --resource-id YOUR-RESOURCE-ID \
    --http-method ANY \
    --type AWS_PROXY \
    --integration-http-method POST \
    --uri arn:aws:apigateway:ap-northeast-1:lambda:path/2015-03-31/functions/arn:aws:lambda:ap-northeast-1:YOUR-ACCOUNT:function:my-lambapi-function/invocations
```

## ローカルテスト

デプロイ前にローカルでテストできます：

```bash
# Python でローカル実行
python3 app.py

# または lambapi CLI を使用
lambapi serve app
```

## API テスト

デプロイ後、以下の方法でテストできます：

### curl を使用

```bash
# API Gateway URL を取得
API_URL=$(aws apigateway get-rest-apis \
    --query 'items[?name==`my-lambapi-api`].id' \
    --output text)
BASE_URL="https://${API_URL}.execute-api.ap-northeast-1.amazonaws.com/prod"

# ヘルスチェック
curl "${BASE_URL}/"

# ユーザー一覧
curl "${BASE_URL}/users"

# ユーザー作成
curl -X POST "${BASE_URL}/users" \
    -H "Content-Type: application/json" \
    -d '{"name":"Test User","email":"test@example.com","age":25}'

# 特定ユーザー取得
curl "${BASE_URL}/users/1"
```

### AWS CLI を使用（直接 Lambda 呼び出し）

```bash
# Lambda 関数を直接呼び出し
aws lambda invoke \
    --function-name my-lambapi-function \
    --payload '{
        "httpMethod": "GET",
        "path": "/",
        "headers": {},
        "body": null
    }' \
    response.json

cat response.json
```

## 監視とログ

### CloudWatch ログの確認

```bash
# ログストリームを確認
aws logs describe-log-streams \
    --log-group-name "/aws/lambda/my-lambapi-function" \
    --order-by LastEventTime \
    --descending \
    --max-items 1

# 最新のログを取得
aws logs get-log-events \
    --log-group-name "/aws/lambda/my-lambapi-function" \
    --log-stream-name "LATEST-STREAM-NAME"
```

### メトリクスの確認

```bash
# Lambda メトリクスを取得
aws cloudwatch get-metric-statistics \
    --namespace AWS/Lambda \
    --metric-name Duration \
    --dimensions Name=FunctionName,Value=my-lambapi-function \
    --statistics Average \
    --start-time 2025-01-01T00:00:00Z \
    --end-time 2025-01-01T23:59:59Z \
    --period 3600
```

## トラブルシューティング

### よくある問題

1. **パッケージサイズエラー**
   ```bash
   # 不要ファイルを除外して ZIP を再作成
   zip -r lambda-deployment.zip . -x "*.pyc" "*__pycache__*" "tests/*" "docs/*"
   ```

2. **インポートエラー**
   ```bash
   # パッケージ構造を確認
   unzip -l lambda-deployment.zip | head -20
   ```

3. **権限エラー**
   ```bash
   # Lambda 実行ロールに必要な権限を追加
   aws iam attach-role-policy \
       --role-name lambda-execution-role \
       --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
   ```

4. **タイムアウトエラー**
   ```bash
   # タイムアウト時間を延長
   aws lambda update-function-configuration \
       --function-name my-lambapi-function \
       --timeout 60
   ```

## パフォーマンス最適化

### Cold Start の軽減

```python
# グローバルスコープで初期化（app.py に追加）
import boto3

# 接続を再利用
dynamodb = boto3.resource('dynamodb')  # 初回のみ実行

def create_app(event, context):
    # dynamodb を再利用
    app = API(event, context)
    return app
```

### メモリサイズの最適化

```bash
# メモリサイズを調整（128MB〜10GB）
aws lambda update-function-configuration \
    --function-name my-lambapi-function \
    --memory-size 512
```

### 依存関係の最適化

```bash
# Layer を使用して依存関係を分離
mkdir -p layer/python
pip install lambapi boto3 -t layer/python/

zip -r lambapi-layer.zip layer/

aws lambda publish-layer-version \
    --layer-name lambapi-dependencies \
    --zip-file fileb://lambapi-layer.zip \
    --compatible-runtimes python3.13
```

## セキュリティ

### 環境変数での設定管理

```bash
# 機密情報は環境変数で管理
aws lambda update-function-configuration \
    --function-name my-lambapi-function \
    --environment Variables='{
        "DATABASE_URL":"your-db-url",
        "API_KEY":"your-api-key",
        "ENVIRONMENT":"production"
    }'
```

### VPC 設定（必要な場合）

```bash
aws lambda update-function-configuration \
    --function-name my-lambapi-function \
    --vpc-config SubnetIds=subnet-12345,SecurityGroupIds=sg-12345
```

このサンプルを参考に、実際のプロジェクトに合わせてカスタマイズしてください。