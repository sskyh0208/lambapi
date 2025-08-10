"""
04. 高度な機能 - CORS, ヘッダー, エラーハンドリング, Pydantic 連携

lambapi の高度な機能を組み合わせた実用的なサンプルです。
本番環境で使える構成例として参考にしてください。
"""

from dataclasses import dataclass
from typing import Optional, List, Union
from lambapi import API, Response, create_lambda_handler
from lambapi.annotations import Body, Path, Query, Header
from lambapi.exceptions import ValidationError, NotFoundError

# Pydantic を使用する場合（オプション）
try:
    from pydantic import BaseModel, field_validator, EmailStr

    PYDANTIC_AVAILABLE = True

    class PydanticUser(BaseModel):
        """Pydantic による高度なバリデーション"""

        name: str
        email: EmailStr  # メールアドレス検証
        age: int
        tags: List[str] = []

        @field_validator("age")
        @classmethod
        def validate_age(cls, v):
            if v < 0 or v > 150:
                raise ValueError("年齢は 0-150 の範囲で入力してください")
            return v

        @field_validator("name")
        @classmethod
        def validate_name(cls, v):
            if len(v.strip()) < 2:
                raise ValueError("名前は 2 文字以上で入力してください")
            return v.strip()

except ImportError:
    PYDANTIC_AVAILABLE = False
    PydanticUser = None


@dataclass
class ApiResponse:
    """API レスポンス用データクラス"""

    success: bool
    message: str
    data: Optional[dict] = None
    errors: Optional[List[str]] = None


@dataclass
class FileUpload:
    """ファイルアップロード情報"""

    filename: str
    content_type: str
    size: int
    content: str  # 実際は base64 等でエンコード


def create_app(event, context):
    app = API(event, context)

    # CORS の設定（本番環境では適切なオリジンを指定）
    app.enable_cors(
        origins=["https://example.com", "https://app.example.com"],
        methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        headers=["Content-Type", "Authorization", "X-API-Key", "X-Request-ID"],
        allow_credentials=True,
        max_age=3600,
    )

    # カスタムエラーハンドラー
    @app.error_handler(ValidationError)
    def handle_validation_error(error, request, context):
        """バリデーションエラーの統一処理"""
        return Response(
            {
                "success": False,
                "error": "VALIDATION_ERROR",
                "message": str(error),
                "request_id": request.headers.get("X-Request-ID", "unknown"),
            },
            status_code=400,
        )

    # === ヘッダーを使用する高度なエンドポイント ===

    @app.get("/api/info")
    def api_info(
        accept: str = Header(alias="Accept", default="application/json"),
        user_agent: Optional[str] = Header(alias="User-Agent"),
        request_id: Optional[str] = Header(alias="X-Request-ID"),
    ):
        """API 情報取得（Header アノテーション使用）"""
        return {
            "api_version": "2.0",
            "features": ["cors", "validation", "authentication", "caching"],
            "request_info": {
                "accept": accept,
                "user_agent": user_agent,
                "request_id": request_id,
                "pydantic_available": PYDANTIC_AVAILABLE,
            },
        }

    @app.post("/api/upload")
    def upload_file(
        file_info: FileUpload,
        content_type: str = Header(alias="Content-Type"),
        api_key: Optional[str] = Header(alias="X-API-Key"),
    ):
        """ファイルアップロード（複合パラメータ使用）"""
        # API キーの確認（簡易版）
        if not api_key or api_key != "demo-api-key":
            return Response(
                {"success": False, "error": "UNAUTHORIZED", "message": "有効な API キーが必要です"},
                status_code=401,
            )

        # ファイルサイズの確認
        if file_info.size > 1024 * 1024:  # 1MB 制限
            return Response(
                {
                    "success": False,
                    "error": "FILE_TOO_LARGE",
                    "message": "ファイルサイズは 1MB 以下にしてください",
                },
                status_code=413,
            )

        return Response(
            {
                "success": True,
                "message": "ファイルアップロード成功",
                "file": {
                    "filename": file_info.filename,
                    "size": file_info.size,
                    "content_type": file_info.content_type,
                    "uploaded_at": "2025-01-01T00:00:00Z",
                },
            },
            status_code=201,
        )

    # === Pydantic による高度なバリデーション ===

    if PYDANTIC_AVAILABLE:

        @app.post("/api/users/pydantic")
        def create_user_pydantic(user: PydanticUser):
            """Pydantic による高度なバリデーション"""
            return Response(
                {
                    "success": True,
                    "message": "ユーザー作成成功（Pydantic 検証済み）",
                    "user": user.model_dump(),
                },
                status_code=201,
            )

    # === 複雑な検索・フィルタリング ===

    @app.get("/api/search")
    def advanced_search(
        q: str = Query(description="検索クエリ"),
        category: Optional[str] = Query(default=None),
        sort_by: str = Query(default="created_at", alias="sort"),
        order: str = Query(default="desc"),
        limit: int = Query(default=20),
        offset: int = Query(default=0),
        include_metadata: bool = Query(default=False, alias="meta"),
    ):
        """高度な検索機能（複数クエリパラメータ）"""
        # 入力値の検証
        valid_sort_fields = ["created_at", "name", "popularity"]
        if sort_by not in valid_sort_fields:
            raise ValidationError(f"sort_by は {valid_sort_fields} のいずれかを指定してください")

        if order not in ["asc", "desc"]:
            raise ValidationError("order は 'asc' または 'desc' を指定してください")

        if limit < 1 or limit > 100:
            raise ValidationError("limit は 1-100 の範囲で指定してください")

        # 検索結果のシミュレーション
        results = [
            {
                "id": f"item_{i}",
                "name": f"{q} result {i}",
                "category": category or "general",
                "score": 0.9 - (i * 0.1),
            }
            for i in range(1, min(limit + 1, 6))  # 最大 5 件の模擬結果
        ]

        response = {
            "success": True,
            "results": results,
            "pagination": {
                "total": 100,  # 実際は DB 照会
                "limit": limit,
                "offset": offset,
                "has_more": offset + limit < 100,
            },
            "search_params": {"query": q, "category": category, "sort_by": sort_by, "order": order},
        }

        if include_metadata:
            response["metadata"] = {
                "search_time_ms": 45,
                "indexed_documents": 10000,
                "api_version": "2.0",
            }

        return response

    # === エラー処理のデモ ===

    @app.get("/api/demo/error/{error_type}")
    def error_demo(error_type: str, include_details: bool = Query(default=False)):
        """エラーハンドリングのデモ"""
        if error_type == "validation":
            raise ValidationError("バリデーションエラーのデモです")
        elif error_type == "not_found":
            raise NotFoundError("Resource", "demo-id")
        elif error_type == "server":
            raise Exception("サーバーエラーのデモです")
        else:
            return {
                "success": True,
                "message": "エラーなし",
                "available_error_types": ["validation", "not_found", "server"],
                "details": (
                    {"error_handling": "カスタムエラーハンドラーで統一処理", "cors_enabled": True}
                    if include_details
                    else None
                ),
            }

    return app


lambda_handler = create_lambda_handler(create_app)


if __name__ == "__main__":
    # 高度な機能のテスト
    print("=== 高度な機能テスト ===")

    import json

    def test_request(method, path, body=None, query=None, headers=None):
        event = {
            "httpMethod": method,
            "path": path,
            "queryStringParameters": query,
            "headers": headers or {"Content-Type": "application/json"},
            "body": json.dumps(body) if body else None,
        }
        result = lambda_handler(event, None)
        print(f"\n{method} {path}")
        print(f"Status: {result['statusCode']}")
        response_body = json.loads(result["body"])
        print(f"Response: {response_body}")

        # CORS ヘッダーの確認
        cors_headers = {
            k: v for k, v in result["headers"].items() if k.startswith("Access-Control")
        }
        if cors_headers:
            print(f"CORS Headers: {cors_headers}")

    # テストシーケンス
    test_request(
        "GET",
        "/api/info",
        headers={
            "Accept": "application/json",
            "User-Agent": "lambapi-test/1.0",
            "X-Request-ID": "test-123",
        },
    )

    test_request(
        "GET",
        "/api/search",
        query={
            "q": "lambapi",
            "category": "tech",
            "sort": "popularity",
            "limit": "5",
            "meta": "true",
        },
    )

    test_request(
        "POST",
        "/api/upload",
        body={
            "filename": "test.txt",
            "content_type": "text/plain",
            "size": 1024,
            "content": "demo content",
        },
        headers={"Content-Type": "application/json", "X-API-Key": "demo-api-key"},
    )

    if PYDANTIC_AVAILABLE:
        test_request(
            "POST",
            "/api/users/pydantic",
            body={
                "name": "Alice",
                "email": "alice@example.com",
                "age": 25,
                "tags": ["developer", "python"],
            },
        )

    test_request("GET", "/api/demo/error/validation")

    print(f"\nPydantic Available: {PYDANTIC_AVAILABLE}")
    print("本番環境では適切な CORS オリジン設定を行ってください")
