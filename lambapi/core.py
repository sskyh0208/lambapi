"""
API メインクラス

モダンな Lambda 用 API フレームワークのコアクラスです。
"""

import re
import inspect
from typing import Dict, Any, Callable, Optional, List, Type, Union

from .request import Request
from .response import Response
from .cors import CORSConfig, create_cors_config
from .error_handlers import get_global_registry
from .base_router import BaseRouterMixin
from .dependency_resolver import resolve_function_dependencies
from .dependencies import get_function_dependencies
from .exceptions import ValidationError

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
        """ルートインデックスを再構築（add_router 時に使用）"""
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

    def add_router(self, router: Any, prefix: str = "", tags: Optional[List[str]] = None) -> None:
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

    def add_error_handler(self, error_handler: Any) -> None:
        """エラーハンドラーを追加"""
        from .error_handlers import ErrorHandler

        if isinstance(error_handler, ErrorHandler):
            # ErrorHandler のレジストリを現在のレジストリにマージ
            for exception_type, handler in error_handler._registry._handlers.items():
                self._error_registry.register(exception_type, handler)

            # デフォルトハンドラーも設定
            if error_handler._registry._default_handler:
                self._error_registry.set_default_handler(error_handler._registry._default_handler)

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
        """パスパラメータとクエリパラメータを自動注入してハンドラーを呼び出し"""
        handler = route.handler

        # signature キャッシュを使用
        if handler not in _SIGNATURE_CACHE:
            _SIGNATURE_CACHE[handler] = inspect.signature(handler)
        signature = _SIGNATURE_CACHE[handler]
        handler_params = signature.parameters

        # 最初の引数が request かどうかをチェック（従来の方式）
        param_names = list(handler_params.keys())
        if param_names and param_names[0] in ["request", "req"]:
            # 従来の方式（request を第一引数に渡す）
            return handler(request)

        # 新しい依存性注入システムを使用するかチェック
        dependencies = get_function_dependencies(handler)
        if dependencies:
            # 新しい依存性注入システムを使用
            # 認証が必要な場合は事前に認証処理を実行
            if getattr(handler, "_auth_required", False):
                # require_role デコレータのロジックを手動実行
                self._handle_authentication_for_dependency_injection(handler, request)

            return self._call_handler_with_dependencies(handler, request, path_params)
        else:
            # 従来のパラメータ注入システムを使用
            return self._call_handler_legacy_params(handler, request, path_params, signature)

    def _call_handler_with_dependencies(
        self, handler: Callable, request: Request, path_params: Optional[Dict[str, str]]
    ) -> Any:
        """新しい依存性注入システムでハンドラーを呼び出し"""
        try:
            # 認証ユーザーを取得（必要に応じて）
            authenticated_user = getattr(request, "_authenticated_user", None)

            # 依存性を解決
            resolved_params = resolve_function_dependencies(
                handler, request, path_params, authenticated_user
            )

            # 従来のパラメータも処理（互換性のため）
            legacy_params = self._get_legacy_params(handler, request, path_params)

            # 依存性注入パラメータを優先し、従来パラメータで補完
            final_params = {**legacy_params, **resolved_params}

            return handler(**final_params) if final_params else handler()

        except ValidationError:
            # バリデーションエラーはそのまま再発生させる（エラーハンドラーで処理される）
            raise
        except (AttributeError, TypeError, ImportError, KeyError):
            # 依存性注入固有のエラーのみ従来システムにフォールバック
            signature = inspect.signature(handler)
            return self._call_handler_legacy_params(handler, request, path_params, signature)
        except Exception:
            # 業務ロジックの例外は依存性注入が完了した後のエラーなのでそのまま再発生
            raise

    def _call_handler_legacy_params(
        self,
        handler: Callable,
        request: Request,
        path_params: Optional[Dict[str, str]],
        signature: inspect.Signature,
    ) -> Any:
        """従来のパラメータ注入システムでハンドラーを呼び出し"""
        handler_params = signature.parameters
        param_names = list(handler_params.keys())
        call_args: Dict[str, Any] = {}

        # パスパラメータをマッチング
        if path_params:
            for param_name in param_names:
                if param_name in path_params:
                    call_args[param_name] = path_params[param_name]

        # クエリパラメータをマッチング
        query_params = request.query_params
        for param_name, param_info in handler_params.items():
            if param_name in call_args or param_name == "request":
                continue

            # クエリパラメータから値を取得
            if param_name in query_params:
                value = query_params[param_name]
                # 型変換を実行
                call_args[param_name] = self._convert_param_type(value, param_info)
            elif param_info.default != inspect.Parameter.empty:
                # 依存性注入用パラメータ（Body, Query, Path, Authenticated）はスキップ
                if hasattr(param_info.default, "source"):
                    continue
                # 通常のデフォルト値を使用
                call_args[param_name] = param_info.default

        # request 引数がある場合は追加
        if "request" in handler_params:
            call_args["request"] = request

        # キーワード引数として渡す、もしくは引数なしで呼び出し
        return handler(**call_args) if call_args else handler()

    def _get_legacy_params(
        self, handler: Callable, request: Request, path_params: Optional[Dict[str, str]]
    ) -> Dict[str, Any]:
        """従来のパラメータ処理ロジックから基本パラメータを取得"""
        signature = inspect.signature(handler)
        handler_params = signature.parameters
        param_names = list(handler_params.keys())
        call_args: Dict[str, Any] = {}

        # パスパラメータをマッチング（依存性注入で処理されないもの）
        if path_params:
            for param_name in param_names:
                if param_name in path_params:
                    # 依存性注入対象でない場合のみ追加
                    param_info = handler_params.get(param_name)
                    if param_info and not hasattr(param_info.default, "source"):
                        call_args[param_name] = self._convert_param_type(
                            path_params[param_name], param_info
                        )

        # request 引数がある場合は追加
        if "request" in handler_params:
            call_args["request"] = request

        return call_args

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
        # レスポンスフォーマットバリデーション
        if isinstance(result, dict) and "statusCode" in result:
            return Response(result)  # エラーレスポンス

        # 結果を Response オブジェクトに変換
        if isinstance(result, Response):
            response = result
        elif isinstance(result, dict):
            response = Response(result)
        else:
            # Pydantic Model の場合は辞書に変換
            if hasattr(result, "model_dump") or hasattr(result, "dict"):
                # json_encoders を考慮した変換を行う
                from .validation import convert_to_dict

                response = Response(convert_to_dict(result))
            else:
                response = Response({"result": result})

        # ミドルウェアを適用
        response = self._apply_middleware(request, response)

        # CORS ヘッダーを追加
        response = self._apply_cors_headers(request, response, route)

        return response

    def _handle_authentication_for_dependency_injection(
        self, handler: Callable, request: Request
    ) -> None:
        """依存性注入システム用の認証処理"""
        try:
            # ハンドラーから認証情報を取得
            required_roles = getattr(handler, "_required_roles", [])

            # DynamoDBAuth インスタンスを見つける（フレームスタックから探索）
            import sys

            auth_instance = None
            frame = sys._getframe()

            while frame and auth_instance is None:
                frame_locals = frame.f_locals
                frame_globals = frame.f_globals

                # ローカル変数から auth を探索
                for var_name, var_value in frame_locals.items():
                    if hasattr(var_value, "get_authenticated_user") and hasattr(
                        var_value, "_required_roles"
                    ):
                        auth_instance = var_value
                        break

                # グローバル変数から auth を探索
                if auth_instance is None:
                    for var_name, var_value in frame_globals.items():
                        if hasattr(var_value, "get_authenticated_user") and hasattr(
                            var_value, "_required_roles"
                        ):
                            auth_instance = var_value
                            break

                frame = frame.f_back  # type: ignore

            if auth_instance is None:
                # ハンドラーのモジュールから auth をインポート
                handler_module = sys.modules.get(handler.__module__)
                if handler_module and hasattr(handler_module, "auth"):
                    auth_instance = handler_module.auth

            if auth_instance:
                # 認証ユーザーを取得
                user = auth_instance.get_authenticated_user(request)

                # ロール権限チェック
                if auth_instance.is_role_permission:
                    user_role = getattr(user, "role", None)
                    if user_role not in required_roles:
                        from .exceptions import AuthorizationError

                        raise AuthorizationError(f"必要なロール: {', '.join(required_roles)}")

                # 認証ユーザーを request に設定
                setattr(request, "_authenticated_user", user)
            else:
                # 認証インスタンスが見つからない場合はパス（エラーは後で発生する）
                pass

        except Exception:
            # 認証エラーをそのまま再発生させる
            raise

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
