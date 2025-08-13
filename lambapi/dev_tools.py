"""
lambapi 開発ツール
pip install lambapi 後に使用可能な開発用ユーティリティ
"""

from .uvicorn_server import serve_with_uvicorn


def serve(app_path: str, host: str = "localhost", port: int = 8000) -> None:
    """
    ローカル開発サーバーを起動する関数

    Args:
        app_path: アプリケーションファイルのパス
        host: バインドするホスト
        port: ポート番号
    """
    serve_with_uvicorn(app_path=app_path, host=host, port=port, reload=True)


__all__ = ["serve"]
