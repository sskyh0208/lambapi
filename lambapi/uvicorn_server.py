"""
lambapi uvicorn 統合サーバー
AWS Lambda ハンドラーを ASGI アプリケーションとして実行
"""

import asyncio
from typing import Dict, Any, Callable, Optional
from urllib.parse import parse_qs

from .json_handler import JSONHandler


class LambdaASGIApp:
    """Lambda ハンドラーを ASGI アプリケーションに変換"""

    def __init__(self, lambda_handler: Callable[[Dict[str, Any], Any], Dict[str, Any]]) -> None:
        self.lambda_handler = lambda_handler

    async def __call__(self, scope: Dict[str, Any], receive: Callable, send: Callable) -> None:
        """ASGI アプリケーションエントリーポイント"""
        if scope["type"] == "http":
            await self._handle_http(scope, receive, send)
        elif scope["type"] == "websocket":
            # WebSocket は未対応
            await self._send_error_response(send, 501, "WebSocket not supported")
        else:
            await self._send_error_response(send, 400, "Unsupported scope type")

    async def _handle_http(self, scope: Dict[str, Any], receive: Callable, send: Callable) -> None:
        """HTTP リクエストの処理"""
        method = scope.get("method", "UNKNOWN")
        path = scope.get("path", "/")

        try:
            # ASGI スコープから Lambda イベントを構築
            event = await self._build_lambda_event(scope, receive)

            # Lambda コンテキストを構築
            context = self._build_lambda_context(scope)

            # Lambda ハンドラーを実行（非同期対応）
            if asyncio.iscoroutinefunction(self.lambda_handler):
                response = await self.lambda_handler(event, context)
            else:
                # 同期関数を非同期で実行
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(None, self.lambda_handler, event, context)

            # リクエストログを表示（詳細）
            status_code = response.get("statusCode", 200)
            body = response.get("body", "")
            print(f"📝 {method} {path} -> {status_code}")
            if status_code >= 400:
                # エラーレスポンスの場合は詳細を表示
                print(
                    f"🔍 Error Response Body: {body[:200]}{'...' if len(str(body)) > 200 else ''}"
                )

            # Lambda レスポンスを ASGI レスポンスに変換
            await self._send_lambda_response(response, send)

        except Exception as e:
            # エラーハンドリング
            print(f"❌ {method} {path} -> 500 (Error: {str(e)})")
            await self._send_error_response(send, 500, f"Internal Server Error: {str(e)}")

    async def _build_lambda_event(self, scope: Dict[str, Any], receive: Callable) -> Dict[str, Any]:
        """ASGI スコープから Lambda イベントを構築"""
        method = scope["method"]
        path = scope["path"]
        query_string = scope["query_string"].decode("utf-8")
        headers = dict(scope["headers"])

        # ヘッダーを文字列に変換
        str_headers = {}
        for key, value in headers.items():
            if isinstance(key, bytes):
                key = key.decode("latin-1")
            if isinstance(value, bytes):
                value = value.decode("latin-1")
            str_headers[key] = value

        # クエリパラメータの解析
        query_params = None
        if query_string:
            parsed_params = parse_qs(query_string)
            query_params = {}
            for key, values in parsed_params.items():
                query_params[key] = values[0] if values else ""

        # リクエストボディの読み取り
        body = await self._read_body(receive)

        # Lambda イベント形式の構築
        event = {
            "httpMethod": method,
            "path": path,
            "queryStringParameters": query_params,
            "headers": str_headers,
            "body": body,
            "requestContext": {
                "requestId": "uvicorn-request-id",
                "stage": "local",
                "httpMethod": method,
                "path": path,
                "protocol": "HTTP/1.1",
                "requestTime": "01/Jan/2025:00:00:00 +0000",
                "requestTimeEpoch": 1735689600,
                "identity": {
                    "sourceIp": scope.get("client", ["127.0.0.1", 0])[0],
                    "userAgent": str_headers.get("user-agent", ""),
                },
            },
            "isBase64Encoded": False,
        }

        return event

    async def _read_body(self, receive: Callable) -> Optional[str]:
        """リクエストボディを読み取り"""
        body_parts = []

        while True:
            message = await receive()
            if message["type"] == "http.request":
                body_part = message.get("body", b"")
                if body_part:
                    body_parts.append(body_part)

                if not message.get("more_body", False):
                    break
            elif message["type"] == "http.disconnect":
                break

        if body_parts:
            body_bytes = b"".join(body_parts)
            return body_bytes.decode("utf-8")

        return None

    def _build_lambda_context(self, scope: Dict[str, Any]) -> Any:
        """Lambda コンテキストを構築"""

        class Context:
            def __init__(self) -> None:
                self.aws_request_id = "uvicorn-request-id"
                self.log_group_name = "/aws/lambda/uvicorn-function"
                self.log_stream_name = "2025/01/01/[$LATEST]uvicorn-stream"
                self.function_name = "uvicorn-function"
                self.function_version = "$LATEST"
                self.invoked_function_arn = (
                    "arn:aws:lambda:local:123456789012:function:uvicorn-function"
                )
                self.memory_limit_in_mb = "128"

            def get_remaining_time_in_millis(self) -> int:
                return 30000

        return Context()

    async def _send_lambda_response(self, response: Dict[str, Any], send: Callable) -> None:
        """Lambda レスポンスを ASGI レスポンスとして送信"""
        status_code = response.get("statusCode", 200)
        headers = response.get("headers", {})
        body = response.get("body", "")

        # ヘッダーをバイト形式に変換
        asgi_headers = []

        # CORS ヘッダーの追加（開発用）
        # 注意: lambapi の enable_cors() が呼ばれている場合は重複を避ける
        cors_headers_exist = any(
            key.lower() in ["access-control-allow-origin", "Access-Control-Allow-Origin"]
            for key in headers.keys()
        )

        if not cors_headers_exist:
            default_headers = {
                "access-control-allow-origin": "*",
                "access-control-allow-methods": "GET, POST, PUT, DELETE, PATCH, OPTIONS",
                "access-control-allow-headers": "Content-Type, Authorization",
            }

            # デフォルトヘッダーを先に追加（CORS 設定がない場合のみ）
            for key, value in default_headers.items():
                asgi_headers.append([key.encode("latin-1"), value.encode("latin-1")])

        # カスタムヘッダーを追加
        for key, value in headers.items():
            key_bytes = key.encode("latin-1") if isinstance(key, str) else key
            value_bytes = value.encode("latin-1") if isinstance(value, str) else value
            asgi_headers.append([key_bytes, value_bytes])

        # Content-Type の設定（デフォルトは JSON）
        has_content_type = any(
            header[0].decode("latin-1").lower() == "content-type" for header in asgi_headers
        )
        if not has_content_type:
            asgi_headers.append([b"content-type", b"application/json"])

        # レスポンス開始
        await send(
            {
                "type": "http.response.start",
                "status": status_code,
                "headers": asgi_headers,
            }
        )

        # レスポンスボディ送信
        if body is not None:
            if isinstance(body, str):
                body_bytes = body.encode("utf-8")
            elif isinstance(body, dict) or isinstance(body, list):
                body_bytes = JSONHandler.dumps(body).encode("utf-8")
            else:
                body_bytes = str(body).encode("utf-8")
        else:
            body_bytes = b""

        await send(
            {
                "type": "http.response.body",
                "body": body_bytes,
            }
        )

    async def _send_error_response(self, send: Callable, status_code: int, message: str) -> None:
        """エラーレスポンスを送信"""
        error_response = {
            "error": "Server Error",
            "message": message,
        }

        await send(
            {
                "type": "http.response.start",
                "status": status_code,
                "headers": [
                    [b"content-type", b"application/json"],
                    [b"access-control-allow-origin", b"*"],
                ],
            }
        )

        await send(
            {
                "type": "http.response.body",
                "body": JSONHandler.dumps(error_response).encode("utf-8"),
            }
        )


def create_asgi_app(
    lambda_handler: Callable[[Dict[str, Any], Any], Dict[str, Any]],
) -> LambdaASGIApp:
    """Lambda ハンドラーから ASGI アプリケーションを作成"""
    return LambdaASGIApp(lambda_handler)


def load_lambda_handler(app_path: str) -> Optional[Callable[[Dict[str, Any], Any], Dict[str, Any]]]:
    """アプリケーションファイルから lambda_handler を動的にロード"""
    import importlib.util
    import os

    if app_path.endswith(".py"):
        app_path = app_path[:-3]  # .py を除去

    # カレントディレクトリのファイルを試す
    file_path = f"{app_path}.py"
    if os.path.exists(file_path):
        try:
            spec = importlib.util.spec_from_file_location("app_module", file_path)
            if spec is None:
                raise ImportError(f"Cannot load spec from {file_path}")
            module = importlib.util.module_from_spec(spec)
            if spec.loader is None:
                raise ImportError(f"No loader for {file_path}")
            spec.loader.exec_module(module)

            if not hasattr(module, "lambda_handler"):
                raise AttributeError(f"{file_path} に lambda_handler が見つかりません")

            handler = getattr(module, "lambda_handler")
            return handler  # type: ignore
        except Exception as e:
            print(f"❌ Error loading {file_path}: {e}")
            return None

    # モジュールとしてインポートを試す
    try:
        module = __import__(app_path, fromlist=[""])
        if not hasattr(module, "lambda_handler"):
            raise AttributeError(f"{app_path} に lambda_handler が見つかりません")
        handler = getattr(module, "lambda_handler")
        return handler  # type: ignore
    except Exception as e:
        print(f"❌ Error loading {app_path}: {e}")
        return None


def create_asgi_app_factory(app_path: str) -> str:
    """アプリケーションファクトリーファイルを作成して、インポートパスを返す"""
    import tempfile
    import os

    # 一時ファイル作成
    temp_dir = tempfile.gettempdir()
    factory_path = os.path.join(temp_dir, "lambapi_asgi_factory.py")

    # ファクトリーファイルの内容
    factory_content = f'''"""
Dynamic ASGI factory for lambapi uvicorn integration
Generated automatically - do not edit manually
"""

def create_app():
    """ASGI アプリケーションファクトリー"""
    import sys
    import os
    sys.path.insert(0, os.getcwd())
    
    from lambapi.uvicorn_server import load_lambda_handler, create_asgi_app
    
    lambda_handler = load_lambda_handler("{app_path}")
    if lambda_handler is None:
        raise RuntimeError(f"Could not load lambda_handler from {app_path}")
    
    return create_asgi_app(lambda_handler)

# uvicorn が参照するアプリケーション
app = create_app()
'''

    # ファクトリーファイルを書き込み
    with open(factory_path, "w", encoding="utf-8") as f:
        f.write(factory_content)

    # インポートパスを返す（拡張子なし）
    factory_name = os.path.splitext(os.path.basename(factory_path))[0]
    return f"{factory_name}:app"


def serve_with_uvicorn(
    app_path: str,
    host: str = "localhost",
    port: int = 8000,
    reload: bool = True,
    debug: bool = False,
    **uvicorn_kwargs: Any,
) -> None:
    """uvicorn を使用してサーバーを起動"""
    try:
        import uvicorn
    except ImportError:
        print("❌ uvicorn がインストールされていません")
        print("   pip install uvicorn でインストールしてください")
        return

    print(
        f"""
🚀 lambapi uvicorn サーバーを起動しました
   URL: http://{host}:{port}
   リロード: {'有効' if reload else '無効'}

💡 使用例:
   curl http://{host}:{port}/
   curl http://{host}:{port}/hello/world
   curl -X POST http://{host}:{port}/users \\
        -H "Content-Type: application/json" -d '{{"name":"test"}}'

🛑 停止: Ctrl+C
"""
    )

    # uvicorn 設定
    config = {
        "host": host,
        "port": port,
        "log_level": "debug" if debug else "info",
        "access_log": True,
        **uvicorn_kwargs,
    }

    if reload:
        # リロード有効時はアプリケーションファクトリーを使用
        import tempfile
        import sys

        # 一時ディレクトリを Python パスに追加
        temp_dir = tempfile.gettempdir()
        if temp_dir not in sys.path:
            sys.path.insert(0, temp_dir)

        app_import_string = create_asgi_app_factory(app_path)
        config.update(
            {
                "reload": True,
                "reload_dirs": ["."],
                "reload_includes": ["*.py"],
            }
        )

        # uvicorn でサーバー起動（インポート文字列）
        uvicorn.run(app_import_string, **config)
    else:
        # リロード無効時は従来通り
        lambda_handler = load_lambda_handler(app_path)
        if lambda_handler is None:
            print(f"❌ Lambda ハンドラーの読み込みに失敗しました: {app_path}")
            return

        asgi_app = create_asgi_app(lambda_handler)
        config["reload"] = False

        # uvicorn でサーバー起動（アプリオブジェクト）
        uvicorn.run(asgi_app, **config)
