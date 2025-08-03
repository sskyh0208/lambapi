"""
API メインクラス

モダンな Lambda 用 API フレームワークのコアクラスです。
"""

import re
import inspect
from typing import Dict, Any, Callable, Optional, List, Type, Union

from .request import Request
from .response import Response
from .validation import validate_and_convert, convert_to_dict
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
        request_format: Optional[Type] = None,
        response_format: Optional[Type] = None,
        cors_config: Optional[CORSConfig] = None,
    ):
        self.path = path
        self.method = method.upper()
        self.handler = handler
        self.request_format = request_format
        self.response_format = response_format
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

    def __init__(self, event: Dict[str, Any], context: Any):
        self.event = event
        self.context = context
        self.routes: List[Route] = []
        self._middleware: List[Callable] = []
        self._cors_config: Optional[CORSConfig] = None
        self._error_registry = get_global_registry()

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
                        route.request_format,
                        route.response_format,
                    )
                    new_router.routes.append(new_route)
                self.routes.extend(new_router.routes)
            else:
                self.routes.extend(router.routes)

    def _add_route(
        self,
        path: str,
        method: str,
        handler: Callable,
        request_format: Optional[Type] = None,
        response_format: Optional[Type] = None,
        cors: Union[bool, CORSConfig, None] = None,
    ) -> Callable:
        """ルートを追加"""
        cors_config = None
        if cors is True:
            # デフォルトの CORS 設定を使用
            cors_config = create_cors_config()
        elif isinstance(cors, CORSConfig):
            cors_config = cors

        route = Route(path, method, handler, request_format, response_format, cors_config)
        self.routes.append(route)
        return handler

    def _find_route(
        self, path: str, method: str
    ) -> tuple[Optional[Route], Optional[Dict[str, str]]]:
        """マッチするルートを検索"""
        for route in self.routes:
            path_params = route.match(path, method)
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

        # リクエストフォーマットが指定されている場合、リクエストをバリデーション
        validated_request_data = None
        if route.request_format:
            try:
                request_data = request.json()
                validated_request_data = validate_and_convert(request_data, route.request_format)
            except Exception as e:
                raise ValueError(f"リクエストバリデーションエラー: {str(e)}")

        # 最初の引数が request またはバリデーション済みリクエストかどうかをチェック
        param_names = list(handler_params.keys())
        if param_names and param_names[0] in ["request", "req"]:
            # 従来の方式（request を第一引数に渡す）
            if route.request_format and validated_request_data:
                return handler(validated_request_data)
            else:
                return handler(request)

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
                # デフォルト値を使用
                call_args[param_name] = param_info.default

        # request 引数がある場合は追加
        if "request" in handler_params:
            if route.request_format and validated_request_data:
                call_args["request"] = validated_request_data
            else:
                call_args["request"] = request

        # キーワード引数として渡す、もしくは引数なしで呼び出し
        return handler(**call_args) if call_args else handler()

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
        result = self._validate_response_format(result, route, request)
        if isinstance(result, dict) and "statusCode" in result:
            return Response(result)  # エラーレスポンス

        # 結果を Response オブジェクトに変換
        if isinstance(result, Response):
            response = result
        elif isinstance(result, dict):
            response = Response(result)
        else:
            response = Response({"result": result})

        # ミドルウェアを適用
        response = self._apply_middleware(request, response)

        # CORS ヘッダーを追加
        response = self._apply_cors_headers(request, response, route)

        return response

    def _validate_response_format(self, result: Any, route: Route, request: Request) -> Any:
        """レスポンスフォーマットをバリデーション"""
        if route.response_format and result is not None:
            try:
                if isinstance(result, dict):
                    validated_result = validate_and_convert(result, route.response_format)
                    return convert_to_dict(validated_result)
                elif hasattr(result, "__dict__"):
                    result_dict = result.__dict__ if hasattr(result, "__dict__") else {}
                    validated_result = validate_and_convert(result_dict, route.response_format)
                    return convert_to_dict(validated_result)
            except Exception as e:
                from .exceptions import InternalServerError

                validation_error = InternalServerError(
                    f"レスポンスバリデーションエラー: {str(e)}",
                    details={"validation_error": str(e)},
                )
                error_response = self._error_registry.handle_error(
                    validation_error, request, self.context
                )
                error_response = self._apply_cors_headers(request, error_response, route)
                return error_response.to_lambda_response()
        return result

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
