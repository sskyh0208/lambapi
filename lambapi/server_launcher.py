#!/usr/bin/env python3
"""
ホットリロード用のサーバー起動スクリプト
"""


def main():
    """サーバー起動のメインエントリーポイント"""
    # lambapi.local_server のメイン関数を直接実行
    from lambapi.local_server import main as server_main

    server_main()


if __name__ == "__main__":
    main()
