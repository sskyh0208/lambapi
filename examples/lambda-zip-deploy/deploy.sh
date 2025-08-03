#!/bin/bash
set -e

echo "🚀 Lambda ZIP デプロイを開始します..."

# 設定
FUNCTION_NAME="${1:-my-lambapi-function}"
REGION="${2:-ap-northeast-1}"

# 作業ディレクトリを作成
rm -rf deploy
mkdir -p deploy

# 依存関係をインストール
echo "📦 依存関係をインストール中..."
pip install -r requirements.txt -t deploy/

# アプリケーションファイルをコピー
echo "📁 アプリケーションファイルをコピー中..."
cp app.py deploy/

# ZIP ファイルを作成
echo "🗜️  ZIP ファイルを作成中..."
cd deploy
zip -r ../lambda-deployment.zip . -x "*.pyc" "*__pycache__*" "*.git*"
cd ..

echo "✅ デプロイパッケージが作成されました: lambda-deployment.zip"
echo "📊 パッケージサイズ: $(du -h lambda-deployment.zip | cut -f1)"

# Lambda 関数の存在確認
if aws lambda get-function --function-name "$FUNCTION_NAME" --region "$REGION" >/dev/null 2>&1; then
    echo "🔄 既存の Lambda 関数を更新中..."
    aws lambda update-function-code \
        --function-name "$FUNCTION_NAME" \
        --zip-file fileb://lambda-deployment.zip \
        --region "$REGION"
    echo "✅ Lambda 関数の更新完了!"
else
    echo "❌ Lambda 関数 '$FUNCTION_NAME' が見つかりません"
    echo "💡 以下のコマンドで関数を作成してください:"
    echo "aws lambda create-function \\"
    echo "    --function-name $FUNCTION_NAME \\"
    echo "    --runtime python3.13 \\"
    echo "    --role arn:aws:iam::YOUR-ACCOUNT:role/lambda-execution-role \\"
    echo "    --handler app.lambda_handler \\"
    echo "    --zip-file fileb://lambda-deployment.zip \\"
    echo "    --timeout 30 \\"
    echo "    --memory-size 256 \\"
    echo "    --region $REGION"
fi

# クリーンアップ
echo "🧹 一時ファイルをクリーンアップ中..."
rm -rf deploy

echo "🎉 デプロイ処理完了!"