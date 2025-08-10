"""
統一されたアノテーション方式のテスト
"""

import json
import pytest
from typing import Optional
from dataclasses import dataclass

from lambapi import (
    API, 
    create_lambda_handler,
    Body, 
    Path, 
    Query, 
    Header,
    CurrentUser,
    RequireRole, 
    OptionalAuth
)

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
            
except ImportError:
    PYDANTIC_AVAILABLE = False
    PydanticUser = None


@dataclass
class DataclassUser:
    name: str
    email: str
    age: Optional[int] = None


def create_test_event(method: str, path: str, body: dict = None, query: dict = None, headers: dict = None):
    """テスト用イベントを作成"""
    return {
        "httpMethod": method,
        "path": path,
        "queryStringParameters": query,
        "headers": headers or {},
        "body": json.dumps(body) if body else None,
    }


def test_body_annotation():
    """Body アノテーションのテスト"""
    def create_app(event, context):
        app = API(event, context)
        
        @app.post("/users")
        def create_user(user: DataclassUser = Body()):
            return {"name": user.name, "email": user.email}
        
        return app
    
    handler = create_lambda_handler(create_app)
    
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


def test_path_annotation():
    """Path アノテーションのテスト"""
    def create_app(event, context):
        app = API(event, context)
        
        @app.get("/users/{user_id}")
        def get_user(user_id: str = Path()):
            return {"user_id": user_id}
        
        return app
    
    handler = create_lambda_handler(create_app)
    
    event = create_test_event("GET", "/users/123")
    
    result = handler(event, None)
    assert result["statusCode"] == 200
    
    body = json.loads(result["body"])
    assert body["user_id"] == "123"


def test_query_annotation():
    """Query アノテーションのテスト"""
    def create_app(event, context):
        app = API(event, context)
        
        @app.get("/search")
        def search(
            q: str = Query(),
            page: int = Query(default=1),
            limit: int = Query(default=10),
            sort: Optional[str] = Query(default=None, alias="sort_by")
        ):
            return {
                "query": q,
                "page": page,
                "limit": limit,
                "sort": sort
            }
        
        return app
    
    handler = create_lambda_handler(create_app)
    
    # デフォルト値付きテスト
    event = create_test_event("GET", "/search", query={"q": "test", "sort_by": "date"})
    
    result = handler(event, None)
    assert result["statusCode"] == 200
    
    body = json.loads(result["body"])
    assert body["query"] == "test"
    assert body["page"] == 1  # デフォルト値
    assert body["limit"] == 10  # デフォルト値
    assert body["sort"] == "date"  # エイリアス


def test_header_annotation():
    """Header アノテーションのテスト"""
    def create_app(event, context):
        app = API(event, context)
        
        @app.get("/debug")
        def debug(
            user_agent: str = Header(alias="User-Agent"),
            accept: Optional[str] = Header(alias="Accept")
        ):
            return {
                "user_agent": user_agent,
                "accept": accept
            }
        
        return app
    
    handler = create_lambda_handler(create_app)
    
    event = create_test_event("GET", "/debug", headers={
        "User-Agent": "TestClient/1.0",
        "Accept": "application/json"
    })
    
    result = handler(event, None)
    assert result["statusCode"] == 200
    
    body = json.loads(result["body"])
    assert body["user_agent"] == "TestClient/1.0"
    assert body["accept"] == "application/json"


@pytest.mark.skipif(not PYDANTIC_AVAILABLE, reason="Pydantic not available")
def test_pydantic_auto_inference():
    """Pydantic モデルの自動推論テスト"""
    def create_app(event, context):
        app = API(event, context)
        
        @app.post("/users")
        def create_user(user: PydanticUser):  # アノテーションなし、自動推論
            return {"name": user.name, "email": user.email}
        
        return app
    
    handler = create_lambda_handler(create_app)
    
    event = create_test_event("POST", "/users", {
        "name": "Auto User",
        "email": "auto@example.com"
    })
    
    result = handler(event, None)
    assert result["statusCode"] == 200
    
    body = json.loads(result["body"])
    assert body["name"] == "Auto User"
    assert body["email"] == "auto@example.com"


def test_dataclass_auto_inference():
    """データクラスの自動推論テスト"""
    def create_app(event, context):
        app = API(event, context)
        
        @app.post("/users")
        def create_user(user: DataclassUser):  # アノテーションなし、自動推論
            return {"name": user.name, "email": user.email}
        
        return app
    
    handler = create_lambda_handler(create_app)
    
    event = create_test_event("POST", "/users", {
        "name": "Dataclass User",
        "email": "dataclass@example.com", 
        "age": 30
    })
    
    result = handler(event, None)
    assert result["statusCode"] == 200
    
    body = json.loads(result["body"])
    assert body["name"] == "Dataclass User"
    assert body["email"] == "dataclass@example.com"


def test_mixed_parameters():
    """複数種類のパラメータ混在テスト"""
    def create_app(event, context):
        app = API(event, context)
        
        @app.put("/users/{user_id}")
        def update_user(
            user_id: str = Path(),
            user_data: DataclassUser = Body(),
            version: int = Query(default=1),
            x_request_id: str = Header(alias="X-Request-ID")
        ):
            return {
                "user_id": user_id,
                "name": user_data.name,
                "version": version,
                "request_id": x_request_id
            }
        
        return app
    
    handler = create_lambda_handler(create_app)
    
    event = {
        "httpMethod": "PUT",
        "path": "/users/456",
        "queryStringParameters": {"version": "2"},
        "headers": {
            "Content-Type": "application/json",
            "X-Request-ID": "req-123"
        },
        "body": json.dumps({"name": "Updated User", "email": "updated@example.com"})
    }
    
    result = handler(event, None)
    assert result["statusCode"] == 200
    
    body = json.loads(result["body"])
    assert body["user_id"] == "456"
    assert body["name"] == "Updated User"
    assert body["version"] == 2
    assert body["request_id"] == "req-123"


def test_no_parameters():
    """引数なし関数のテスト"""
    def create_app(event, context):
        app = API(event, context)
        
        @app.get("/health")
        def health_check():
            return {"status": "ok"}
        
        return app
    
    handler = create_lambda_handler(create_app)
    
    event = create_test_event("GET", "/health")
    
    result = handler(event, None)
    assert result["statusCode"] == 200
    
    body = json.loads(result["body"])
    assert body["status"] == "ok"


def test_path_and_query_auto_inference():
    """パス・クエリパラメータの自動推論テスト"""
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
    
    event = create_test_event("GET", "/users/789", query={"include_profile": "true"})
    
    result = handler(event, None)
    assert result["statusCode"] == 200
    
    body = json.loads(result["body"])
    assert body["user_id"] == "789"
    assert body["include_profile"] is True


def test_validation_error():
    """バリデーションエラーのテスト"""
    def create_app(event, context):
        app = API(event, context)
        
        @app.post("/users")
        def create_user(user: DataclassUser = Body()):
            return {"name": user.name}
        
        return app
    
    handler = create_lambda_handler(create_app)
    
    # 必須フィールドが不足
    event = create_test_event("POST", "/users", {"name": "Test"})  # email が不足
    
    result = handler(event, None)
    assert result["statusCode"] == 500  # バリデーションエラー


def test_missing_required_parameter():
    """必須パラメータが不足した場合のテスト"""
    def create_app(event, context):
        app = API(event, context)
        
        @app.get("/search")
        def search(query: str = Query()):  # デフォルト値なしの必須パラメータ
            return {"query": query}
        
        return app
    
    handler = create_lambda_handler(create_app)
    
    event = create_test_event("GET", "/search")  # query パラメータなし
    
    result = handler(event, None)
    assert result["statusCode"] == 500  # パラメータエラー