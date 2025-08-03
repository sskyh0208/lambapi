"""
Request クラス

Lambda イベントからモダンな Request オブジェクトを提供します。
"""

from typing import Dict, Any, Optional
from urllib.parse import unquote

from .json_handler import JSONHandler


class Request:
    """モダンな Request オブジェクト"""

    def __init__(self, event: Dict[str, Any]) -> None:
        self.event = event
        self._body: Optional[str] = None
        self._json: Optional[Dict[str, Any]] = None

    @property
    def method(self) -> str:
        """HTTP メソッドを取得"""
        return str(self.event.get("httpMethod", "GET"))

    @property
    def path(self) -> str:
        """リクエストパスを取得"""
        return str(self.event.get("path", "/"))

    @property
    def query_params(self) -> Dict[str, str]:
        """クエリパラメータを取得"""
        params = self.event.get("queryStringParameters") or {}
        return {k: unquote(str(v)) for k, v in params.items()}

    @property
    def headers(self) -> Dict[str, str]:
        """リクエストヘッダーを取得"""
        headers = self.event.get("headers", {})
        return {k: str(v) for k, v in headers.items()}

    @property
    def body(self) -> str:
        """リクエストボディを取得"""
        if self._body is None:
            self._body = str(self.event.get("body", ""))
        return self._body

    def json(self) -> Dict[str, Any]:
        """JSON ボディをパース（最適化版）"""
        if self._json is None:
            self._json = JSONHandler.loads(self.body)
        return self._json

    @property
    def path_params(self) -> Dict[str, str]:
        """パスパラメータを取得"""
        params = self.event.get("pathParameters") or {}
        return {k: str(v) for k, v in params.items()}
