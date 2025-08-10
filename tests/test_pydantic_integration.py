"""
Pydantic 統合機能のテスト
"""

import json
import pytest
from typing import Optional
from dataclasses import dataclass

from lambapi import API, Response, create_lambda_handler


# テスト用データクラス
@dataclass
class DataclassUser:
    name: str
    email: str
    age: Optional[int] = None


try:
    from pydantic import BaseModel, field_validator
    PYDANTIC_AVAILABLE = True
    
    class PydanticUser(BaseModel):
        name: str
        email: str
        age: Optional[int] = None
        
        @field_validator('name')
        @classmethod
        def name_must_not_be_empty(cls, v):
            if not v.strip():
                raise ValueError('名前は空にできません')
            return v.strip()
        
        @field_validator('age')
        @classmethod
        def age_must_be_positive(cls, v):
            if v is not None and v < 0:
                raise ValueError('年齢は 0 以上である必要があります')
            return v
            
except ImportError:
    PYDANTIC_AVAILABLE = False
    BaseModel = None
    PydanticUser = None


def create_test_event(method: str, path: str, body: dict = None, query: dict = None):
    """テスト用イベントを作成"""
    return {
        "httpMethod": method,
        "path": path,
        "queryStringParameters": query,
        "headers": {"Content-Type": "application/json"} if body else {},
        "body": json.dumps(body) if body else None,
    }


def test_dataclass_fastapi_style():
    """データクラスを使った FastAPI 風の引数注入テスト"""
    def create_app(event, context):
        app = API(event, context)
        
        @app.post("/users")
        def create_user(user: DataclassUser):
            return {
                "id": f"user_{hash(user.email)}",
                "name": user.name,
                "email": user.email,
                "age": user.age
            }
        
        return app
    
    handler = create_lambda_handler(create_app)
    
    # 正常ケース
    event = create_test_event("POST", "/users", {
        "name": "Test User",
        "email": "test@example.com",
        "age": 25
    })
    
    result = handler(event, None)
    assert result["statusCode"] == 200
    
    body = json.loads(result["body"])
    assert body["name"] == "Test User"
    assert body["email"] == "test@example.com"
    assert body["age"] == 25


@pytest.mark.skipif(not PYDANTIC_AVAILABLE, reason="Pydantic not available")
def test_pydantic_fastapi_style():
    """Pydantic モデルを使った FastAPI 風の引数注入テスト"""
    def create_app(event, context):
        app = API(event, context)
        
        @app.post("/users")
        def create_user(user: PydanticUser):
            return {
                "id": f"user_{hash(user.email)}",
                "name": user.name,
                "email": user.email,
                "age": user.age
            }
        
        return app
    
    handler = create_lambda_handler(create_app)
    
    # 正常ケース
    event = create_test_event("POST", "/users", {
        "name": "Test User",
        "email": "test@example.com",
        "age": 25
    })
    
    result = handler(event, None)
    assert result["statusCode"] == 200
    
    body = json.loads(result["body"])
    assert body["name"] == "Test User"
    assert body["email"] == "test@example.com"
    assert body["age"] == 25


@pytest.mark.skipif(not PYDANTIC_AVAILABLE, reason="Pydantic not available")
def test_pydantic_validation_error():
    """Pydantic バリデーションエラーのテスト"""
    def create_app(event, context):
        app = API(event, context)
        
        @app.post("/users")
        def create_user(user: PydanticUser):
            return {"status": "created"}
        
        return app
    
    handler = create_lambda_handler(create_app)
    
    # バリデーションエラーケース（空の名前）
    event = create_test_event("POST", "/users", {
        "name": "  ",
        "email": "test@example.com",
        "age": -5
    })
    
    result = handler(event, None)
    assert result["statusCode"] == 500  # バリデーションエラーでサーバーエラーになる


def test_path_and_query_params():
    """パスパラメータとクエリパラメータの自動注入テスト"""
    def create_app(event, context):
        app = API(event, context)
        
        @app.get("/users/{user_id}")
        def get_user(user_id: str, include_profile: bool = False):
            return {
                "user_id": user_id,
                "include_profile": include_profile
            }
        
        return app
    
    handler = create_lambda_handler(create_app)
    
    # パスパラメータとクエリパラメータのテスト
    event = create_test_event("GET", "/users/123", query={"include_profile": "true"})
    
    result = handler(event, None)
    assert result["statusCode"] == 200
    
    body = json.loads(result["body"])
    assert body["user_id"] == "123"
    assert body["include_profile"] is True




def test_mixed_parameters():
    """複数種類のパラメータ混在テスト"""
    def create_app(event, context):
        app = API(event, context)
        
        @app.post("/users/{user_id}/update")
        def update_user(user_id: str, user: DataclassUser, version: int = 1):
            return {
                "user_id": user_id,
                "name": user.name,
                "email": user.email,
                "version": version
            }
        
        return app
    
    handler = create_lambda_handler(create_app)
    
    # パスパラメータ + リクエストボディ + クエリパラメータ
    event = {
        "httpMethod": "POST",
        "path": "/users/123/update",
        "queryStringParameters": {"version": "2"},
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"name": "Updated User", "email": "updated@example.com"})
    }
    
    result = handler(event, None)
    assert result["statusCode"] == 200
    
    body = json.loads(result["body"])
    assert body["user_id"] == "123"
    assert body["name"] == "Updated User"
    assert body["version"] == 2