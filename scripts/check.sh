#!/bin/bash
# Pre-commit チェックをローカルで実行するスクリプト
# Usage: ./scripts/check.sh [--fix]

set -e

# カラー設定
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ヘルプ表示
show_help() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --fix    自動修正可能な問題を修正する"
    echo "  --help   このヘルプを表示"
    echo ""
    echo "実行される チェック:"
    echo "  - Black (フォーマット)"
    echo "  - Flake8 (リンター)"
    echo "  - MyPy (型チェック)"
    echo "  - Bandit (セキュリティチェック)"
    echo "  - ファイル基本チェック"
    echo "  - pytest (テスト)"
}

# エラーカウンター
error_count=0

# 実行結果を記録する関数
run_check() {
    local name="$1"
    local command="$2"
    
    echo -e "${BLUE}🔍 $name を実行中...${NC}"
    if eval "$command"; then
        echo -e "${GREEN}✅ $name: 成功${NC}"
    else
        echo -e "${RED}❌ $name: 失敗${NC}"
        ((error_count++))
    fi
    echo ""
}

# オプション解析
FIX_MODE=false
while [[ $# -gt 0 ]]; do
    case $1 in
        --fix)
            FIX_MODE=true
            shift
            ;;
        --help|-h)
            show_help
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

echo -e "${YELLOW}🚀 Pre-commit チェックを開始します...${NC}"
echo ""

# 1. Black (フォーマット)
if [ "$FIX_MODE" = true ]; then
    run_check "Black (自動修正)" "black ."
else
    run_check "Black (チェックのみ)" "black --check --diff ."
fi

# 2. Flake8 (リンター)
run_check "Flake8" "flake8 ."

# 3. MyPy (型チェック)
run_check "MyPy" "mypy lambapi/ --exclude lambapi/templates/"

# 4. Bandit (セキュリティチェック)
run_check "Bandit" "bandit -r lambapi/"

# 5. pytest (テスト)
run_check "pytest" "pytest tests/ -v --cov=lambapi --cov-report=xml --cov-report=term-missing"

# 結果サマリー
echo -e "${YELLOW}📊 チェック結果サマリー${NC}"
echo "=================================="

if [ $error_count -eq 0 ]; then
    echo -e "${GREEN}🎉 すべてのチェックが成功しました！${NC}"
    exit 0
else
    echo -e "${RED}❌ $error_count 個のチェックが失敗しました${NC}"
    echo ""
    echo -e "${YELLOW}💡 修正可能な問題がある場合は --fix オプションを使用してください:${NC}"
    echo "   ./scripts/check.sh --fix"
    exit 1
fi