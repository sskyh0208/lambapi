#!/bin/bash
# Pre-commit フックのセットアップスクリプト

set -e

echo "🚀 Pre-commit フックをセットアップしています..."

# pre-commit のインストール確認
if ! command -v pre-commit &> /dev/null; then
    echo "📦 pre-commit をインストールしています..."
    pip install pre-commit
fi

# pre-commit フックのインストール
echo "🔧 Pre-commit フックをインストールしています..."
pre-commit install

# 初回実行（全ファイルに対して）
echo "🧪 初回チェックを実行しています..."
pre-commit run --all-files || {
    echo "⚠️  初回チェックで問題が見つかりました。"
    echo "   修正されたファイルがある場合は、変更を確認してコミットしてください。"
    exit 1
}

echo "✅ Pre-commit フックのセットアップが完了しました！"
echo ""
echo "📝 使用方法:"
echo "   - 通常のコミット時に自動実行されます"
echo "   - 手動実行: pre-commit run --all-files"
echo "   - 特定ファイルのみ: pre-commit run --files <file1> <file2>"
echo "   - フックをスキップ: git commit --no-verify"
