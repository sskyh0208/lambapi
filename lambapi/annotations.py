"""
FastAPI 風のアノテーション機能

パラメータの由来と認証要件を明示的に指定するためのアノテーションクラスです。
"""

from typing import Any, List, Optional, Union
from dataclasses import dataclass


# ベースアノテーションクラス
@dataclass
class ParameterAnnotation:
    """パラメータアノテーションのベースクラス"""

    pass


# パラメータソース系アノテーション
@dataclass
class Body(ParameterAnnotation):
    """リクエストボディからパラメータを取得"""

    pass


@dataclass
class Path(ParameterAnnotation):
    """パスパラメータからパラメータを取得"""

    pass


@dataclass
class Query(ParameterAnnotation):
    """クエリパラメータからパラメータを取得

    Args:
        default: デフォルト値
        alias: クエリパラメータ名のエイリアス
    """

    default: Any = None
    alias: Optional[str] = None


@dataclass
class Header(ParameterAnnotation):
    """ヘッダーからパラメータを取得

    Args:
        alias: ヘッダー名のエイリアス
    """

    alias: Optional[str] = None


# 認証系アノテーション
@dataclass
class AuthAnnotation(ParameterAnnotation):
    """認証アノテーションのベースクラス"""

    pass


@dataclass
class CurrentUser(AuthAnnotation):
    """現在のログイン済みユーザーを取得

    JWT トークンが必要で、有効でない場合は 401 エラーを返します。
    """

    pass


@dataclass
class RequireRole(AuthAnnotation):
    """指定されたロールを持つユーザーを取得

    JWT トークンが必要で、指定されたロールを持たない場合は 403 エラーを返します。

    Args:
        roles: 必要なロール（文字列または文字列のリスト）
    """

    roles: Union[str, List[str]]

    def __post_init__(self) -> None:
        if isinstance(self.roles, str):
            self.roles = [self.roles]


@dataclass
class OptionalAuth(AuthAnnotation):
    """オプショナルな認証ユーザーを取得

    JWT トークンがある場合は検証してユーザーを返し、ない場合は None を返します。
    エラーは発生しません。
    """

    pass


# アノテーションの判定用ヘルパー関数
def is_parameter_annotation(obj: Any) -> bool:
    """オブジェクトがパラメータアノテーションかどうかを判定"""
    return isinstance(obj, ParameterAnnotation)


def is_auth_annotation(obj: Any) -> bool:
    """オブジェクトが認証アノテーションかどうかを判定"""
    return isinstance(obj, AuthAnnotation)


def is_body_annotation(obj: Any) -> bool:
    """オブジェクトが Body アノテーションかどうかを判定"""
    return isinstance(obj, Body)


def is_path_annotation(obj: Any) -> bool:
    """オブジェクトが Path アノテーションかどうかを判定"""
    return isinstance(obj, Path)


def is_query_annotation(obj: Any) -> bool:
    """オブジェクトが Query アノテーションかどうかを判定"""
    return isinstance(obj, Query)


def is_header_annotation(obj: Any) -> bool:
    """オブジェクトが Header アノテーションかどうかを判定"""
    return isinstance(obj, Header)


def is_current_user_annotation(obj: Any) -> bool:
    """オブジェクトが CurrentUser アノテーションかどうかを判定"""
    return isinstance(obj, CurrentUser)


def is_require_role_annotation(obj: Any) -> bool:
    """オブジェクトが RequireRole アノテーションかどうかを判定"""
    return isinstance(obj, RequireRole)


def is_optional_auth_annotation(obj: Any) -> bool:
    """オブジェクトが OptionalAuth アノテーションかどうかを判定"""
    return isinstance(obj, OptionalAuth)
