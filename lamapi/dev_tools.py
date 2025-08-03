"""
lambapi 開発ツール
pip install lambapi 後に使用可能な開発用ユーティリティ
"""

from .local_server import start_server, load_lambda_handler


def serve(app_path: str, host: str = "localhost", port: int = 8000) -> None:
    """
    ローカル開発サーバーを起動する関数

    Args:
        app_path: アプリケーションファイルのパス
        host: バインドするホスト
        port: ポート番号
    """
    lambda_handler = load_lambda_handler(app_path)
    if lambda_handler:
        start_server(lambda_handler, host, port)
    else:
        raise ValueError(f"Could not load lambda_handler from {app_path}")


__all__ = ["serve"]
