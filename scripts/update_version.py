#!/usr/bin/env python3
"""
バージョン更新スクリプト

使用例:
    python scripts/update_version.py 1.2.3
    python scripts/update_version.py --type patch
    python scripts/update_version.py --type minor
    python scripts/update_version.py --type major
"""

import argparse
import re
import sys
from pathlib import Path


def get_current_version():
    """現在のバージョンを取得"""
    init_file = Path("lambapi/__init__.py")
    if not init_file.exists():
        print("エラー: lambapi/__init__.py が見つかりません")
        return None

    content = init_file.read_text(encoding="utf-8")
    match = re.search(r'__version__ = ["\']([^"\']+)["\']', content)
    if not match:
        print("エラー: __version__ が見つかりません")
        return None

    return match.group(1)


def parse_version(version_str):
    """バージョン文字列を解析"""
    try:
        parts = version_str.split(".")
        if len(parts) != 3:
            raise ValueError
        return tuple(int(part) for part in parts)
    except ValueError:
        print(f"エラー: 無効なバージョン形式: {version_str}")
        return None


def increment_version(current_version, increment_type):
    """バージョンをインクリメント"""
    major, minor, patch = parse_version(current_version)
    if (major, minor, patch) == (None, None, None):
        return None

    if increment_type == "major":
        return f"{major + 1}.0.0"
    elif increment_type == "minor":
        return f"{major}.{minor + 1}.0"
    elif increment_type == "patch":
        return f"{major}.{minor}.{patch + 1}"
    else:
        print(f"エラー: 無効なインクリメントタイプ: {increment_type}")
        return None


def update_file_version(file_path, pattern, new_version):
    """ファイル内のバージョンを更新"""
    if not file_path.exists():
        print(f"警告: {file_path} が見つかりません")
        return False

    content = file_path.read_text(encoding="utf-8")
    new_content = re.sub(pattern, lambda m: m.group(0).replace(m.group(1), new_version), content)

    if content != new_content:
        file_path.write_text(new_content, encoding="utf-8")
        print(f"✓ {file_path} を更新しました")
        return True
    else:
        print(f"- {file_path} は変更されませんでした")
        return False


def update_all_versions(new_version):
    """全ファイルのバージョンを更新"""
    files_to_update = [
        (Path("lambapi/__init__.py"), r'__version__ = ["\']([^"\']+)["\']'),
        (Path("pyproject.toml"), r'version = ["\']([^"\']+)["\']'),
    ]

    updated_count = 0
    for file_path, pattern in files_to_update:
        if update_file_version(file_path, pattern, new_version):
            updated_count += 1

    return updated_count


def main():
    parser = argparse.ArgumentParser(description="バージョン更新スクリプト")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("version", nargs="?", help="新しいバージョン (例: 1.2.3)")
    group.add_argument(
        "--type", choices=["patch", "minor", "major"], help="バージョンインクリメントタイプ"
    )

    args = parser.parse_args()

    # 現在のバージョンを取得
    current_version = get_current_version()
    if not current_version:
        sys.exit(1)

    print(f"現在のバージョン: {current_version}")

    # 新しいバージョンを決定
    if args.version:
        new_version = args.version
        # バージョン形式を検証
        if not parse_version(new_version):
            sys.exit(1)
    else:
        new_version = increment_version(current_version, args.type)
        if not new_version:
            sys.exit(1)

    print(f"新しいバージョン: {new_version}")

    # 確認
    if current_version == new_version:
        print("バージョンに変更はありません")
        sys.exit(0)

    try:
        response = input("バージョンを更新しますか？ (y/N): ")
        if response.lower() not in ["y", "yes"]:
            print("キャンセルしました")
            sys.exit(0)
    except KeyboardInterrupt:
        print("\n キャンセルしました")
        sys.exit(0)

    # バージョン更新
    updated_count = update_all_versions(new_version)

    if updated_count > 0:
        print(f"\n✓ {updated_count} 個のファイルを更新しました")
        print(f"  {current_version} → {new_version}")
        print("\n 次のステップ:")
        print("  1. git add .")
        print(f'  2. git commit -m "chore: バージョンを v{new_version} に更新"')
        print(f"  3. git tag v{new_version}")
        print("  4. git push origin main --tags")
    else:
        print("更新されたファイルはありません")


if __name__ == "__main__":
    main()
