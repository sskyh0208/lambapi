"""
Dependencies モジュール

FastAPI 風の Query, Path, Body, Authenticated 依存性注入機能を提供します。
"""

from typing import Any, Optional, Dict, Callable
import inspect


class FieldInfo:
    """パラメータのメタデータを保持するベースクラス"""

    def __init__(
        self,
        default: Any = ...,
        alias: Optional[str] = None,
        description: Optional[str] = None,
        gt: Optional[float] = None,
        ge: Optional[float] = None,
        lt: Optional[float] = None,
        le: Optional[float] = None,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        regex: Optional[str] = None,
    ):
        self.default = default
        self.alias = alias or None
        self.description = description
        self.gt = gt
        self.ge = ge
        self.lt = lt
        self.le = le
        self.min_length = min_length
        self.max_length = max_length
        self.regex = regex

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(default={self.default!r})"

    def __bool__(self) -> bool:
        """JSON シリアライゼーション時の問題を避けるため False を返す"""
        return False

    def __str__(self) -> str:
        """文字列変換時はデフォルト値を返す"""
        return str(self.default) if self.default is not ... else ""


class QueryInfo(FieldInfo):
    """クエリパラメータの情報を保持するクラス"""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.source = "query"


class PathInfo(FieldInfo):
    """パスパラメータの情報を保持するクラス"""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.source = "path"


class BodyInfo(FieldInfo):
    """リクエストボディの情報を保持するクラス"""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.source = "body"


class AuthenticatedInfo(FieldInfo):
    """認証ユーザー情報を保持するクラス"""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.source = "authenticated"


# FastAPI 風のファクトリ関数
def Query(
    default: Any = ...,
    alias: Optional[str] = None,
    description: Optional[str] = None,
    gt: Optional[float] = None,
    ge: Optional[float] = None,
    lt: Optional[float] = None,
    le: Optional[float] = None,
    min_length: Optional[int] = None,
    max_length: Optional[int] = None,
    regex: Optional[str] = None,
) -> Any:
    """
    クエリパラメータを定義する

    Args:
        default: デフォルト値（... は必須を意味する）
        alias: パラメータ名のエイリアス
        description: パラメータの説明
        gt: 値が指定値より大きいこと（>）
        ge: 値が指定値以上であること（>=）
        lt: 値が指定値より小さいこと（<）
        le: 値が指定値以下であること（<=）
        min_length: 文字列の最小長
        max_length: 文字列の最大長
        regex: 正規表現パターン

    Returns:
        QueryInfo: クエリパラメータの情報
    """
    return QueryInfo(
        default=default,
        alias=alias,
        description=description,
        gt=gt,
        ge=ge,
        lt=lt,
        le=le,
        min_length=min_length,
        max_length=max_length,
        regex=regex,
    )


def Path(
    default: Any = ...,
    alias: Optional[str] = None,
    description: Optional[str] = None,
    gt: Optional[float] = None,
    ge: Optional[float] = None,
    lt: Optional[float] = None,
    le: Optional[float] = None,
    min_length: Optional[int] = None,
    max_length: Optional[int] = None,
    regex: Optional[str] = None,
) -> Any:
    """
    パスパラメータを定義する

    Args:
        default: デフォルト値（パスパラメータは通常必須なので ... を使用）
        alias: パラメータ名のエイリアス
        description: パラメータの説明
        gt: 値が指定値より大きいこと（>）
        ge: 値が指定値以上であること（>=）
        lt: 値が指定値より小さいこと（<）
        le: 値が指定値以下であること（<=）
        min_length: 文字列の最小長
        max_length: 文字列の最大長
        regex: 正規表現パターン

    Returns:
        PathInfo: パスパラメータの情報
    """
    return PathInfo(
        default=default,
        alias=alias,
        description=description,
        gt=gt,
        ge=ge,
        lt=lt,
        le=le,
        min_length=min_length,
        max_length=max_length,
        regex=regex,
    )


def Body(
    default: Any = ...,
    alias: Optional[str] = None,
    description: Optional[str] = None,
) -> Any:
    """
    リクエストボディを定義する

    Args:
        default: デフォルト値（... は必須を意味する）
        alias: パラメータ名のエイリアス
        description: パラメータの説明

    Returns:
        BodyInfo: リクエストボディの情報
    """
    return BodyInfo(
        default=default,
        alias=alias,
        description=description,
    )


def Authenticated(
    default: Any = ...,
    alias: Optional[str] = None,
    description: Optional[str] = None,
) -> Any:
    """
    認証されたユーザー情報を注入する

    Args:
        default: デフォルト値（認証は通常必須なので ... を使用）
        alias: パラメータ名のエイリアス
        description: パラメータの説明

    Returns:
        AuthenticatedInfo: 認証ユーザー情報
    """
    return AuthenticatedInfo(
        default=default,
        alias=alias,
        description=description,
    )


def get_parameter_info(param: inspect.Parameter) -> Optional[FieldInfo]:
    """
    関数パラメータから依存性情報を取得する

    Args:
        param: inspect.Parameter オブジェクト

    Returns:
        FieldInfo または None
    """
    if param.default is not inspect.Parameter.empty:
        if isinstance(param.default, FieldInfo):
            return param.default
    return None


def get_function_dependencies(func: Callable) -> Dict[str, FieldInfo]:
    """
    関数から全ての依存性情報を抽出する

    Args:
        func: 解析対象の関数

    Returns:
        パラメータ名をキーとした依存性情報の辞書
    """
    sig = inspect.signature(func)
    dependencies = {}

    for param_name, param in sig.parameters.items():
        field_info = get_parameter_info(param)
        if field_info is not None:
            dependencies[param_name] = field_info

    return dependencies


def is_dependency_parameter(param: inspect.Parameter) -> bool:
    """
    パラメータが依存性注入パラメータかどうかを判定する

    Args:
        param: inspect.Parameter オブジェクト

    Returns:
        bool: 依存性注入パラメータの場合 True
    """
    return get_parameter_info(param) is not None
