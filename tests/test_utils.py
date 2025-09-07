"""
ユーティリティ関数のテスト

lambapi.utils モジュールの各機能をテストします。
"""

import pytest
from unittest.mock import Mock
from lambapi.utils import create_lambda_handler
from lambapi.core import API


class TestCreateLambdaHandler:
    """create_lambda_handler 関数のテスト"""

    def test_create_lambda_handler_basic(self):
        """基本的な lambda_handler 作成のテスト"""
        # モック API
        mock_api = Mock(spec=API)
        mock_api.handle_request.return_value = {"statusCode": 200, "body": "success"}

        def mock_app_factory(event, context):
            return mock_api

        # lambda_handler を作成
        handler = create_lambda_handler(mock_app_factory)

        # 関数が作成されていることを確認
        assert callable(handler)
        assert handler.__name__ == "lambda_handler"

    def test_lambda_handler_execution(self):
        """lambda_handler の実行テスト"""
        # モック API
        mock_api = Mock(spec=API)
        expected_response = {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": '{"message": "Hello, World!"}',
        }
        mock_api.handle_request.return_value = expected_response

        def mock_app_factory(event, context):
            return mock_api

        # lambda_handler を作成
        handler = create_lambda_handler(mock_app_factory)

        # テスト用の event と context
        test_event = {
            "httpMethod": "GET",
            "path": "/",
            "headers": {},
            "queryStringParameters": None,
            "body": None,
        }
        test_context = Mock()
        test_context.aws_request_id = "test-request-id"

        # ハンドラーを実行
        result = handler(test_event, test_context)

        # 結果を検証
        assert result == expected_response
        mock_api.handle_request.assert_called_once()

    def test_lambda_handler_with_different_events(self):
        """異なるイベントでの lambda_handler 実行テスト"""
        # モック API
        mock_api = Mock(spec=API)
        mock_api.handle_request.return_value = {"statusCode": 201, "body": "created"}

        call_args = []

        def mock_app_factory(event, context):
            call_args.append((event, context))
            return mock_api

        handler = create_lambda_handler(mock_app_factory)

        # 異なるイベントでテスト
        events = [
            {
                "httpMethod": "POST",
                "path": "/users",
                "headers": {"Content-Type": "application/json"},
                "body": '{"name": "Alice"}',
            },
            {
                "httpMethod": "GET",
                "path": "/users/123",
                "queryStringParameters": {"include": "profile"},
            },
            {"httpMethod": "DELETE", "path": "/users/456"},
        ]

        contexts = [Mock(aws_request_id=f"request-{i}") for i in range(len(events))]

        # 各イベントでハンドラーを実行
        for i, (event, context) in enumerate(zip(events, contexts)):
            result = handler(event, context)
            assert result == {"statusCode": 201, "body": "created"}

            # app_factory が正しい引数で呼ばれていることを確認
            assert call_args[i] == (event, context)

        # handle_request が 3 回呼ばれていることを確認
        assert mock_api.handle_request.call_count == 3

    def test_lambda_handler_with_exception_in_app_factory(self):
        """app_factory で例外が発生した場合のテスト"""

        def failing_app_factory(event, context):
            raise ValueError("App factory error")

        handler = create_lambda_handler(failing_app_factory)

        test_event = {"httpMethod": "GET", "path": "/"}
        test_context = Mock()

        # 例外がそのまま伝播することを確認
        with pytest.raises(ValueError, match="App factory error"):
            handler(test_event, test_context)

    def test_lambda_handler_with_exception_in_handle_request(self):
        """handle_request で例外が発生した場合のテスト"""
        mock_api = Mock(spec=API)
        mock_api.handle_request.side_effect = RuntimeError("Handle request error")

        def mock_app_factory(event, context):
            return mock_api

        handler = create_lambda_handler(mock_app_factory)

        test_event = {"httpMethod": "GET", "path": "/"}
        test_context = Mock()

        # 例外がそのまま伝播することを確認
        with pytest.raises(RuntimeError, match="Handle request error"):
            handler(test_event, test_context)

    def test_lambda_handler_preserves_return_types(self):
        """lambda_handler が様々な戻り値型を保持することをテスト"""
        return_values = [
            {"statusCode": 200, "body": "string"},
            {"statusCode": 201, "body": '{"json": "data"}', "headers": {"Custom": "header"}},
            {"statusCode": 404, "body": "Not Found"},
            {"statusCode": 500, "body": "Internal Server Error", "headers": {}},
        ]

        for expected_return in return_values:
            mock_api = Mock(spec=API)
            mock_api.handle_request.return_value = expected_return

            def mock_app_factory(event, context):
                return mock_api

            handler = create_lambda_handler(mock_app_factory)

            test_event = {"httpMethod": "GET", "path": "/"}
            test_context = Mock()

            result = handler(test_event, test_context)
            assert result == expected_return

    def test_lambda_handler_with_real_api_instance(self):
        """実際の API インスタンスでのテスト"""

        def real_app_factory(event, context):
            app = API(event, context)

            @app.get("/")
            def hello():
                return {"message": "Hello from real API"}

            return app

        handler = create_lambda_handler(real_app_factory)

        # API Gateway 形式のイベント
        test_event = {
            "httpMethod": "GET",
            "path": "/",
            "headers": {},
            "queryStringParameters": None,
            "body": None,
            "requestContext": {"requestId": "test-request"},
        }
        test_context = Mock()
        test_context.aws_request_id = "test-context-id"

        result = handler(test_event, test_context)

        # 結果を検証
        assert result["statusCode"] == 200
        assert "message" in result["body"]

    def test_lambda_handler_callable_signature(self):
        """lambda_handler の呼び出しシグネチャテスト"""
        mock_api = Mock(spec=API)
        mock_api.handle_request.return_value = {"statusCode": 200}

        def mock_app_factory(event, context):
            return mock_api

        handler = create_lambda_handler(mock_app_factory)

        # 正しい引数の数で呼び出せることを確認
        test_event = {}
        test_context = None

        # 2 つの引数で呼び出し可能
        result = handler(test_event, test_context)
        assert result == {"statusCode": 200}

        # 引数が足りない場合はエラー
        with pytest.raises(TypeError):
            handler(test_event)  # context が不足

        # 引数が多すぎる場合もエラー
        with pytest.raises(TypeError):
            handler(test_event, test_context, "extra_arg")

    def test_lambda_handler_with_none_values(self):
        """None や Empty 値でのテスト"""
        mock_api = Mock(spec=API)
        mock_api.handle_request.return_value = {"statusCode": 200, "body": "ok"}

        def mock_app_factory(event, context):
            return mock_api

        handler = create_lambda_handler(mock_app_factory)

        # None や empty 値でのテスト
        test_cases = [
            ({}, None),
            (None, Mock()),
            ({}, {}),
            ({"httpMethod": None}, Mock()),
        ]

        for event, context in test_cases:
            result = handler(event, context)
            assert result == {"statusCode": 200, "body": "ok"}

    def test_multiple_handlers_independence(self):
        """複数のハンドラーの独立性テスト"""
        # 2 つの異なる app_factory
        mock_api1 = Mock(spec=API)
        mock_api1.handle_request.return_value = {"statusCode": 200, "body": "api1"}

        mock_api2 = Mock(spec=API)
        mock_api2.handle_request.return_value = {"statusCode": 201, "body": "api2"}

        def app_factory1(event, context):
            return mock_api1

        def app_factory2(event, context):
            return mock_api2

        # 2 つのハンドラーを作成
        handler1 = create_lambda_handler(app_factory1)
        handler2 = create_lambda_handler(app_factory2)

        test_event = {"httpMethod": "GET", "path": "/"}
        test_context = Mock()

        # それぞれが独立して動作することを確認
        result1 = handler1(test_event, test_context)
        result2 = handler2(test_event, test_context)

        assert result1 == {"statusCode": 200, "body": "api1"}
        assert result2 == {"statusCode": 201, "body": "api2"}

        # 各 API が 1 回ずつ呼ばれていることを確認
        mock_api1.handle_request.assert_called_once()
        mock_api2.handle_request.assert_called_once()

    def test_lambda_handler_context_propagation(self):
        """context の伝播テスト"""
        received_contexts = []

        def context_checking_app_factory(event, context):
            received_contexts.append(context)
            mock_api = Mock(spec=API)
            mock_api.handle_request.return_value = {"statusCode": 200}
            return mock_api

        handler = create_lambda_handler(context_checking_app_factory)

        # 異なる context でテスト
        contexts = [
            Mock(aws_request_id="req1", function_name="func1"),
            Mock(aws_request_id="req2", function_name="func2"),
            Mock(aws_request_id="req3", function_name="func3"),
        ]

        for context in contexts:
            handler({}, context)

        # すべての context が正しく伝播されていることを確認
        assert len(received_contexts) == 3
        for i, received_context in enumerate(received_contexts):
            assert received_context is contexts[i]

    def test_app_factory_function_signature(self):
        """app_factory 関数のシグネチャ検証テスト"""

        # 正常なシグネチャ
        def valid_app_factory(event, context):
            return Mock(spec=API)

        # lambda_handler が作成できることを確認
        handler = create_lambda_handler(valid_app_factory)
        assert callable(handler)

        # 引数が少なすぎる factory
        def invalid_app_factory_few_args(event):
            return Mock(spec=API)

        # 引数が多すぎる factory
        def invalid_app_factory_many_args(event, context, extra):
            return Mock(spec=API)

        # 作成時は問題ないが、実行時にエラーになる
        handler_few = create_lambda_handler(invalid_app_factory_few_args)
        handler_many = create_lambda_handler(invalid_app_factory_many_args)

        test_event = {}
        test_context = Mock()

        # 引数が足りない場合
        with pytest.raises(TypeError):
            handler_few(test_event, test_context)

        # 引数が多すぎる場合
        with pytest.raises(TypeError):
            handler_many(test_event, test_context)
