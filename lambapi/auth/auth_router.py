"""
認証エンドポイント用ルーター

DynamoDB 認証システムの各エンドポイントを定義します。
"""

from typing import Dict, Any

from .dynamodb_auth import DynamoDBAuth
from ..router import Router
from ..request import Request


def create_auth_router(auth: DynamoDBAuth) -> Router:
    """認証エンドポイントのルーターを作成"""
    router = Router(prefix="/auth")

    @router.post("/signup")
    def signup_endpoint(request: Request) -> Dict[str, Any]:
        """ユーザー登録エンドポイント"""
        return auth.signup(request)

    @router.post("/login")
    def login_endpoint(request: Request) -> Dict[str, Any]:
        """ユーザーログインエンドポイント"""
        return auth.login(request)

    @router.post("/logout")
    def logout_endpoint(request: Request) -> Dict[str, Any]:
        """ユーザーログアウトエンドポイント"""
        return auth.logout(request)

    @router.delete("/user/{user_id}")
    def delete_user_endpoint(request: Request, user_id: str) -> Dict[str, Any]:
        """ユーザー削除エンドポイント"""
        return auth.delete_user(request, user_id)

    @router.put("/user/{user_id}/password")
    def update_password_endpoint(request: Request, user_id: str) -> Dict[str, Any]:
        """パスワード更新エンドポイント"""
        return auth.update_password(request, user_id)

    return router
