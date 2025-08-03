#!/bin/bash

# テストスクリプト - テストスイート実行
set -e

echo "🧪 テストスイートを開始します..."

echo "📊 pytest でテスト実行中..."
pytest tests/ -v \
    --cov=lambapi \
    --cov-report=xml \
    --cov-report=term-missing \
    --cov-report=html \
    --cov-fail-under=80

echo "✅ すべてのテストが完了しました！"