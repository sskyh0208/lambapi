"""
依存性注入システムのテスト
"""

import pytest
from dataclasses import dataclass
from typing import Optional

from lambapi import Query, Path, Body, Authenticated
from lambapi.dependencies import (
    FieldInfo,
    QueryInfo,
    PathInfo,
    BodyInfo,
    AuthenticatedInfo,
    get_function_dependencies,
    is_dependency_parameter,
)
from lambapi.dependency_resolver import DependencyResolver
from lambapi.request import Request
from lambapi.exceptions import ValidationError


@dataclass
class DataModel:
    name: str
    age: int


def create_request(query_params=None, path_params=None, json_body=None, headers=None):
    """テスト用のリクエストオブジェクトを作成"""
    event = {
        "httpMethod": "GET",
        "path": "/test",
        "queryStringParameters": query_params,
        "pathParameters": path_params,
        "body": json_body,
        "headers": headers or {},
    }
    return Request(event)


class TestDependencies:
    """依存性注入アノテーションのテスト"""

    def test_query_annotation(self):
        """Query アノテーション機能のテスト"""

        def test_handler(
            name: str = Query(..., description="Name parameter"),
            age: int = Query(25, ge=0, le=100),
            email: Optional[str] = Query(None),
        ):
            return {"name": name, "age": age, "email": email}

        dependencies = get_function_dependencies(test_handler)

        assert len(dependencies) == 3
        assert "name" in dependencies
        assert "age" in dependencies
        assert "email" in dependencies

        assert isinstance(dependencies["name"], QueryInfo)
        assert dependencies["name"].default == ...
        assert dependencies["name"].description == "Name parameter"

        assert isinstance(dependencies["age"], QueryInfo)
        assert dependencies["age"].default == 25
        assert dependencies["age"].ge == 0
        assert dependencies["age"].le == 100

    def test_path_annotation(self):
        """Path アノテーション機能のテスト"""

        def test_handler(
            user_id: str = Path(..., description="User ID"),
            item_id: int = Path(..., ge=1),
        ):
            return {"user_id": user_id, "item_id": item_id}

        dependencies = get_function_dependencies(test_handler)

        assert len(dependencies) == 2
        assert isinstance(dependencies["user_id"], PathInfo)
        assert isinstance(dependencies["item_id"], PathInfo)
        assert dependencies["item_id"].ge == 1

    def test_body_annotation(self):
        """Body アノテーション機能のテスト"""

        def test_handler(
            data: dict = Body(..., description="Request body"),
            model: DataModel = Body(...),
        ):
            return {"data": data, "model": model}

        dependencies = get_function_dependencies(test_handler)

        assert len(dependencies) == 2
        assert isinstance(dependencies["data"], BodyInfo)
        assert isinstance(dependencies["model"], BodyInfo)

    def test_authenticated_annotation(self):
        """Authenticated アノテーション機能のテスト"""

        def test_handler(
            user=Authenticated(..., description="Current user"),
        ):
            return {"user": user}

        dependencies = get_function_dependencies(test_handler)

        assert len(dependencies) == 1
        assert isinstance(dependencies["user"], AuthenticatedInfo)


class TestDependencyResolver:
    """依存性リゾルバーのテスト"""

    def setup_method(self):
        """テスト前の準備"""
        self.resolver = DependencyResolver()

    def test_resolve_query_parameters(self):
        """クエリパラメータの解決テスト"""

        def test_handler(
            name: str = Query(...),
            age: int = Query(25),
            active: bool = Query(True),
        ):
            pass

        request = create_request(query_params={"name": "test", "age": "30", "active": "false"})

        resolved = self.resolver.resolve_dependencies(test_handler, request)

        assert resolved["name"] == "test"
        assert resolved["age"] == 30
        assert resolved["active"] is False

    def test_resolve_path_parameters(self):
        """パスパラメータの解決テスト"""

        def test_handler(
            user_id: str = Path(...),
            item_id: int = Path(...),
        ):
            pass

        path_params = {"user_id": "user123", "item_id": "42"}
        request = create_request()

        resolved = self.resolver.resolve_dependencies(
            test_handler, request, path_params=path_params
        )

        assert resolved["user_id"] == "user123"
        assert resolved["item_id"] == 42

    def test_resolve_body_parameter(self):
        """リクエストボディの解決テスト"""

        def test_handler(
            data: dict = Body(...),
        ):
            pass

        import json

        body_data = {"name": "test", "value": 123}
        request = create_request(json_body=json.dumps(body_data))

        resolved = self.resolver.resolve_dependencies(test_handler, request)

        assert resolved["data"] == body_data

    def test_resolve_authenticated_parameter(self):
        """認証パラメータの解決テスト"""

        def test_handler(
            user=Authenticated(...),
        ):
            pass

        request = create_request()
        test_user = {"id": "user123", "name": "Test User"}

        resolved = self.resolver.resolve_dependencies(
            test_handler, request, authenticated_user=test_user
        )

        assert resolved["user"] == test_user

    def test_validation_constraints(self):
        """バリデーション制約のテスト"""

        def test_handler(
            age: int = Query(..., ge=0, le=100),
            name: str = Query(..., min_length=2, max_length=10),
        ):
            pass

        # 正常なケース
        request = create_request(query_params={"age": "25", "name": "test"})
        resolved = self.resolver.resolve_dependencies(test_handler, request)
        assert resolved["age"] == 25
        assert resolved["name"] == "test"

        # 制約違反のケース - 年齢が範囲外
        request = create_request(query_params={"age": "150", "name": "test"})
        with pytest.raises(ValidationError):
            self.resolver.resolve_dependencies(test_handler, request)

        # 制約違反のケース - 文字列が短すぎる
        request = create_request(query_params={"age": "25", "name": "a"})
        with pytest.raises(ValidationError):
            self.resolver.resolve_dependencies(test_handler, request)

    def test_missing_required_parameter(self):
        """必須パラメータが不足している場合のテスト"""

        def test_handler(
            name: str = Query(...),  # 必須
        ):
            pass

        request = create_request(query_params={})

        with pytest.raises(ValidationError) as exc_info:
            self.resolver.resolve_dependencies(test_handler, request)

        assert "必須のクエリパラメータ 'name' が不足しています" in str(exc_info.value)

    def test_default_values(self):
        """デフォルト値の処理テスト"""

        def test_handler(
            name: str = Query("default_name"),
            age: int = Query(25),
        ):
            pass

        request = create_request(query_params={})
        resolved = self.resolver.resolve_dependencies(test_handler, request)

        assert resolved["name"] == "default_name"
        assert resolved["age"] == 25

    def test_type_conversion(self):
        """型変換のテスト"""

        def test_handler(
            count: int = Query(...),
            rate: float = Query(...),
            enabled: bool = Query(...),
        ):
            pass

        request = create_request(query_params={"count": "42", "rate": "3.14", "enabled": "true"})

        resolved = self.resolver.resolve_dependencies(test_handler, request)

        assert resolved["count"] == 42
        assert resolved["rate"] == 3.14
        assert resolved["enabled"] is True

    def test_mixed_parameters(self):
        """複数タイプのパラメータ混在テスト"""

        def test_handler(
            user_id: str = Path(...),
            name: str = Query(...),
            data: dict = Body(...),
            user=Authenticated(...),
        ):
            pass

        import json

        body_data = {"key": "value"}
        request = create_request(query_params={"name": "test"}, json_body=json.dumps(body_data))
        path_params = {"user_id": "user123"}
        test_user = {"id": "user123"}

        resolved = self.resolver.resolve_dependencies(
            test_handler, request, path_params=path_params, authenticated_user=test_user
        )

        assert resolved["user_id"] == "user123"
        assert resolved["name"] == "test"
        assert resolved["data"] == body_data
        assert resolved["user"] == test_user
