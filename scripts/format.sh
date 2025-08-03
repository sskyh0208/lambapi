#!/bin/bash

# フォーマットスクリプト - コード自動フォーマット
set -e

echo "🎨 コードフォーマットを開始します..."

echo "✨ Black でコードフォーマット実行中..."
black .

echo "🔧 インポート文を isort で整理中..."
isort . --profile black

echo "✅ コードフォーマットが完了しました！"