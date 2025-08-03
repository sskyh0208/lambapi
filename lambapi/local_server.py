"""
lambapi ローカル開発サーバー
pip install lambapi 後に使用可能なローカル開発ツール
"""

import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import sys
import os
import importlib.util
import argparse
import traceback
from typing import Any, Dict, Optional, Callable, Tuple


class LambdaHTTPHandler(BaseHTTPRequestHandler):
    """HTTP リクエストを Lambda イベント形式に変換するハンドラー"""

    def __init__(
        self,
        request: Any,
        client_address: Tuple[str, int],
        server: Any,
        lambda_handler: Callable[[Dict[str, Any], Any], Dict[str, Any]],
    ) -> None:
        self.lambda_handler = lambda_handler
        super().__init__(request, client_address, server)

    def do_GET(self) -> None:
        self._handle_request("GET")

    def do_POST(self) -> None:
        self._handle_request("POST")

    def do_PUT(self) -> None:
        self._handle_request("PUT")

    def do_DELETE(self) -> None:
        self._handle_request("DELETE")

    def do_PATCH(self) -> None:
        self._handle_request("PATCH")

    def do_OPTIONS(self) -> None:
        self._handle_request("OPTIONS")

    def _handle_request(self, method: str) -> None:
        """HTTP リクエストを処理"""
        try:
            # URL の解析
            parsed_url = urlparse(self.path)
            path = parsed_url.path
            query_params = parse_qs(parsed_url.query)

            # クエリパラメータを単一値に変換（Lambda の形式に合わせる）
            query_string_parameters = {}
            if query_params:
                for key, values in query_params.items():
                    query_string_parameters[key] = values[0] if values else ""

            # リクエストボディの読み取り
            content_length = int(self.headers.get("Content-Length", 0))
            body = None
            if content_length > 0:
                body = self.rfile.read(content_length).decode("utf-8")

            # Lambda イベントの構築
            event = {
                "httpMethod": method,
                "path": path,
                "queryStringParameters": (
                    query_string_parameters if query_string_parameters else None
                ),
                "headers": dict(self.headers),
                "body": body,
                "requestContext": {
                    "requestId": "local-request-id",
                    "stage": "local",
                    "httpMethod": method,
                    "path": path,
                    "protocol": "HTTP/1.1",
                    "requestTime": "01/Jan/2025:00:00:00 +0000",
                    "requestTimeEpoch": 1735689600,
                    "identity": {
                        "sourceIp": self.client_address[0],
                        "userAgent": self.headers.get("User-Agent", ""),
                    },
                },
                "isBase64Encoded": False,
            }

            # Lambda コンテキストの構築
            context = type(
                "Context",
                (),
                {
                    "aws_request_id": "local-request-id",
                    "log_group_name": "/aws/lambda/local-function",
                    "log_stream_name": "2025/01/01/[$LATEST]local-stream",
                    "function_name": "local-function",
                    "function_version": "$LATEST",
                    "invoked_function_arn": (
                        "arn:aws:lambda:local:123456789012:function:local-function"
                    ),
                    "memory_limit_in_mb": "128",
                    "remaining_time_in_millis": lambda: 30000,
                },
            )()

            # Lambda ハンドラーの実行
            response = self.lambda_handler(event, context)

            # HTTP レスポンスの送信
            status_code = response.get("statusCode", 200)
            headers = response.get("headers", {})
            body = response.get("body", "")

            # レスポンスヘッダーの設定
            self.send_response(status_code)

            # CORS ヘッダーの追加（開発用）
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header(
                "Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, PATCH, OPTIONS"
            )
            self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

            # カスタムヘッダーの追加
            for header_name, header_value in headers.items():
                self.send_header(header_name, header_value)

            # Content-Type の設定（デフォルトは JSON）
            if "Content-Type" not in headers:
                self.send_header("Content-Type", "application/json")

            self.end_headers()

            # レスポンスボディの送信
            if isinstance(body, str):
                self.wfile.write(body.encode("utf-8"))
            else:
                self.wfile.write(json.dumps(body).encode("utf-8"))

            # ログ出力
            print(f"{method} {path} -> {status_code}")

        except Exception as e:
            # エラーハンドリング
            print(f"Error handling request: {e}")
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            error_response = {"error": "Internal Server Error", "message": str(e)}
            self.wfile.write(json.dumps(error_response).encode("utf-8"))

    def log_message(self, format: str, *args: Any) -> None:
        """ログメッセージの出力をカスタマイズ"""
        # デフォルトのログ出力を無効化
        pass


def handle_import_error(e: ImportError, app_path: str, debug: bool = False) -> None:
    """ImportError の詳細ハンドリング"""
    print(f"❌ アプリケーション読み込みエラー: ImportError")
    print(f"📄 ファイル: {app_path}.py")
    print(f"💬 エラー: {str(e)}")

    if debug:
        print(f"\n🔍 詳細情報:")
        traceback.print_exc()

    print(f"\n💡 解決方法:")
    print(f"   - ファイル '{app_path}.py' が存在することを確認してください")
    print(f"   - 必要な依存関係がインストールされていることを確認してください")
    print(f"   - インポートパスが正しいことを確認してください")


def handle_syntax_error(e: SyntaxError, app_path: str, debug: bool = False) -> None:
    """SyntaxError の詳細ハンドリング"""
    print(f"❌ アプリケーション読み込みエラー: SyntaxError")
    print(f"📄 ファイル: {app_path}.py:{e.lineno if e.lineno else '?'}")
    print(f"💬 エラー: {str(e)}")

    if debug:
        print(f"\n🔍 詳細情報:")
        traceback.print_exc()

    print(f"\n💡 解決方法:")
    print(f"   - Python 構文をチェックしてください")
    print(f"   - インデントが正しいことを確認してください")
    print(f"   - 括弧やクォートの対応を確認してください")
    if e.lineno:
        print(f"   - {e.lineno} 行目付近を確認してください")


def handle_attribute_error(e: AttributeError, app_path: str, debug: bool = False) -> None:
    """AttributeError の詳細ハンドリング"""
    print(f"❌ アプリケーション読み込みエラー: AttributeError")
    print(f"📄 ファイル: {app_path}.py")
    print(f"💬 エラー: {str(e)}")

    if debug:
        print(f"\n🔍 詳細情報:")
        traceback.print_exc()

    print(f"\n💡 解決方法:")
    print(f"   - lambda_handler 関数が定義されていることを確認してください")
    print(f"   - create_lambda_handler() を正しく呼び出していることを確認してください")
    print(f"   - 例: lambda_handler = create_lambda_handler(create_app)")


def handle_name_error(e: NameError, app_path: str, debug: bool = False) -> None:
    """NameError の詳細ハンドリング"""
    print(f"❌ アプリケーション読み込みエラー: NameError")
    print(f"📄 ファイル: {app_path}.py")
    print(f"💬 エラー: {str(e)}")

    if debug:
        print(f"\n🔍 詳細情報:")
        traceback.print_exc()

    print(f"\n💡 解決方法:")
    print(f"   - 変数名のスペルを確認してください")
    print(f"   - 変数が定義されているかチェックしてください")
    print(f"   - スコープが正しいか確認してください")
    print(f"   - 必要なインポートが行われているか確認してください")


def handle_generic_error(e: Exception, app_path: str, debug: bool = False) -> None:
    """その他のエラーの詳細ハンドリング"""
    error_type = type(e).__name__
    print(f"❌ アプリケーション読み込みエラー: {error_type}")
    print(f"📄 ファイル: {app_path}.py")
    print(f"💬 エラー: {str(e)}")

    if debug:
        print(f"\n🔍 詳細情報:")
        traceback.print_exc()

    print(f"\n💡 解決方法:")
    print(f"   - アプリケーションコードを確認してください")
    print(f"   - --debug フラグを使用して詳細情報を確認してください")
    print(f"   - 例: lambapi serve {app_path} --debug")


def load_lambda_handler(
    app_path: str, debug: bool = False
) -> Optional[Callable[[Dict[str, Any], Any], Dict[str, Any]]]:
    """アプリケーションファイルから lambda_handler を動的にロード"""
    original_app_path = app_path
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
        except ImportError as e:
            handle_import_error(e, app_path, debug)
            return None
        except SyntaxError as e:
            handle_syntax_error(e, app_path, debug)
            return None
        except AttributeError as e:
            handle_attribute_error(e, app_path, debug)
            return None
        except NameError as e:
            handle_name_error(e, app_path, debug)
            return None
        except Exception as e:
            handle_generic_error(e, app_path, debug)
            return None

    # モジュールとしてインポートを試す
    try:
        module = __import__(app_path, fromlist=[""])
        if not hasattr(module, "lambda_handler"):
            raise AttributeError(f"{app_path} に lambda_handler が見つかりません")
        handler = getattr(module, "lambda_handler")
        return handler  # type: ignore
    except ImportError as e:
        # ファイルが見つからない場合の詳細表示
        print(f"❌ アプリケーション読み込みエラー: FileNotFoundError")
        print(f"📄 ファイル: {original_app_path}")
        print(f"💬 エラー: アプリケーション '{original_app_path}' が見つかりません")

        if debug:
            print(f"\n🔍 詳細情報:")
            print(f"   - 検索パス: {os.getcwd()}")
            print(f"   - 試行ファイル: {file_path}")

        print(f"\n💡 解決方法:")
        print(f"   - ファイル '{app_path}.py' が存在することを確認してください")
        print(f"   - 現在のディレクトリ: {os.getcwd()}")
        print(f"   - 利用可能な .py ファイル:")
        try:
            py_files = [f for f in os.listdir(".") if f.endswith(".py") and not f.startswith("__")]
            if py_files:
                for py_file in py_files[:5]:  # 最大 5 つまで表示
                    print(f"     - {py_file[:-3]}")
            else:
                print(f"     (なし)")
        except PermissionError:
            print(f"     (ディレクトリの読み取り権限がありません)")
        
        return None
    except SyntaxError as e:
        handle_syntax_error(e, app_path, debug)
        return None
    except AttributeError as e:
        handle_attribute_error(e, app_path, debug)
        return None
    except NameError as e:
        handle_name_error(e, app_path, debug)
        return None
    except Exception as e:
        handle_generic_error(e, app_path, debug)
        return None


def start_server(
    lambda_handler: Callable[[Dict[str, Any], Any], Dict[str, Any]],
    host: str = "localhost",
    port: int = 8000,
) -> None:
    """ローカルサーバーを起動"""

    class ServerWithHandler(HTTPServer):
        def __init__(
            self,
            server_address: Tuple[str, int],
            handler_class: Any,
            lambda_handler: Callable[[Dict[str, Any], Any], Dict[str, Any]],
        ) -> None:
            self.lambda_handler = lambda_handler
            super().__init__(server_address, handler_class)

    def handler_factory(
        lambda_handler: Callable[[Dict[str, Any], Any], Dict[str, Any]],
    ) -> Callable[..., LambdaHTTPHandler]:
        def handler(
            request: Any, client_address: Tuple[str, int], server: Any
        ) -> LambdaHTTPHandler:
            return LambdaHTTPHandler(request, client_address, server, lambda_handler)

        return handler

    server_address = (host, port)

    # ポートが既に使用されているかチェック
    import socket

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind((host, port))
        sock.close()
    except OSError as e:
        sock.close()
        if e.errno == 48 or "Address already in use" in str(e):  # macOS/Linux
            print(f"❌ エラー: ポート {port} は既に使用されています")
            print(
                f"""
💡 解決方法:
   1. 別のポートを使用してください:
      lambapi serve {sys.argv[1] if len(sys.argv) > 1 else 'app'} --port {port + 1}
   
   2. 使用中のプロセスを確認:
      lsof -i :{port}
   
   3. プロセスを停止:
      kill <PID>
"""
            )
            sys.exit(1)
        elif e.errno == 10048 or "Only one usage of each socket address" in str(e):  # Windows
            print(f"❌ エラー: ポート {port} は既に使用されています")
            print(
                f"""
💡 解決方法:
   1. 別のポートを使用してください:
      lambapi serve {sys.argv[1] if len(sys.argv) > 1 else 'app'} --port {port + 1}
   
   2. 使用中のプロセスを確認:
      netstat -ano | findstr :{port}
"""
            )
            sys.exit(1)
        else:
            print(f"❌ サーバー起動エラー: {e}")
            sys.exit(1)

    try:
        httpd = ServerWithHandler(server_address, handler_factory(lambda_handler), lambda_handler)
    except OSError as e:
        if e.errno == 48 or "Address already in use" in str(e):  # macOS/Linux
            print(f"❌ エラー: ポート {port} は既に使用されています")
            print(
                f"""
💡 解決方法:
   1. 別のポートを使用してください:
      lambapi serve {sys.argv[1] if len(sys.argv) > 1 else 'app'} --port {port + 1}
   
   2. 使用中のプロセスを確認:
      lsof -i :{port}
   
   3. プロセスを停止:
      kill <PID>
"""
            )
            sys.exit(1)
        elif e.errno == 10048 or "Only one usage of each socket address" in str(e):  # Windows
            print(f"❌ エラー: ポート {port} は既に使用されています")
            print(
                f"""
💡 解決方法:
   1. 別のポートを使用してください:
      lambapi serve {sys.argv[1] if len(sys.argv) > 1 else 'app'} --port {port + 1}
   
   2. 使用中のプロセスを確認:
      netstat -ano | findstr :{port}
"""
            )
            sys.exit(1)
        else:
            print(f"❌ サーバー起動エラー: {e}")
            sys.exit(1)

    print(
        f"""
🚀 lambapi ローカルサーバーを起動しました
   URL: http://{host}:{port}
   
💡 使用例:
   curl http://{host}:{port}/
   curl http://{host}:{port}/hello/world
   curl -X POST http://{host}:{port}/users \\
        -H "Content-Type: application/json" -d '{{"name":"test"}}'
   
🛑 停止: Ctrl+C
"""
    )

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n\n✋ サーバーを停止しました")
        httpd.server_close()


def main() -> None:
    """コマンドライン エントリーポイント"""
    parser = argparse.ArgumentParser(description="lambapi ローカル開発サーバー")
    parser.add_argument("app", help="アプリケーションファイル (例: app, app.py, myapp)")
    parser.add_argument(
        "--host", default="localhost", help="バインドするホスト (デフォルト: localhost)"
    )
    parser.add_argument("--port", type=int, default=8000, help="ポート番号 (デフォルト: 8000)")
    parser.add_argument("--debug", action="store_true", help="詳細なデバッグ情報を表示")

    args = parser.parse_args()

    lambda_handler = load_lambda_handler(args.app, args.debug)
    if lambda_handler:
        start_server(lambda_handler, args.host, args.port)
    else:
        print(f"\n🚨 アプリケーションの読み込みに失敗しました")
        print(f"\n📖 サンプルコード:")
        print(
            f"""
   # {args.app}.py
   from lambapi import API, create_lambda_handler
   
   def create_app(event, context):
       app = API(event, context)
       
       @app.get("/")
       def hello():
           return {{"message": "Hello, World!"}}
       
       return app
   
   lambda_handler = create_lambda_handler(create_app)
"""
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
