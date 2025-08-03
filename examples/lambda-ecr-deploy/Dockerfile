# lambapi ECR デプロイ用 Dockerfile
FROM public.ecr.aws/lambda/python:3.13

# システムパッケージの更新（必要に応じて）
RUN yum update -y

# アプリケーションディレクトリを作成
WORKDIR ${LAMBDA_TASK_ROOT}

# requirements.txt をコピーして依存関係をインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションコードをコピー
COPY app.py .

# 設定ファイルなどがあればコピー
# COPY config/ ./config/
# COPY utils/ ./utils/

# Python パスを設定
ENV PYTHONPATH="${LAMBDA_TASK_ROOT}:${PYTHONPATH}"

# 環境変数のデフォルト値
ENV ENVIRONMENT=production
ENV LOG_LEVEL=INFO
ENV LOG_FORMAT=json

# Lambda ハンドラーを指定
CMD ["app.lambda_handler"]