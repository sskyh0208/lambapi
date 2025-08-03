"""
CORS (Cross-Origin Resource Sharing) 機能

API Gateway + Lambda での CORS プリフライトリクエスト自動処理を提供します。
"""

from typing import Dict, List, Optional, Union
from dataclasses import dataclass


@dataclass
class CORSConfig:
    """CORS 設定クラス"""

    origins: Union[str, List[str]] = "*"
    methods: Optional[List[str]] = None
    headers: Optional[List[str]] = None
    allow_credentials: bool = False
    max_age: Optional[int] = None
    expose_headers: Optional[List[str]] = None

    def __post_init__(self) -> None:
        """初期化後の処理"""
        if self.methods is None:
            self.methods = ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]

        if self.headers is None:
            self.headers = ["Content-Type", "Authorization", "X-Requested-With"]

    def get_origin_header(self, request_origin: Optional[str] = None) -> str:
        """Origin ヘッダーの値を取得"""
        if self.origins == "*":
            return "*"

        if isinstance(self.origins, str):
            return self.origins

        # リスト形式の場合、リクエストオリジンがリストに含まれるかチェック
        if request_origin and request_origin in self.origins:
            return request_origin

        # デフォルトで最初のオリジンを返す
        return self.origins[0] if self.origins else "*"

    def get_cors_headers(self, request_origin: Optional[str] = None) -> Dict[str, str]:
        """CORS ヘッダーを生成"""
        headers = {
            "Access-Control-Allow-Origin": self.get_origin_header(request_origin),
            "Access-Control-Allow-Methods": ", ".join(self.methods or []),
            "Access-Control-Allow-Headers": ", ".join(self.headers or []),
        }

        if self.allow_credentials:
            headers["Access-Control-Allow-Credentials"] = "true"

        if self.max_age is not None:
            headers["Access-Control-Max-Age"] = str(self.max_age)

        if self.expose_headers:
            headers["Access-Control-Expose-Headers"] = ", ".join(self.expose_headers)

        return headers


def create_cors_config(
    origins: Union[str, List[str]] = "*",
    methods: Optional[List[str]] = None,
    headers: Optional[List[str]] = None,
    allow_credentials: bool = False,
    max_age: Optional[int] = None,
    expose_headers: Optional[List[str]] = None,
) -> CORSConfig:
    """CORS 設定を作成するヘルパー関数"""
    return CORSConfig(
        origins=origins,
        methods=methods,
        headers=headers,
        allow_credentials=allow_credentials,
        max_age=max_age,
        expose_headers=expose_headers,
    )
