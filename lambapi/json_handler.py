"""
JSON 処理統一ハンドラー

Lambda 環境での高速 JSON 処理を提供します。
パフォーマンス最適化と一貫性のあるエラーハンドリングを実現します。
"""

import json
from typing import Dict, Any, Union, Optional

# オプション: orjson による更なる高速化
try:
    import orjson

    HAS_ORJSON = True
except ImportError:
    HAS_ORJSON = False


class JSONHandler:
    """高速 JSON 処理の統一インターフェース"""

    @staticmethod
    def loads(data: Union[str, bytes, None]) -> Dict[str, Any]:
        """
        安全で高速な JSON パース

        Args:
            data: JSON 文字列またはバイト列

        Returns:
            Dict[str, Any]: パースされた辞書オブジェクト

        Note:
            無効な JSON や空データの場合は空辞書を返します
        """
        if not data:
            return {}

        try:
            if HAS_ORJSON:
                # orjson は文字列とバイト列の両方を受け入れる
                result = orjson.loads(data)
                return result if isinstance(result, dict) else {}
            else:
                # 標準 json モジュールは文字列のみ
                if isinstance(data, bytes):
                    data = data.decode("utf-8")
                result = json.loads(data)
                return result if isinstance(result, dict) else {}
        except (json.JSONDecodeError, UnicodeDecodeError, TypeError):
            return {}

    @staticmethod
    def dumps(data: Any, ensure_ascii: bool = False, indent: Optional[int] = None) -> str:
        """
        高速 JSON シリアライズ

        Args:
            data: シリアライズするオブジェクト
            ensure_ascii: ASCII エンコーディングを強制するか
            indent: インデントレベル（None で最小化）

        Returns:
            str: JSON 文字列

        Note:
            Lambda 環境での転送効率化のため、デフォルトで最小化されます
        """
        try:
            if HAS_ORJSON:
                option = 0
                if not ensure_ascii:
                    option |= orjson.OPT_NON_STR_KEYS
                if indent is not None:
                    option |= orjson.OPT_INDENT_2

                result = orjson.dumps(data, option=option)
                return result.decode("utf-8") if isinstance(result, bytes) else str(result)
            else:
                separators = (",", ":") if indent is None else (",", ": ")
                return json.dumps(
                    data, ensure_ascii=ensure_ascii, separators=separators, indent=indent
                )
        except (TypeError, ValueError) as e:
            # シリアライズできない場合はエラー情報を含む辞書を返す
            error_data = {
                "error": "JSON serialization failed",
                "message": str(e),
                "type": type(data).__name__,
            }
            return json.dumps(error_data, ensure_ascii=ensure_ascii)

    @staticmethod
    def is_json_string(data: str) -> bool:
        """
        文字列が有効な JSON かどうかを判定

        Args:
            data: 判定する文字列

        Returns:
            bool: 有効な JSON の場合 True
        """
        if not data or not isinstance(data, str):
            return False

        try:
            result = JSONHandler.loads(data)
            return isinstance(result, dict) and bool(result)
        except Exception:
            return False

    @staticmethod
    def safe_get(data: Union[Dict[str, Any], Any], key: str, default: Any = None) -> Any:
        """
        辞書から安全にキーを取得

        Args:
            data: 検索対象の辞書（または任意のオブジェクト）
            key: 取得するキー
            default: デフォルト値

        Returns:
            Any: 取得した値またはデフォルト値
        """
        if not isinstance(data, dict):
            return default
        return data.get(key, default)


# 下位互換性のためのエイリアス
json_loads = JSONHandler.loads
json_dumps = JSONHandler.dumps
