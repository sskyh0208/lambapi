"""
API メインクラス

モダンな Lambda 用 API フレームワークのコアクラスです。
"""

import re
import inspect
from typing import Dict, Any, Callable, Optional, List, Type, Union

from .request import Request
from .response import Response
from .validation import validate_and_convert, is_pydantic_model
from .annotations import (
    is_parameter_annotation,
    is_auth_annotation,
    is_body_annotation,
    is_path_annotation,
    is_query_annotation,
    is_header_annotation,
    is_current_user_annotation,
    is_require_role_annotation,
    is_optional_auth_annotation,
)
from dataclasses import is_dataclass
from .cors import CORSConfig, create_cors_config
from .error_handlers import get_global_registry
from .base_router import BaseRouterMixin

# パフォーマンス最適化用キャッシュ
_SIGNATURE_CACHE: Dict[Callable, inspect.Signature] = {}
_TYPE_CONVERTER_CACHE: Dict[Type, Callable[[str], Any]] = {}


def _get_type_converter(annotation: Type) -> Callable[[str], Any]:
    """型変換関数をキャッシュ付きで取得"""
    if annotation in _TYPE_CONVERTER_CACHE:
        return _TYPE_CONVERTER_CACHE[annotation]

    if annotation == inspect.Parameter.empty or annotation == str:

        def str_converter(x: str) -> Any:
            return x

        converter = str_converter
    elif annotation == int:

        def int_converter(x: str) -> int:
            return int(x) if x.isdigit() or (x.startswith("-") and x[1:].isdigit()) else 0

        converter = int_converter
    elif annotation == float:

        def float_converter(x: str) -> float:
            return float(x) if _is_float(x) else 0.0

        converter = float_converter
    elif annotation == bool:

        def bool_converter(x: str) -> bool:
            return x.lower() in ("true", "1", "yes", "on")

        converter = bool_converter
    else:

        def default_converter(x: str) -> Any:
            return x

        converter = default_converter

    _TYPE_CONVERTER_CACHE[annotation] = converter
    return converter


def _is_float(value: str) -> bool:
    """文字列が float に変換可能かチェック"""
    try:
        float(value)
        return True
    except ValueError:
        return False


class Route:
    """ルート情報を保持するクラス"""

    def __init__(
        self,
        path: str,
        method: str,
        handler: Callable,
        cors_config: Optional[CORSConfig] = None,
    ):
        self.path = path
        self.method = method.upper()
        self.handler = handler
        self.cors_config = cors_config
        self.path_regex = self._compile_path_regex(path)

    def _compile_path_regex(self, path: str) -> re.Pattern:
        """パスパラメータを正規表現に変換"""
        # {param} を名前付きグループに変換
        pattern = re.sub(r"\{(\w+)\}", r"(?P<\1>[^/]+)", path)
        # 完全一致にする
        pattern = f"^{pattern}$"
        return re.compile(pattern)

    def match(self, path: str, method: str) -> Optional[Dict[str, str]]:
        """パスとメソッドがマッチするかチェック"""
        if self.method != method.upper():
            return None

        match = self.path_regex.match(path)
        if match:
            return match.groupdict()
        return None


class API(BaseRouterMixin):
    """モダンな Lambda 用 API フレームワーク"""

    def __init__(self, event: Dict[str, Any], context: Any, root_path: str = ""):
        self.event = event
        self.context = context
        self.root_path = self._validate_root_path(root_path)
        self.routes: List[Route] = []
        # 高速ルート検索のための最適化構造
        self._exact_routes: Dict[str, Dict[str, Route]] = {}  # method -> {path -> route}
        self._pattern_routes: Dict[str, List[Route]] = {}  # method -> [routes with params]
        self._middleware: List[Callable] = []
        self._cors_config: Optional[CORSConfig] = None
        self._error_registry = get_global_registry()
        self._auth_instance: Optional[Any] = None

    def _validate_root_path(self, root_path: str) -> str:
        """root_path をバリデーションして正規化"""
        if not root_path:
            return ""

        # 先頭にスラッシュがない場合は追加
        if not root_path.startswith("/"):
            root_path = f"/{root_path}"

        # 末尾スラッシュを除去
        root_path = root_path.rstrip("/")

        # 重複スラッシュを正規化
        root_path = re.sub(r"/+", "/", root_path)

        return root_path

    def _normalize_path(self, path: str) -> str:
        """root_path を考慮してパスを正規化"""
        if not self.root_path:
            return path

        # 完全一致または / で区切られた場合のみ除去
        if path == self.root_path:
            return "/"
        elif path.startswith(f"{self.root_path}/"):
            return path[len(self.root_path) :]
        else:
            return path

    def add_middleware(self, middleware: Callable) -> None:
        """ミドルウェアを追加"""
        self._middleware.append(middleware)

    def error_handler(self, exception_type: Type[Exception]) -> Callable:
        """エラーハンドラーデコレータ"""

        def decorator(handler_func: Callable) -> Callable:
            self._error_registry.register(exception_type, handler_func)
            return handler_func

        return decorator

    def default_error_handler(self, handler_func: Callable) -> Callable:
        """デフォルトエラーハンドラーデコレータ"""
        self._error_registry.set_default_handler(handler_func)
        return handler_func

    def _update_route_index(self, route: Route) -> None:
        """ルートを高速検索用インデックスに追加"""
        method = route.method

        # メソッド別辞書の初期化
        if method not in self._exact_routes:
            self._exact_routes[method] = {}
        if method not in self._pattern_routes:
            self._pattern_routes[method] = []

        # パスパラメータがない場合は完全一致テーブルに追加
        if "{" not in route.path:
            self._exact_routes[method][route.path] = route
        else:
            # パスパラメータがある場合はパターンマッチング用リストに追加
            self._pattern_routes[method].append(route)

    def _rebuild_route_index(self) -> None:
        """ルートインデックスを再構築（include_router 時に使用）"""
        self._exact_routes.clear()
        self._pattern_routes.clear()

        for route in self.routes:
            self._update_route_index(route)

    def enable_cors(
        self,
        origins: Union[str, List[str]] = "*",
        methods: Optional[List[str]] = None,
        headers: Optional[List[str]] = None,
        allow_credentials: bool = False,
        max_age: Optional[int] = None,
        expose_headers: Optional[List[str]] = None,
    ) -> None:
        """CORS を有効にする

        Args:
            origins: 許可するオリジン（'*' または具体的な URL）
            methods: 許可する HTTP メソッド
            headers: 許可するヘッダー
            allow_credentials: 認証情報の送信を許可するか
            max_age: プリフライトリクエストのキャッシュ時間（秒）
            expose_headers: ブラウザに公開するレスポンスヘッダー
        """
        self._cors_config = create_cors_config(
            origins=origins,
            methods=methods,
            headers=headers,
            allow_credentials=allow_credentials,
            max_age=max_age,
            expose_headers=expose_headers,
        )

    def include_router(
        self, router: Any, prefix: str = "", tags: Optional[List[str]] = None
    ) -> None:
        """ルーターを追加"""
        from .router import Router

        if isinstance(router, Router):
            # プレフィックスやタグが指定されている場合は新しいルーターを作成
            if prefix or tags:
                new_router = Router(prefix=prefix, tags=tags or [])
                for route in router.routes:
                    # 既存のルートを新しいプレフィックス付きでコピー
                    new_path = f"{prefix.rstrip('/')}{route.path}" if prefix else route.path
                    new_route = Route(
                        new_path,
                        route.method,
                        route.handler,
                    )
                    new_router.routes.append(new_route)
                self.routes.extend(new_router.routes)
            else:
                self.routes.extend(router.routes)

        # ルートインデックスを再構築
        self._rebuild_route_index()

    def include_auth(self, auth: Any) -> None:
        """認証機能を追加"""
        from .auth.dynamodb_auth import DynamoDBAuth
        from .auth.auth_router import create_auth_router

        if isinstance(auth, DynamoDBAuth):
            # 認証インスタンスを保存
            self._auth_instance = auth
            # 認証エンドポイントのルーターを作成して追加
            auth_router = create_auth_router(auth)
            self.include_router(auth_router)
        else:
            raise ValueError("auth は DynamoDBAuth のインスタンスである必要があります")

    def _add_route(
        self,
        path: str,
        method: str,
        handler: Callable,
        cors: Union[bool, CORSConfig, None] = None,
    ) -> Callable:
        """ルートを追加"""
        cors_config = None
        if cors is True:
            # デフォルトの CORS 設定を使用
            cors_config = create_cors_config()
        elif isinstance(cors, CORSConfig):
            cors_config = cors

        route = Route(path, method, handler, cors_config)
        self.routes.append(route)
        self._update_route_index(route)
        return handler

    def _find_route(
        self, path: str, method: str
    ) -> tuple[Optional[Route], Optional[Dict[str, str]]]:
        """マッチするルートを検索（最適化版）"""
        # root_path を考慮してパスを正規化
        normalized_path = self._normalize_path(path)

        # 1. 完全一致検索（O(1)）
        exact_routes = self._exact_routes.get(method, {})
        if normalized_path in exact_routes:
            return exact_routes[normalized_path], {}

        # 2. パターンマッチング検索（パラメータ付きルート）
        pattern_routes = self._pattern_routes.get(method, [])
        for route in pattern_routes:
            path_params = route.match(normalized_path, method)
            if path_params is not None:
                return route, path_params

        return None, None

    def _call_handler_with_params(
        self, route: Route, request: Request, path_params: Optional[Dict[str, str]]
    ) -> Any:
        """アノテーション方式でパラメータを自動注入してハンドラーを呼び出し"""
        handler = route.handler

        # signature キャッシュを使用
        if handler not in _SIGNATURE_CACHE:
            _SIGNATURE_CACHE[handler] = inspect.signature(handler)
        signature = _SIGNATURE_CACHE[handler]
        handler_params = signature.parameters

        call_args: Dict[str, Any] = {}

        # 各引数を解析してアノテーションに基づいて値を注入
        for param_name, param_info in handler_params.items():
            param_type = param_info.annotation
            default_value = param_info.default

            # アノテーションがある場合の処理
            if default_value != inspect.Parameter.empty and is_parameter_annotation(default_value):
                try:
                    call_args[param_name] = self._resolve_annotation_parameter(
                        param_name, param_type, default_value, request, path_params
                    )
                    continue
                except Exception as e:
                    # 認証エラーなど重要なエラーはそのまま伝播
                    raise e

            # アノテーションがない場合の自動推論（FastAPI 風）
            # Pydantic モデルまたはデータクラス -> Body
            if param_type != inspect.Parameter.empty and (
                is_pydantic_model(param_type) or is_dataclass(param_type)
            ):
                try:
                    request_data = request.json()
                    call_args[param_name] = validate_and_convert(request_data, param_type)
                    continue
                except Exception as e:
                    raise ValueError(f"リクエストボディのバリデーションエラー: {str(e)}")

            # パスパラメータから取得を試行
            if path_params and param_name in path_params:
                call_args[param_name] = self._convert_param_type(
                    path_params[param_name], param_info
                )
                continue

            # クエリパラメータから取得を試行
            query_params = request.query_params
            if param_name in query_params:
                value = query_params[param_name]
                call_args[param_name] = self._convert_param_type(value, param_info)
                continue

            # デフォルト値がある場合
            if default_value != inspect.Parameter.empty:
                call_args[param_name] = default_value
                continue

            # 必須引数で値が見つからない場合はエラー
            raise ValueError(f"必須パラメータ '{param_name}' の値が見つかりません")

        # キーワード引数として渡す
        return handler(**call_args) if call_args else handler()

    def _resolve_annotation_parameter(
        self,
        param_name: str,
        param_type: Type,
        annotation: Any,
        request: Request,
        path_params: Optional[Dict[str, str]],
    ) -> Any:
        """アノテーションに基づいてパラメータの値を解決"""

        # Body アノテーション
        if is_body_annotation(annotation):
            if param_type == inspect.Parameter.empty:
                raise ValueError(f"Body パラメータ '{param_name}' には型アノテーションが必要です")

            request_data = request.json()
            if is_pydantic_model(param_type) or is_dataclass(param_type):
                return validate_and_convert(request_data, param_type)
            else:
                return request_data

        # Path アノテーション
        elif is_path_annotation(annotation):
            if not path_params or param_name not in path_params:
                raise ValueError(f"パスパラメータ '{param_name}' が見つかりません")

            value = path_params[param_name]
            if param_type != inspect.Parameter.empty:
                converter = _get_type_converter(param_type)
                return converter(value)
            return value

        # Query アノテーション
        elif is_query_annotation(annotation):
            query_params = request.query_params
            param_key = annotation.alias or param_name

            if param_key in query_params:
                value = query_params[param_key]
                if param_type != inspect.Parameter.empty:
                    converter = _get_type_converter(param_type)
                    return converter(value)
                return value
            elif annotation.default is not None:
                return annotation.default
            else:
                raise ValueError(f"クエリパラメータ '{param_key}' が見つかりません")

        # Header アノテーション
        elif is_header_annotation(annotation):
            headers = request.headers
            header_key = annotation.alias or param_name

            if header_key in headers:
                return headers[header_key]
            else:
                raise ValueError(f"ヘッダー '{header_key}' が見つかりません")

        # 認証系アノテーション
        elif is_auth_annotation(annotation):
            return self._resolve_auth_annotation(param_name, param_type, annotation, request)

        else:
            raise ValueError(f"未知のアノテーション: {type(annotation)}")

    def _resolve_auth_annotation(
        self, param_name: str, param_type: Type, annotation: Any, request: Request
    ) -> Any:
        """認証系アノテーションを解決"""
        # DynamoDBAuth インスタンスを取得
        auth = self._get_auth_instance()
        if not auth:
            raise ValueError("認証機能が設定されていません")

        try:
            # CurrentUser アノテーション
            if is_current_user_annotation(annotation):
                return auth.get_authenticated_user(request)

            # RequireRole アノテーション
            elif is_require_role_annotation(annotation):
                user = auth.get_authenticated_user(request)

                # ロール権限チェック
                if auth.user_model._is_role_permission_enabled():
                    user_role = getattr(user, "role", None)
                    required_roles = annotation.roles
                    if user_role not in required_roles:
                        from .exceptions import AuthorizationError

                        raise AuthorizationError(f"必要なロール: {', '.join(required_roles)}")

                return user

            # OptionalAuth アノテーション
            elif is_optional_auth_annotation(annotation):
                try:
                    return auth.get_authenticated_user(request)
                except Exception:
                    # 認証に失敗した場合は None を返す
                    return None

            else:
                raise ValueError(f"未知の認証アノテーション: {type(annotation)}")

        except Exception as e:
            # OptionalAuth 以外では認証エラーをそのまま伝播
            if not is_optional_auth_annotation(annotation):
                raise e
            return None

    def _get_auth_instance(self):
        """DynamoDBAuth インスタンスを取得（設定されている場合）"""
        return self._auth_instance

    def _convert_param_type(self, value: str, param_info: inspect.Parameter) -> Any:
        """パラメータの型アノテーションに基づいて値を変換（最適化版）"""
        converter = _get_type_converter(param_info.annotation)
        return converter(value)

    def _handle_cors_preflight(self, request: Request) -> Optional[Dict[str, Any]]:
        """CORS プリフライトリクエストを処理"""
        if request.method == "OPTIONS" and self._cors_config:
            origin = request.headers.get("origin") or request.headers.get("Origin")
            cors_headers = self._cors_config.get_cors_headers(origin)
            response = Response("", status_code=200, headers=cors_headers)
            return response.to_lambda_response()
        return None

    def _handle_route_not_found(self, request: Request) -> Dict[str, Any]:
        """ルートが見つからない場合の処理"""
        response = Response({"error": "Not Found"}, status_code=404)
        response = self._apply_cors_headers(request, response, None)
        return response.to_lambda_response()

    def _process_path_params(
        self, request: Request, path_params: Optional[Dict[str, str]]
    ) -> Request:
        """パスパラメータを処理"""
        if path_params:
            if "pathParameters" not in self.event:
                self.event["pathParameters"] = {}
            self.event["pathParameters"].update(path_params)
            request = Request(self.event)  # 更新された event で Request を再作成
        return request

    def _execute_handler(
        self, route: Route, request: Request, path_params: Optional[Dict[str, str]]
    ) -> Any:
        """ハンドラーを実行"""
        try:
            return self._call_handler_with_params(route, request, path_params)
        except Exception as e:
            # カスタムエラーハンドリング
            error_response = self._error_registry.handle_error(e, request, self.context)
            error_response = self._apply_cors_headers(request, error_response, route)
            return error_response.to_lambda_response()

    def _process_response(self, result: Any, route: Route, request: Request) -> Response:
        """レスポンスを処理"""
        # 結果を Response オブジェクトに変換
        if isinstance(result, Response):
            response = result
        elif isinstance(result, dict):
            response = Response(result)
        else:
            # Pydantic BaseModel の場合は辞書に変換
            if hasattr(result, "model_dump"):
                response = Response(result.model_dump())
            elif hasattr(result, "dict"):
                response = Response(result.dict())
            else:
                response = Response({"result": result})

        # ミドルウェアを適用
        response = self._apply_middleware(request, response)

        # CORS ヘッダーを追加
        response = self._apply_cors_headers(request, response, route)

        return response

    def _handle_global_error(self, error: Exception) -> Dict[str, Any]:
        """グローバルエラーハンドリング"""
        try:
            # request の作成を試みる
            try:
                request = Request(self.event)
                error_response = self._error_registry.handle_error(error, request, self.context)
                error_response = self._apply_cors_headers(request, error_response)
            except Exception:
                # request が作成できない場合のフォールバック
                from .exceptions import InternalServerError

                internal_error = InternalServerError("Request processing failed")
                error_response = self._error_registry._handle_unknown_error(
                    internal_error, None, self.context
                )
        except Exception:
            # エラーハンドリング自体でエラーが発生した場合のフォールバック
            error_response = Response(
                {"error": "INTERNAL_ERROR", "message": "An unexpected error occurred"},
                status_code=500,
            )

        return error_response.to_lambda_response()

    def _apply_cors_headers(
        self, request: Request, response: Response, route: Optional[Route] = None
    ) -> Response:
        """CORS ヘッダーをレスポンスに追加"""
        if isinstance(response, Response):
            # 個別ルートの CORS 設定を優先
            cors_config = None
            if route and route.cors_config:
                cors_config = route.cors_config
            elif self._cors_config:
                cors_config = self._cors_config

            if cors_config:
                origin = request.headers.get("origin") or request.headers.get("Origin")
                cors_headers = cors_config.get_cors_headers(origin)
                response.headers.update(cors_headers)
        return response

    def _apply_middleware(self, request: Request, response: Any) -> Any:
        """ミドルウェアを適用"""
        for middleware in self._middleware:
            response = middleware(request, response)
        return response

    def handle_request(self) -> Dict[str, Any]:
        """メインのリクエスト処理"""
        try:
            request = Request(self.event)

            # OPTIONS リクエストの自動処理（CORS プリフライト）
            cors_response = self._handle_cors_preflight(request)
            if cors_response:
                return cors_response

            # ルート検索
            route, path_params = self._find_route(request.path, request.method)
            if not route:
                return self._handle_route_not_found(request)

            # パスパラメータを処理
            request = self._process_path_params(request, path_params)

            # ハンドラー実行
            result = self._execute_handler(route, request, path_params)
            if isinstance(result, dict) and "statusCode" in result:
                return result  # エラーレスポンスの場合

            # レスポンス処理
            response = self._process_response(result, route, request)

            return response.to_lambda_response()

        except Exception as e:
            return self._handle_global_error(e)
