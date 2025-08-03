#!/bin/bash
set -e

# 設定
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION="${2:-ap-northeast-1}"
REPOSITORY_NAME="${1:-my-lambapi-app}"
IMAGE_TAG="${3:-latest}"
FUNCTION_NAME="${4:-my-lambapi-container}"
REPOSITORY_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${REPOSITORY_NAME}"

echo "🚀 ECR コンテナデプロイを開始します..."
echo "リポジトリ: ${REPOSITORY_NAME}"
echo "関数名: ${FUNCTION_NAME}"
echo "リージョン: ${AWS_REGION}"

# ECR リポジトリを作成（存在しない場合）
echo "📦 ECR リポジトリを確認中..."
aws ecr describe-repositories --repository-names ${REPOSITORY_NAME} --region ${AWS_REGION} >/dev/null 2>&1 || \
aws ecr create-repository --repository-name ${REPOSITORY_NAME} --region ${AWS_REGION}

# ECR にログイン
echo "🔐 ECR にログイン中..."
aws ecr get-login-password --region ${AWS_REGION} | \
docker login --username AWS --password-stdin ${REPOSITORY_URI}

# Docker イメージをビルド
echo "🔨 Docker イメージをビルド中..."
docker build -t ${REPOSITORY_NAME}:${IMAGE_TAG} .

# イメージにタグを付ける
echo "🏷️  イメージにタグを付与中..."
docker tag ${REPOSITORY_NAME}:${IMAGE_TAG} ${REPOSITORY_URI}:${IMAGE_TAG}

# ECR にプッシュ
echo "⬆️  ECR にプッシュ中..."
docker push ${REPOSITORY_URI}:${IMAGE_TAG}

# Lambda 関数を更新
echo "🔄 Lambda 関数を更新中..."
if aws lambda get-function --function-name ${FUNCTION_NAME} --region ${AWS_REGION} >/dev/null 2>&1; then
    aws lambda update-function-code \
        --function-name ${FUNCTION_NAME} \
        --image-uri ${REPOSITORY_URI}:${IMAGE_TAG} \
        --region ${AWS_REGION}
    echo "✅ 既存の Lambda 関数を更新しました"
else
    echo "❌ Lambda 関数 '${FUNCTION_NAME}' が見つかりません"
    echo "💡 以下のコマンドで作成してください:"
    echo "aws lambda create-function \\"
    echo "    --function-name ${FUNCTION_NAME} \\"
    echo "    --package-type Image \\"
    echo "    --code ImageUri=${REPOSITORY_URI}:${IMAGE_TAG} \\"
    echo "    --role arn:aws:iam::${AWS_ACCOUNT_ID}:role/lambda-execution-role \\"
    echo "    --timeout 30 \\"
    echo "    --memory-size 512 \\"
    echo "    --region ${AWS_REGION}"
fi

echo "🎉 デプロイ処理完了!"