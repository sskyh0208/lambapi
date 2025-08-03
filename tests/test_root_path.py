"""
root_path 機能のテスト

API クラスの root_path 機能が正しく動作することを確認するテストです。
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lambapi import API


def test_empty_root_path():
    """空の root_path は空文字列になる"""
    api = API({}, None, "")
    assert api.root_path == ""


def test_none_root_path():
    """None の root_path は空文字列になる"""
    api = API({}, None)
    assert api.root_path == ""


def test_valid_root_path_with_leading_slash():
    """先頭スラッシュありの root_path は正しく処理される"""
    api = API({}, None, "/api/v1")
    assert api.root_path == "/api/v1"


def test_valid_root_path_without_leading_slash():
    """先頭スラッシュなしの root_path は先頭スラッシュが追加される"""
    api = API({}, None, "api/v1")
    assert api.root_path == "/api/v1"


def test_root_path_with_trailing_slash():
    """末尾スラッシュは除去される"""
    api = API({}, None, "/api/v1/")
    assert api.root_path == "/api/v1"


def test_root_path_with_multiple_slashes():
    """重複スラッシュは正規化される"""
    api = API({}, None, "//api//v1//")
    assert api.root_path == "/api/v1"


def test_root_path_single_slash():
    """単一スラッシュは空文字列になる"""
    api = API({}, None, "/")
    assert api.root_path == ""


def test_root_path_multiple_slashes_only():
    """複数スラッシュのみは空文字列になる"""
    api = API({}, None, "///")
    assert api.root_path == ""


def test_normalize_path_no_root_path():
    """root_path がない場合は元のパスが返される"""
    api = API({}, None, "")
    assert api._normalize_path("/users") == "/users"
    assert api._normalize_path("/") == "/"


def test_normalize_path_exact_match():
    """パスが root_path と完全一致する場合は / が返される"""
    api = API({}, None, "/api/v1")
    assert api._normalize_path("/api/v1") == "/"


def test_normalize_path_with_prefix():
    """パスが root_path/ で始まる場合は root_path が除去される"""
    api = API({}, None, "/api/v1")
    assert api._normalize_path("/api/v1/users") == "/users"
    assert api._normalize_path("/api/v1/users/123") == "/users/123"


def test_normalize_path_partial_match_not_removed():
    """パスが root_path の部分一致の場合は除去されない"""
    api = API({}, None, "/api")
    assert api._normalize_path("/api-v2/users") == "/api-v2/users"
    assert api._normalize_path("/apisomething") == "/apisomething"


def test_normalize_path_no_match():
    """パスが root_path と一致しない場合は元のパスが返される"""
    api = API({}, None, "/api/v1")
    assert api._normalize_path("/users") == "/users"
    assert api._normalize_path("/v2/users") == "/v2/users"


def test_route_matching_with_root_path():
    """root_path が設定されている場合のルートマッチング"""
    event = {
        "httpMethod": "GET",
        "path": "/api/v1/users",
        "headers": {},
        "queryStringParameters": None,
        "body": None,
    }

    api = API(event, None, "/api/v1")

    @api.get("/users")
    def get_users():
        return {"users": []}

    route, path_params = api._find_route("/api/v1/users", "GET")
    assert route is not None
    assert route.path == "/users"
    assert path_params == {}


def test_route_matching_with_path_params():
    """root_path とパスパラメータの組み合わせ"""
    event = {
        "httpMethod": "GET",
        "path": "/api/v1/users/123",
        "headers": {},
        "queryStringParameters": None,
        "body": None,
    }

    api = API(event, None, "/api/v1")

    @api.get("/users/{user_id}")
    def get_user(user_id: str):
        return {"user_id": user_id}

    route, path_params = api._find_route("/api/v1/users/123", "GET")
    assert route is not None
    assert route.path == "/users/{user_id}"
    assert path_params == {"user_id": "123"}


def test_route_not_matching_wrong_root_path():
    """間違った root_path でのルートマッチング失敗"""
    api = API({}, None, "/api/v1")

    @api.get("/users")
    def get_users():
        return {"users": []}

    route, path_params = api._find_route("/v2/users", "GET")
    assert route is None
    assert path_params is None


def test_route_matching_exact_root_path():
    """root_path そのものでのルートマッチング"""
    api = API({}, None, "/api/v1")

    @api.get("/")
    def get_root():
        return {"message": "API v1"}

    route, path_params = api._find_route("/api/v1", "GET")
    assert route is not None
    assert route.path == "/"
    assert path_params == {}


def test_full_request_handling_with_root_path():
    """root_path を使った完全なリクエスト処理"""
    event = {
        "httpMethod": "GET",
        "path": "/api/v1/health",
        "headers": {},
        "queryStringParameters": None,
        "body": None,
    }

    api = API(event, None, "/api/v1")

    @api.get("/health")
    def health_check():
        return {"status": "ok"}

    response = api.handle_request()
    assert response["statusCode"] == 200


def test_deeply_nested_root_path():
    """深くネストされた root_path"""
    api = API({}, None, "/api/v1/internal/service")
    assert api.root_path == "/api/v1/internal/service"

    assert api._normalize_path("/api/v1/internal/service/health") == "/health"
    assert api._normalize_path("/api/v1/internal/service") == "/"


def test_unicode_in_root_path():
    """Unicode 文字を含む root_path"""
    api = API({}, None, "/api/テスト")
    assert api.root_path == "/api/テスト"

    assert api._normalize_path("/api/テスト/users") == "/users"


def test_special_characters_in_root_path():
    """特殊文字を含む root_path"""
    api = API({}, None, "/api/v1.0")
    assert api.root_path == "/api/v1.0"

    assert api._normalize_path("/api/v1.0/users") == "/users"


def test_empty_path_normalization():
    """空パスの正規化"""
    api = API({}, None, "/api/v1")
    assert api._normalize_path("") == ""


def test_root_slash_only_path():
    """ルートスラッシュのみのパス"""
    api = API({}, None, "/api/v1")
    assert api._normalize_path("/") == "/"


if __name__ == "__main__":
    # 簡単なテストランナー
    import traceback

    test_functions = [
        test_empty_root_path,
        test_none_root_path,
        test_valid_root_path_with_leading_slash,
        test_valid_root_path_without_leading_slash,
        test_root_path_with_trailing_slash,
        test_root_path_with_multiple_slashes,
        test_root_path_single_slash,
        test_root_path_multiple_slashes_only,
        test_normalize_path_no_root_path,
        test_normalize_path_exact_match,
        test_normalize_path_with_prefix,
        test_normalize_path_partial_match_not_removed,
        test_normalize_path_no_match,
        test_route_matching_with_root_path,
        test_route_matching_with_path_params,
        test_route_not_matching_wrong_root_path,
        test_route_matching_exact_root_path,
        test_full_request_handling_with_root_path,
        test_deeply_nested_root_path,
        test_unicode_in_root_path,
        test_special_characters_in_root_path,
        test_empty_path_normalization,
        test_root_slash_only_path,
    ]

    passed = 0
    failed = 0

    for test_func in test_functions:
        try:
            test_func()
            print(f"✓ {test_func.__name__}")
            passed += 1
        except Exception as e:
            print(f"✗ {test_func.__name__}: {e}")
            traceback.print_exc()
            failed += 1

    print(f"\n テスト結果: {passed} 成功, {failed} 失敗")

    if failed == 0:
        print("すべてのテストが成功しました!")
    else:
        print(f"{failed} 個のテストが失敗しました。")
