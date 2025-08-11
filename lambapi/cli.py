"""
lambapi CLI ツール
pip install lambapi 後に使用可能なコマンドライン インターフェース
"""

import argparse
import sys
import os
from .template_loader import TemplateLoader


def create_project() -> None:
    """新しい lambapi プロジェクトを作成（旧形式、下位互換性のため保持）"""
    parser = argparse.ArgumentParser(description="新しい lambapi プロジェクトを作成")
    parser.add_argument("project_name", help="プロジェクト名")
    parser.add_argument(
        "--template",
        choices=["basic", "crud"],
        default="basic",
        help="プロジェクトテンプレート (デフォルト: basic)",
    )

    args = parser.parse_args(sys.argv[2:])
    create_project_with_args(args.project_name, args.template)


def create_project_with_args(project_name: str, template: str = "basic") -> None:
    """新しい lambapi プロジェクトを作成"""
    project_dir = project_name

    if os.path.exists(project_dir):
        print(f"❌ エラー: ディレクトリ '{project_dir}' は既に存在します")
        sys.exit(1)

    # プロジェクトディレクトリを作成
    os.makedirs(project_dir)

    if template == "basic":
        create_basic_project(project_dir)
    elif template == "crud":
        create_crud_project(project_dir)

    print(
        f"""
✅ プロジェクト '{project_name}' を作成しました！

🚀 開始方法:
   cd {project_dir}
   pip install -r requirements.txt
   lambapi serve app

📖 詳細: README.md を参照してください
"""
    )


def create_basic_project(project_dir: str) -> None:
    """基本的なプロジェクトテンプレートを作成"""
    loader = TemplateLoader()
    project_name = os.path.basename(project_dir)

    # テンプレートファイルを取得
    templates = loader.get_template_files("basic")

    # ファイル作成
    for filename, content in templates.items():
        if filename == "README.md":
            # README.md は project_name を置換
            content = content.format(project_name=project_name)

        with open(os.path.join(project_dir, filename), "w", encoding="utf-8") as f:
            f.write(content)


def create_crud_project(project_dir: str) -> None:
    """CRUD プロジェクトテンプレートを作成"""
    loader = TemplateLoader()
    project_name = os.path.basename(project_dir)

    # テンプレートファイルを取得
    templates = loader.get_template_files("crud")

    # ファイル作成
    for filename, content in templates.items():
        if filename == "README.md":
            # README.md は project_name を置換
            content = content.format(project_name=project_name)

        with open(os.path.join(project_dir, filename), "w", encoding="utf-8") as f:
            f.write(content)


def main() -> None:
    """メイン CLI エントリーポイント"""
    parser = argparse.ArgumentParser(description="lambapi CLI")
    subparsers = parser.add_subparsers(dest="command", help="利用可能なコマンド")

    # serve コマンド
    serve_parser = subparsers.add_parser("serve", help="ローカル開発サーバーを起動")
    serve_parser.add_argument("app", help="アプリケーションファイル (例: app, app.py)")
    serve_parser.add_argument("--host", default="localhost", help="バインドするホスト")
    serve_parser.add_argument("--port", type=int, default=8000, help="ポート番号")
    serve_parser.add_argument("--debug", action="store_true", help="詳細なデバッグ情報を表示")

    # uvicorn 関連オプション
    serve_parser.add_argument(
        "--reload", action="store_true", default=True, help="ホットリロードを有効化 (デフォルト)"
    )
    serve_parser.add_argument(
        "--no-reload", action="store_false", dest="reload", help="ホットリロードを無効化"
    )
    serve_parser.add_argument("--workers", type=int, default=1, help="ワーカープロセス数")
    serve_parser.add_argument("--access-log", action="store_true", help="アクセスログを有効化")
    serve_parser.add_argument(
        "--no-access-log", action="store_false", dest="access_log", help="アクセスログを無効化"
    )
    serve_parser.add_argument(
        "--log-level",
        choices=["critical", "error", "warning", "info", "debug", "trace"],
        default="info",
        help="ログレベル",
    )

    # create コマンド
    create_parser = subparsers.add_parser("create", help="新しいプロジェクトを作成")
    create_parser.add_argument("project_name", help="プロジェクト名")
    create_parser.add_argument(
        "--template", choices=["basic", "crud"], default="basic", help="プロジェクトテンプレート"
    )

    args = parser.parse_args()

    if args.command == "serve":
        # uvicorn サーバー起動
        from .uvicorn_server import serve_with_uvicorn

        # uvicorn 設定
        uvicorn_kwargs = {
            "workers": args.workers,
            "log_level": "debug" if args.debug else args.log_level,
        }

        # アクセスログの設定
        if hasattr(args, "access_log"):
            uvicorn_kwargs["access_log"] = args.access_log

        serve_with_uvicorn(
            app_path=args.app,
            host=args.host,
            port=args.port,
            reload=args.reload,
            debug=args.debug,
            **uvicorn_kwargs,
        )
    elif args.command == "create":
        # プロジェクト作成
        create_project_with_args(args.project_name, args.template)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
