#!/bin/bash

# リントスクリプト - コード品質チェック
set -e

echo "🔍 コード品質チェックを開始します..."

echo "📋 Black でフォーマットチェック中..."
black --check --diff .

echo "🧹 Flake8 でリント実行中..."
flake8 .

echo "🔍 MyPy で型チェック実行中..."
mypy lambapi/

echo "✅ すべてのコード品質チェックが完了しました！"