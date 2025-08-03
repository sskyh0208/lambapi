"""
Response クラス

Lambda 用のレスポンスオブジェクトを提供します。
"""

from typing import Dict, Any, Optional

from .json_handler import JSONHandler


class Response:
    """レスポンスオブジェクト"""

    def __init__(
        self, content: Any = None, status_code: int = 200, headers: Optional[Dict[str, str]] = None
    ):
        self.content = content
        self.status_code = status_code
        self.headers = headers or {}

    def to_lambda_response(self) -> Dict[str, Any]:
        """Lambda 用のレスポンス形式に変換"""
        body = self.content
        if isinstance(body, (dict, list)):
            body = JSONHandler.dumps(body, ensure_ascii=False)
            self.headers.setdefault("Content-Type", "application/json")
        elif body is None:
            body = ""

        return {"statusCode": self.status_code, "headers": self.headers, "body": str(body)}
