"""
Dependency Resolver モジュール

依存性注入パラメータの解決・バリデーション処理を提供します。
"""

import re
import inspect
from typing import Any, Dict, Optional, Type, Callable, get_type_hints
from dataclasses import is_dataclass

from .dependencies import (
    FieldInfo,
    QueryInfo,
    PathInfo,
    BodyInfo,
    AuthenticatedInfo,
    get_function_dependencies,
)
from .validation import validate_and_convert
from .request import Request
from .exceptions import ValidationError


class DependencyResolver:
    """依存性注入パラメータの解決とバリデーションを行うクラス"""

    def __init__(self) -> None:
        # バリデーション結果のキャッシュ
        self._validation_cache: Dict[str, Any] = {}

    def resolve_dependencies(
        self,
        func: Callable,
        request: Request,
        path_params: Optional[Dict[str, str]] = None,
        authenticated_user: Any = None,
    ) -> Dict[str, Any]:
        """
        関数の依存性注入パラメータを解決する

        Args:
            func: 対象の関数
            request: Request オブジェクト
            path_params: パスパラメータの辞書
            authenticated_user: 認証済みユーザーオブジェクト

        Returns:
            解決されたパラメータの辞書

        Raises:
            ValidationError: バリデーションエラーが発生した場合
        """
        sig = inspect.signature(func)
        type_hints = get_type_hints(func)
        dependencies = get_function_dependencies(func)
        resolved_params = {}

        # 各パラメータを処理
        for param_name, param in sig.parameters.items():
            # 既存の request パラメータは従来通り処理（依存性注入が定義されていない場合のみ）
            if param_name in ["request", "req"] and dependencies.get(param_name) is None:
                resolved_params[param_name] = request
                continue

            # 依存性注入パラメータの処理
            field_info = dependencies.get(param_name)
            if field_info is not None:
                resolved_value = self._resolve_single_dependency(
                    param_name=param_name,
                    param=param,
                    field_info=field_info,
                    param_type=type_hints.get(param_name, str),
                    request=request,
                    path_params=path_params or {},
                    authenticated_user=authenticated_user,
                )
                resolved_params[param_name] = resolved_value

        return resolved_params

    def _resolve_single_dependency(
        self,
        param_name: str,
        param: inspect.Parameter,
        field_info: FieldInfo,
        param_type: Type,
        request: Request,
        path_params: Dict[str, str],
        authenticated_user: Any,
    ) -> Any:
        """
        単一の依存性注入パラメータを解決する

        Args:
            param_name: パラメータ名
            param: inspect.Parameter オブジェクト
            field_info: FieldInfo オブジェクト
            param_type: パラメータの型
            request: Request オブジェクト
            path_params: パスパラメータの辞書
            authenticated_user: 認証済みユーザーオブジェクト

        Returns:
            解決されたパラメータ値

        Raises:
            ValidationError: バリデーションエラーが発生した場合
        """
        try:
            if isinstance(field_info, QueryInfo):
                return self._resolve_query_param(param_name, field_info, param_type, request)
            elif isinstance(field_info, PathInfo):
                return self._resolve_path_param(param_name, field_info, param_type, path_params)
            elif isinstance(field_info, BodyInfo):
                return self._resolve_body_param(param_name, field_info, param_type, request)
            elif isinstance(field_info, AuthenticatedInfo):
                return self._resolve_authenticated_param(
                    param_name, field_info, param_type, authenticated_user
                )
            else:
                raise ValidationError(f"不明な依存性タイプ: {type(field_info)}")

        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError(
                f"パラメータ '{param_name}' の解決中にエラーが発生しました: {str(e)}"
            )

    def _resolve_query_param(
        self, param_name: str, field_info: QueryInfo, param_type: Type, request: Request
    ) -> Any:
        """クエリパラメータを解決する"""
        param_key = field_info.alias or param_name
        query_params = request.query_params

        if param_key in query_params:
            raw_value = query_params[param_key]
            return self._convert_and_validate_value(
                raw_value, param_type, field_info, param_name, "query parameter"
            )
        elif field_info.default is not ...:
            return field_info.default
        else:
            raise ValidationError(f"必須のクエリパラメータ '{param_name}' が不足しています")

    def _resolve_path_param(
        self, param_name: str, field_info: PathInfo, param_type: Type, path_params: Dict[str, str]
    ) -> Any:
        """パスパラメータを解決する"""
        param_key = field_info.alias or param_name

        if param_key in path_params:
            raw_value = path_params[param_key]
            return self._convert_and_validate_value(
                raw_value, param_type, field_info, param_name, "path parameter"
            )
        elif field_info.default is not ...:
            return field_info.default
        else:
            raise ValidationError(f"必須のパスパラメータ '{param_name}' が不足しています")

    def _resolve_body_param(
        self, param_name: str, field_info: BodyInfo, param_type: Type, request: Request
    ) -> Any:
        """リクエストボディを解決する"""
        try:
            json_data = request.json()

            if param_type == dict or param_type == Dict[str, Any]:
                # dict 型の場合はそのまま返す
                return json_data
            elif is_dataclass(param_type):
                # dataclass の場合はバリデーションして変換
                return validate_and_convert(json_data, param_type)
            elif self._is_pydantic_model(param_type):
                # Pydantic Model の場合はバリデーションして変換
                return param_type(**json_data)
            else:
                # その他の型の場合も try to convert
                return self._convert_and_validate_value(
                    json_data, param_type, field_info, param_name, "request body"
                )
        except Exception as e:
            if field_info.default is not ...:
                return field_info.default
            else:
                raise ValidationError(
                    f"リクエストボディ '{param_name}' の解析に失敗しました: {str(e)}"
                )

    def _resolve_authenticated_param(
        self,
        param_name: str,
        field_info: AuthenticatedInfo,
        param_type: Type,
        authenticated_user: Any,
    ) -> Any:
        """認証ユーザーパラメータを解決する"""
        if authenticated_user is not None:
            return authenticated_user
        elif field_info.default is not ...:
            return field_info.default
        else:
            raise ValidationError(f"認証が必要ですが、ユーザーが認証されていません")

    def _convert_and_validate_value(
        self,
        raw_value: Any,
        target_type: Type,
        field_info: FieldInfo,
        param_name: str,
        param_source: str,
    ) -> Any:
        """値を指定された型に変換し、バリデーションを実行する"""
        try:
            # 基本的な型変換
            converted_value = self._convert_basic_type(raw_value, target_type)

            # フィールド固有のバリデーション実行
            self._validate_field_constraints(converted_value, field_info, param_name, param_source)

            return converted_value

        except ValueError as e:
            raise ValidationError(f"{param_source} '{param_name}': {str(e)}")

    def _is_pydantic_model(self, param_type: Type) -> bool:
        """パラメータタイプが Pydantic の Model かチェック"""
        try:
            # Pydantic v2 対応
            if hasattr(param_type, "__pydantic_core_schema__"):
                return True
            # Pydantic v1 対応
            if hasattr(param_type, "__config__") and hasattr(param_type, "__fields__"):
                return True
            # Model 継承チェック
            import inspect

            if inspect.isclass(param_type):
                for base in inspect.getmro(param_type):
                    if base.__name__ == "Model" and base.__module__.startswith("pydantic"):
                        return True
            return False
        except Exception:
            return False

    def _convert_basic_type(self, value: Any, target_type: Type) -> Any:
        """基本的な型変換を実行する"""
        if value is None:
            return value

        if target_type is str or target_type is type(None):
            return str(value)
        elif target_type == int:
            if isinstance(value, str):
                if not value.lstrip("-").isdigit():
                    raise ValueError(f"'{value}' を int に変換できません")
            return int(value)
        elif target_type == float:
            return float(value)
        elif target_type == bool:
            if isinstance(value, str):
                return value.lower() in ("true", "1", "yes", "on")
            return bool(value)
        else:
            return value

    def _validate_field_constraints(
        self, value: Any, field_info: FieldInfo, param_name: str, param_source: str
    ) -> None:
        """フィールド制約のバリデーションを実行する"""
        # 数値制約のチェック
        if isinstance(value, (int, float)):
            if field_info.gt is not None and not (value > field_info.gt):
                raise ValidationError(
                    f"{param_source} '{param_name}' は {field_info.gt} より大きい必要があります"
                )
            if field_info.ge is not None and not (value >= field_info.ge):
                raise ValidationError(
                    f"{param_source} '{param_name}' は {field_info.ge} 以上である必要があります"
                )
            if field_info.lt is not None and not (value < field_info.lt):
                raise ValidationError(
                    f"{param_source} '{param_name}' は {field_info.lt} より小さい必要があります"
                )
            if field_info.le is not None and not (value <= field_info.le):
                raise ValidationError(
                    f"{param_source} '{param_name}' は {field_info.le} 以下である必要があります"
                )

        # 文字列制約のチェック
        if isinstance(value, str):
            if field_info.min_length is not None and len(value) < field_info.min_length:
                raise ValidationError(
                    f"{param_source} '{param_name}' は最低 {field_info.min_length} 文字必要です"
                )
            if field_info.max_length is not None and len(value) > field_info.max_length:
                raise ValidationError(
                    f"{param_source} '{param_name}' は最大 {field_info.max_length} 文字までです"
                )
            if field_info.regex is not None and not re.match(field_info.regex, value):
                raise ValidationError(
                    f"{param_source} '{param_name}' は指定されたパターンにマッチしません"
                )


# グローバルリゾルバーインスタンス
_global_resolver = DependencyResolver()


def get_dependency_resolver() -> DependencyResolver:
    """グローバルな依存性リゾルバーを取得する"""
    return _global_resolver


def resolve_function_dependencies(
    func: Callable,
    request: Request,
    path_params: Optional[Dict[str, str]] = None,
    authenticated_user: Any = None,
) -> Dict[str, Any]:
    """
    関数の依存性注入パラメータを解決する便利関数

    Args:
        func: 対象の関数
        request: Request オブジェクト
        path_params: パスパラメータの辞書
        authenticated_user: 認証済みユーザーオブジェクト

    Returns:
        解決されたパラメータの辞書
    """
    resolver = get_dependency_resolver()
    return resolver.resolve_dependencies(func, request, path_params, authenticated_user)
