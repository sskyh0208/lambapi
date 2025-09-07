"""
バリデーション機能

リクエスト/レスポンスバリデーション機能を提供します。
"""

from typing import Dict, Any, Type, Union, get_type_hints, get_origin, get_args, List
from dataclasses import fields, is_dataclass, MISSING

# バリデーション最適化用キャッシュ
_FIELD_INFO_CACHE: Dict[Type, Dict[str, Any]] = {}
_TYPE_HINTS_CACHE: Dict[Type, Dict[str, Type]] = {}


def validate_and_convert(data: Dict[str, Any], model_class: Type) -> Any:
    """辞書データを指定されたクラスに変換・バリデーション（最適化版）"""
    if not is_dataclass(model_class):
        raise ValueError(f"{model_class.__name__} はデータクラスである必要があります")

    # キャッシュからフィールド情報を取得
    if model_class not in _FIELD_INFO_CACHE:
        _FIELD_INFO_CACHE[model_class] = {f.name: f for f in fields(model_class)}
    field_info = _FIELD_INFO_CACHE[model_class]

    # キャッシュから型ヒントを取得
    if model_class not in _TYPE_HINTS_CACHE:
        _TYPE_HINTS_CACHE[model_class] = get_type_hints(model_class)
    type_hints = _TYPE_HINTS_CACHE[model_class]

    converted_data = {}

    for field_name, field_obj in field_info.items():
        field_type = type_hints.get(field_name, str)

        if field_name in data:
            value = data[field_name]
            converted_data[field_name] = _convert_value(value, field_type)
        elif field_obj.default is not MISSING:
            # デフォルト値を使用
            converted_data[field_name] = field_obj.default
        elif field_obj.default_factory is not MISSING:
            # デフォルトファクトリを使用
            converted_data[field_name] = field_obj.default_factory()
        else:
            # 必須フィールドが不足
            raise ValueError(f"必須フィールド '{field_name}' が不足しています")

    try:
        return model_class(**converted_data)
    except Exception as e:
        raise ValueError(f"バリデーションエラー: {str(e)}")


def _convert_value(value: Any, target_type: Type) -> Any:
    """値を指定された型に変換"""
    # None の場合はそのまま返す
    if value is None:
        return value

    # 基本型の変換
    if target_type == str:
        return str(value)
    elif target_type == int:
        if isinstance(value, str):
            try:
                return int(value)
            except ValueError:
                raise ValueError(f"'{value}' を int に変換できません")
        return int(value)
    elif target_type == float:
        if isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                raise ValueError(f"'{value}' を float に変換できません")
        return float(value)
    elif target_type == bool:
        if isinstance(value, str):
            return value.lower() in ("true", "1", "yes", "on")
        return bool(value)
    elif target_type == list:
        return list(value) if not isinstance(value, list) else value
    elif target_type == dict:
        return dict(value) if not isinstance(value, dict) else value

    # Optional 型の処理
    origin = get_origin(target_type)
    if origin is Union:
        args = get_args(target_type)
        # Optional[T] は Union[T, NoneType] として表現される
        if len(args) == 2 and type(None) in args:
            non_none_type = args[0] if args[1] is type(None) else args[1]
            return _convert_value(value, non_none_type)

    # リスト型の処理
    if origin is list:
        if not isinstance(value, list):
            raise ValueError(f"リスト型が期待されましたが {type(value)} を受け取りました")

        args = get_args(target_type)
        item_type = args[0] if args else Any
        # 型アノテーションからの変換を安全に実行
        from typing import cast

        return [_convert_value(item, cast(type, item_type)) for item in value]

    # データクラスの場合は再帰的に変換
    if is_dataclass(target_type):
        if isinstance(value, dict):
            return validate_and_convert(value, target_type)
        else:
            raise ValueError(
                f"データクラス {target_type.__name__} には辞書が必要ですが {type(value)} を受け取りました"
            )

    # その他の場合はそのまま返す
    return value


def convert_to_dict(obj: Any) -> Any:
    """データクラス・Pydanticオブジェクトを辞書に変換"""
    import datetime
    import uuid
    import decimal
    import enum

    # Pydantic Model の場合
    if hasattr(obj, "model_dump"):
        # Pydantic v2 対応
        result_dict = obj.model_dump()
        return convert_to_dict(result_dict)
    elif hasattr(obj, "dict"):
        # Pydantic v1 対応
        result_dict = obj.dict()
        return convert_to_dict(result_dict)
    elif is_dataclass(obj):
        result = {}
        for field in fields(obj):
            value = getattr(obj, field.name)
            if is_dataclass(value):
                result[field.name] = convert_to_dict(value)
            elif isinstance(value, list):
                converted_list: List[Any] = [
                    convert_to_dict(item) if is_dataclass(item) else item for item in value
                ]
                result[field.name] = converted_list
            elif isinstance(value, datetime.datetime):
                result[field.name] = value.isoformat()
            elif isinstance(value, datetime.date):
                result[field.name] = value.isoformat()
            elif isinstance(value, datetime.time):
                result[field.name] = value.isoformat()
            elif isinstance(value, uuid.UUID):
                result[field.name] = str(value)
            elif isinstance(value, decimal.Decimal):
                result[field.name] = str(value)
            elif isinstance(value, enum.Enum):
                result[field.name] = value.value
            else:
                result[field.name] = value
        return result
    elif isinstance(obj, dict):
        # 辞書の場合は各値を再帰的に変換
        result = {}
        for key, value in obj.items():
            result[key] = convert_to_dict(value)
        return result
    elif isinstance(obj, list):
        # リストの場合は各要素を再帰的に変換
        return [convert_to_dict(item) for item in obj]
    elif isinstance(obj, datetime.datetime):
        return obj.isoformat()
    elif isinstance(obj, datetime.date):
        return obj.isoformat()
    elif isinstance(obj, datetime.time):
        return obj.isoformat()
    elif isinstance(obj, uuid.UUID):
        return str(obj)
    elif isinstance(obj, decimal.Decimal):
        return str(obj)
    elif isinstance(obj, enum.Enum):
        return obj.value
    else:
        return obj
