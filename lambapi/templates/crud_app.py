"""
CRUD API を含む lambapi アプリケーション
"""

from typing import Dict, Any
from lambapi import API, Response, create_lambda_handler
from lambapi.exceptions import ValidationError, NotFoundError
import uuid
from datetime import datetime


def create_app(event: Dict[str, Any], context: Any) -> API:
    app = API(event, context)

    # インメモリデータストア（本番では DB を使用）
    items_db: Dict[str, Dict[str, Any]] = {}

    @app.get("/")
    def root() -> Dict[str, Any]:
        return {
            "name": "CRUD API",
            "version": "1.0.0",
            "endpoints": [
                "GET /",
                "GET /items",
                "POST /items",
                "GET /items/{item_id}",
                "PUT /items/{item_id}",
                "DELETE /items/{item_id}",
            ],
        }

    @app.get("/items")
    def list_items(limit: int = 10, search: str = "") -> Dict[str, Any]:
        """アイテム一覧取得"""
        items = list(items_db.values())

        # 検索フィルタ
        if search:
            items = [item for item in items if search.lower() in item["name"].lower()]

        # リミット適用
        items = items[:limit]

        return {"items": items, "total": len(items), "limit": limit}

    @app.post("/items")
    def create_item(request: Any) -> Response:
        """新しいアイテム作成"""
        data = request.json()

        # バリデーション
        if not data.get("name"):
            raise ValidationError("Name is required", field="name")

        # アイテム作成
        item_id = str(uuid.uuid4())
        item = {
            "id": item_id,
            "name": data["name"],
            "description": data.get("description", ""),
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }

        items_db[item_id] = item

        return Response({"message": "Item created successfully", "item": item}, status_code=201)

    @app.get("/items/{item_id}")
    def get_item(item_id: str) -> Dict[str, Any]:
        """特定のアイテム取得"""
        if item_id not in items_db:
            raise NotFoundError("Item", item_id)

        return {"item": items_db[item_id]}

    @app.put("/items/{item_id}")
    def update_item(item_id: str, request: Any) -> Dict[str, Any]:
        """アイテム更新"""
        if item_id not in items_db:
            raise NotFoundError("Item", item_id)

        data = request.json()
        item = items_db[item_id]

        # 更新可能なフィールド
        if "name" in data:
            item["name"] = data["name"]
        if "description" in data:
            item["description"] = data["description"]

        item["updated_at"] = datetime.now().isoformat()

        return {"message": "Item updated successfully", "item": item}

    @app.delete("/items/{item_id}")
    def delete_item(item_id: str) -> Dict[str, str]:
        """アイテム削除"""
        if item_id not in items_db:
            raise NotFoundError("Item", item_id)

        deleted_item = items_db.pop(item_id)

        return {
            "message": f"Item '{deleted_item['name']}' deleted successfully",
            "deleted_item_id": item_id,
        }

    return app


# Lambda エントリーポイント
lambda_handler = create_lambda_handler(create_app)
