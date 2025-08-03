"""
lambapi ローカルサーバーのテスト
"""

import unittest
import socket
import tempfile
import os
from unittest.mock import patch, MagicMock
from lambapi.local_server import load_lambda_handler


class TestLocalServer(unittest.TestCase):
    """ローカルサーバーのテストクラス"""

    def test_load_lambda_handler_success(self):
        """lambda_handler の正常ロードをテスト"""
        # テスト用の一時ファイルを作成
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(
                """
from lambapi import API, create_lambda_handler

def create_app(event, context):
    app = API(event, context)
    
    @app.get("/")
    def hello():
        return {"message": "Hello from test!"}
    
    return app

lambda_handler = create_lambda_handler(create_app)
"""
            )
            temp_file = f.name

        try:
            # .py を除いたファイル名でテスト
            app_name = temp_file[:-3]
            handler = load_lambda_handler(app_name)
            self.assertIsNotNone(handler)
            self.assertTrue(callable(handler))
        finally:
            os.unlink(temp_file)

    def test_load_lambda_handler_missing_file(self):
        """存在しないファイルのテスト"""
        # 新しい実装では例外を発生させず、None を返してエラーメッセージを表示
        with patch("builtins.print"):  # エラーメッセージの出力をモック
            handler = load_lambda_handler("nonexistent_app")
            self.assertIsNone(handler)

    def test_load_lambda_handler_missing_handler(self):
        """lambda_handler が存在しないファイルのテスト"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(
                """
# lambda_handler が定義されていないファイル
def some_function():
    pass
"""
            )
            temp_file = f.name

        try:
            app_name = temp_file[:-3]
            # 新しい実装では例外を発生させず、None を返してエラーメッセージを表示
            with patch("builtins.print"):  # エラーメッセージの出力をモック
                handler = load_lambda_handler(app_name)
                self.assertIsNone(handler)
        finally:
            os.unlink(temp_file)

    def test_port_conflict_real_usage(self):
        """実際のポート競合をテスト"""
        from lambapi.local_server import start_server

        # 利用可能なポートを見つける
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(("localhost", 0))
        _, port = sock.getsockname()
        sock.close()

        # ポートを占有
        blocking_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        blocking_socket.bind(("localhost", port))
        blocking_socket.listen(1)

        try:
            # モックハンドラー
            mock_handler = MagicMock()
            mock_handler.return_value = {"statusCode": 200, "body": "{}"}

            # start_server がシステム終了することを確認
            with patch("sys.exit") as mock_exit:
                # sys.exit がモックされているので SystemExit は発生しない
                # その代わり、UnboundLocalError が発生する（httpd が定義されないため）
                with self.assertRaises(UnboundLocalError):
                    start_server(mock_handler, "localhost", port)
                mock_exit.assert_called_with(1)

        finally:
            blocking_socket.close()


if __name__ == "__main__":
    unittest.main()
