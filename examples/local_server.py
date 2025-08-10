#!/usr/bin/env python3
"""
lambapi ローカル開発サーバー
API Gateway の代替として、ローカルでの開発・テスト用に使用
"""

import json
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import sys
import os

# アプリケーションのインポート（app.py があることを前提）
try:
    from app import lambda_handler
except ImportError:
    print("Error: app.py が見つかりません。lambda_handler を含む app.py を作成してください。")
    sys.exit(1)


class LambdaHTTPHandler(BaseHTTPRequestHandler):
    """HTTP リクエストを Lambda イベント形式に変換するハンドラー"""

    def do_GET(self):
        self._handle_request("GET")

    def do_POST(self):
        self._handle_request("POST")

    def do_PUT(self):
        self._handle_request("PUT")

    def do_DELETE(self):
        self._handle_request("DELETE")

    def do_PATCH(self):
        self._handle_request("PATCH")

    def do_OPTIONS(self):
        self._handle_request("OPTIONS")

    def _handle_request(self, method):
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
            response = lambda_handler(event, context)

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

    def log_message(self, format, *args):
        """ログメッセージの出力をカスタマイズ"""
        return  # デフォルトのログ出力を無効化


def start_server(host="localhost", port=8000):
    """ローカルサーバーを起動"""
    server_address = (host, port)
    httpd = HTTPServer(server_address, LambdaHTTPHandler)

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


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="lambapi ローカル開発サーバー")
    parser.add_argument(
        "--host", default="localhost", help="バインドするホスト (デフォルト: localhost)"
    )
    parser.add_argument("--port", type=int, default=8000, help="ポート番号 (デフォルト: 8000)")
    parser.add_argument(
        "--app", default="app", help="アプリケーションモジュール名 (デフォルト: app)"
    )

    args = parser.parse_args()

    # 動的にアプリケーションをインポート
    if args.app != "app":
        try:
            import importlib

            app_module = importlib.import_module(args.app)
            example_lambda_handler = app_module.lambda_handler
        except ImportError as e:
            print(f"Error: {args.app}.py が見つかりません: {e}")
            sys.exit(1)
    else:
        example_lambda_handler = lambda_handler

    start_server(example_lambda_handler, args.host, args.port)
