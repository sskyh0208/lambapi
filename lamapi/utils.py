"""
ユーティリティ関数

Lambda API のヘルパー関数を提供します。
"""

from typing import Dict, Any, Callable
from .core import API


def create_lambda_handler(
    app_factory: Callable[[Dict[str, Any], Any], API],
) -> Callable[[Dict[str, Any], Any], Dict[str, Any]]:
    """Lambda 用のハンドラーを作成

    Args:
        app_factory: API インスタンスを作成する関数

    Returns:
        Lambda ハンドラー関数
    """

    def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
        app = app_factory(event, context)
        return app.handle_request()

    return lambda_handler
