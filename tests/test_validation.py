"""
バリデーション機能のテスト

lambapi.validation モジュールの各機能をテストします。
"""

import pytest
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Union
from lambapi.validation import validate_and_convert, convert_to_dict, _convert_value


# テスト用データクラス定義
@dataclass
class SimpleUser:
    name: str
    age: int
    active: bool = True


@dataclass
class UserWithOptional:
    name: str
    age: Optional[int] = None
    email: Optional[str] = None
    active: bool = True


@dataclass
class UserWithList:
    name: str
    tags: List[str]
    scores: List[int] = field(default_factory=list)


@dataclass
class Address:
    street: str
    city: str
    zipcode: str


@dataclass
class UserWithNestedData:
    name: str
    address: Address
    age: int = 25


@dataclass
class UserWithListOfObjects:
    name: str
    addresses: List[Address]


class TestValidateAndConvert:
    """validate_and_convert 関数のテスト"""

    def test_simple_dataclass_conversion(self):
        """基本的なデータクラス変換のテスト"""
        data = {"name": "Alice", "age": 30, "active": True}
        result = validate_and_convert(data, SimpleUser)

        assert isinstance(result, SimpleUser)
        assert result.name == "Alice"
        assert result.age == 30
        assert result.active is True

    def test_type_conversion(self):
        """型変換のテスト"""
        data = {"name": "Bob", "age": "25", "active": "true"}
        result = validate_and_convert(data, SimpleUser)

        assert isinstance(result, SimpleUser)
        assert result.name == "Bob"
        assert result.age == 25
        assert result.active is True

    def test_default_values(self):
        """デフォルト値のテスト"""
        data = {"name": "Charlie", "age": 35}
        result = validate_and_convert(data, SimpleUser)

        assert result.name == "Charlie"
        assert result.age == 35
        assert result.active is True  # デフォルト値

    def test_optional_fields(self):
        """オプショナルフィールドのテスト"""
        data = {"name": "Diana"}
        result = validate_and_convert(data, UserWithOptional)

        assert result.name == "Diana"
        assert result.age is None
        assert result.email is None
        assert result.active is True

    def test_optional_fields_with_values(self):
        """値ありオプショナルフィールドのテスト"""
        data = {"name": "Eve", "age": "28", "email": "eve@example.com"}
        result = validate_and_convert(data, UserWithOptional)

        assert result.name == "Eve"
        assert result.age == 28
        assert result.email == "eve@example.com"
        assert result.active is True

    def test_list_fields(self):
        """リストフィールドのテスト"""
        data = {"name": "Frank", "tags": ["admin", "user"], "scores": ["100", "95", "88"]}
        result = validate_and_convert(data, UserWithList)

        assert result.name == "Frank"
        assert result.tags == ["admin", "user"]
        assert result.scores == [100, 95, 88]

    def test_list_field_with_default_factory(self):
        """デフォルトファクトリを使用するリストフィールドのテスト"""
        data = {"name": "Grace", "tags": ["guest"]}
        result = validate_and_convert(data, UserWithList)

        assert result.name == "Grace"
        assert result.tags == ["guest"]
        assert result.scores == []  # デフォルトファクトリ

    def test_nested_dataclass(self):
        """ネストしたデータクラスのテスト"""
        data = {
            "name": "Henry",
            "address": {"street": "123 Main St", "city": "Tokyo", "zipcode": "100-0001"},
        }
        result = validate_and_convert(data, UserWithNestedData)

        assert result.name == "Henry"
        assert isinstance(result.address, Address)
        assert result.address.street == "123 Main St"
        assert result.address.city == "Tokyo"
        assert result.address.zipcode == "100-0001"
        assert result.age == 25  # デフォルト値

    def test_list_of_nested_dataclass(self):
        """ネストしたデータクラスのリストのテスト"""
        data = {
            "name": "Iris",
            "addresses": [
                {"street": "123 Main St", "city": "Tokyo", "zipcode": "100-0001"},
                {"street": "456 Side St", "city": "Osaka", "zipcode": "530-0001"},
            ],
        }
        result = validate_and_convert(data, UserWithListOfObjects)

        assert result.name == "Iris"
        assert len(result.addresses) == 2
        assert all(isinstance(addr, Address) for addr in result.addresses)
        assert result.addresses[0].street == "123 Main St"
        assert result.addresses[1].city == "Osaka"

    def test_missing_required_field(self):
        """必須フィールド不足のテスト"""
        data = {"age": 30}  # name が不足

        with pytest.raises(ValueError, match="必須フィールド 'name' が不足しています"):
            validate_and_convert(data, SimpleUser)

    def test_invalid_dataclass(self):
        """非データクラスでのエラーテスト"""

        class NotADataclass:
            pass

        with pytest.raises(ValueError, match="NotADataclass はデータクラスである必要があります"):
            validate_and_convert({}, NotADataclass)

    def test_validation_error_in_constructor(self):
        """コンストラクタでのバリデーションエラーテスト"""

        @dataclass
        class StrictUser:
            name: str
            age: int

            def __post_init__(self):
                if self.age < 0:
                    raise ValueError("Age must be positive")

        data = {"name": "Test", "age": -1}

        with pytest.raises(ValueError, match="バリデーションエラー"):
            validate_and_convert(data, StrictUser)


class TestConvertValue:
    """_convert_value 関数のテスト"""

    def test_none_value(self):
        """None 値のテスト"""
        assert _convert_value(None, str) is None
        assert _convert_value(None, int) is None

    def test_string_conversion(self):
        """文字列変換のテスト"""
        assert _convert_value(123, str) == "123"
        assert _convert_value(True, str) == "True"
        assert _convert_value("test", str) == "test"

    def test_int_conversion(self):
        """整数変換のテスト"""
        assert _convert_value("123", int) == 123
        assert _convert_value(123.5, int) == 123
        assert _convert_value(True, int) == 1

    def test_int_conversion_error(self):
        """整数変換エラーのテスト"""
        with pytest.raises(ValueError, match="'abc' を int に変換できません"):
            _convert_value("abc", int)

    def test_float_conversion(self):
        """浮動小数点変換のテスト"""
        assert _convert_value("123.5", float) == 123.5
        assert _convert_value(123, float) == 123.0
        assert _convert_value("0.5", float) == 0.5

    def test_float_conversion_error(self):
        """浮動小数点変換エラーのテスト"""
        with pytest.raises(ValueError, match="'xyz' を float に変換できません"):
            _convert_value("xyz", float)

    def test_bool_conversion(self):
        """ブール変換のテスト"""
        # True の場合
        assert _convert_value("true", bool) is True
        assert _convert_value("TRUE", bool) is True
        assert _convert_value("1", bool) is True
        assert _convert_value("yes", bool) is True
        assert _convert_value("on", bool) is True
        assert _convert_value(1, bool) is True

        # False の場合
        assert _convert_value("false", bool) is False
        assert _convert_value("0", bool) is False
        assert _convert_value("", bool) is False
        assert _convert_value(0, bool) is False

    def test_list_conversion(self):
        """リスト変換のテスト"""
        assert _convert_value((1, 2, 3), list) == [1, 2, 3]
        assert _convert_value([1, 2, 3], list) == [1, 2, 3]
        assert _convert_value("abc", list) == ["a", "b", "c"]

    def test_dict_conversion(self):
        """辞書変換のテスト"""
        original_dict = {"a": 1, "b": 2}
        assert _convert_value(original_dict, dict) == original_dict

        # タプルのリストは辞書に変換される
        result = _convert_value([("a", 1), ("b", 2)], dict)
        expected = {"a": 1, "b": 2}
        assert result == expected

    def test_optional_type_conversion(self):
        """Optional 型変換のテスト"""
        from typing import Optional

        # Optional[int] の変換
        assert _convert_value("123", Optional[int]) == 123
        assert _convert_value(None, Optional[int]) is None

        # Optional[str] の変換
        assert _convert_value(123, Optional[str]) == "123"

    def test_list_type_conversion(self):
        """List 型変換のテスト"""
        from typing import List

        # List[int] の変換
        result = _convert_value(["1", "2", "3"], List[int])
        assert result == [1, 2, 3]

        # List[str] の変換
        result = _convert_value([1, 2, 3], List[str])
        assert result == ["1", "2", "3"]

    def test_list_type_conversion_error(self):
        """List 型変換エラーのテスト"""
        from typing import List

        with pytest.raises(ValueError, match="リスト型が期待されましたが"):
            _convert_value("not_a_list", List[int])

    def test_dataclass_conversion(self):
        """データクラス変換のテスト"""
        address_data = {"street": "123 Main St", "city": "Tokyo", "zipcode": "100-0001"}
        result = _convert_value(address_data, Address)

        assert isinstance(result, Address)
        assert result.street == "123 Main St"
        assert result.city == "Tokyo"

    def test_dataclass_conversion_error(self):
        """データクラス変換エラーのテスト"""
        with pytest.raises(ValueError, match="データクラス Address には辞書が必要ですが"):
            _convert_value("not_a_dict", Address)

    def test_unknown_type_passthrough(self):
        """未知の型のパススルーテスト"""
        custom_object = object()
        assert _convert_value(custom_object, object) is custom_object


class TestConvertToDict:
    """convert_to_dict 関数のテスト"""

    def test_simple_dataclass_to_dict(self):
        """単純なデータクラスの辞書変換テスト"""
        user = SimpleUser(name="Alice", age=30, active=True)
        result = convert_to_dict(user)

        expected = {"name": "Alice", "age": 30, "active": True}
        assert result == expected

    def test_nested_dataclass_to_dict(self):
        """ネストしたデータクラスの辞書変換テスト"""
        address = Address(street="123 Main St", city="Tokyo", zipcode="100-0001")
        user = UserWithNestedData(name="Bob", address=address, age=35)
        result = convert_to_dict(user)

        expected = {
            "name": "Bob",
            "address": {"street": "123 Main St", "city": "Tokyo", "zipcode": "100-0001"},
            "age": 35,
        }
        assert result == expected

    def test_list_of_dataclass_to_dict(self):
        """データクラスのリストの辞書変換テスト"""
        addresses = [
            Address(street="123 Main St", city="Tokyo", zipcode="100-0001"),
            Address(street="456 Side St", city="Osaka", zipcode="530-0001"),
        ]
        user = UserWithListOfObjects(name="Charlie", addresses=addresses)
        result = convert_to_dict(user)

        expected = {
            "name": "Charlie",
            "addresses": [
                {"street": "123 Main St", "city": "Tokyo", "zipcode": "100-0001"},
                {"street": "456 Side St", "city": "Osaka", "zipcode": "530-0001"},
            ],
        }
        assert result == expected

    def test_list_with_mixed_types(self):
        """混在型リストの辞書変換テスト"""

        @dataclass
        class UserWithMixedList:
            name: str
            items: List[Any]

        address = Address(street="123 Main St", city="Tokyo", zipcode="100-0001")
        user = UserWithMixedList(name="Diana", items=[address, "string", 42])
        result = convert_to_dict(user)

        expected = {
            "name": "Diana",
            "items": [
                {"street": "123 Main St", "city": "Tokyo", "zipcode": "100-0001"},
                "string",
                42,
            ],
        }
        assert result == expected

    def test_non_dataclass_passthrough(self):
        """非データクラスのパススルーテスト"""
        regular_dict = {"name": "Eve", "age": 25}
        assert convert_to_dict(regular_dict) == regular_dict

        regular_string = "Hello, World!"
        assert convert_to_dict(regular_string) == regular_string

        regular_list = [1, 2, 3]
        assert convert_to_dict(regular_list) == regular_list


class TestCacheOptimization:
    """キャッシュ最適化のテスト"""

    def test_field_info_cache(self):
        """フィールド情報キャッシュのテスト"""
        from lambapi.validation import _FIELD_INFO_CACHE

        # キャッシュをクリア
        _FIELD_INFO_CACHE.clear()

        # 最初の呼び出し
        data1 = {"name": "Test1", "age": 25}
        validate_and_convert(data1, SimpleUser)
        assert SimpleUser in _FIELD_INFO_CACHE

        # 2 回目の呼び出し（キャッシュが使用される）
        data2 = {"name": "Test2", "age": 30}
        result = validate_and_convert(data2, SimpleUser)
        assert result.name == "Test2"
        assert result.age == 30

    def test_type_hints_cache(self):
        """型ヒントキャッシュのテスト"""
        from lambapi.validation import _TYPE_HINTS_CACHE

        # キャッシュをクリア
        _TYPE_HINTS_CACHE.clear()

        # 最初の呼び出し
        data1 = {"name": "Test1", "age": 25}
        validate_and_convert(data1, SimpleUser)
        assert SimpleUser in _TYPE_HINTS_CACHE

        # 2 回目の呼び出し（キャッシュが使用される）
        data2 = {"name": "Test2", "age": 30}
        result = validate_and_convert(data2, SimpleUser)
        assert result.name == "Test2"
        assert result.age == 30


class TestEdgeCases:
    """エッジケースのテスト"""

    def test_empty_data(self):
        """空データのテスト"""

        @dataclass
        class EmptyClass:
            pass

        result = validate_and_convert({}, EmptyClass)
        assert isinstance(result, EmptyClass)

    def test_complex_nested_structure(self):
        """複雑なネスト構造のテスト"""

        @dataclass
        class Department:
            name: str
            users: List[UserWithNestedData]

        data = {
            "name": "Engineering",
            "users": [
                {
                    "name": "Alice",
                    "address": {"street": "123 Main St", "city": "Tokyo", "zipcode": "100-0001"},
                    "age": 30,
                },
                {
                    "name": "Bob",
                    "address": {"street": "456 Side St", "city": "Osaka", "zipcode": "530-0001"},
                    # age はデフォルト値を使用
                },
            ],
        }

        result = validate_and_convert(data, Department)
        assert result.name == "Engineering"
        assert len(result.users) == 2
        assert result.users[0].name == "Alice"
        assert result.users[0].age == 30
        assert result.users[1].name == "Bob"
        assert result.users[1].age == 25  # デフォルト値

    def test_union_type_handling(self):
        """Union 型の処理テスト"""

        @dataclass
        class FlexibleUser:
            name: str
            value: Union[str, int]

        # 文字列の場合
        data1 = {"name": "Test1", "value": "string_value"}
        result1 = validate_and_convert(data1, FlexibleUser)
        assert result1.value == "string_value"

        # 整数の場合
        data2 = {"name": "Test2", "value": 42}
        result2 = validate_and_convert(data2, FlexibleUser)
        assert result2.value == 42
