# DynamoDBAuth 例外クラス

v0.2.15 以降、DynamoDBAuth は設定エラーや運用エラーを適切にハンドリングするための専用例外クラスを提供します。

## 🎯 概要

従来の `ValueError` の代わりに、用途別の例外クラスを使用することで：

- **明確なエラー分類**: 設定エラー、バリデーションエラー、機能エラーを区別
- **詳細な情報提供**: エラーの詳細情報を構造化された形で取得
- **適切なエラーハンドリング**: ユーザー向けとシステム向けのエラーを分離

## 📋 例外クラス一覧

| 例外クラス | 用途 | ステータス | エラーコード | 発生場面 |
|-----------|------|------------|--------------|----------|
| `AuthConfigError` | 設定エラー | 500 | `AUTH_CONFIG_ERROR` | 無効なモデル、インデックス不備 |
| `ModelValidationError` | モデル定義エラー | 400 | `MODEL_VALIDATION_ERROR` | フィールド不足、トークン設定エラー |
| `PasswordValidationError` | パスワード要件違反 | 400 | `VALIDATION_ERROR` | 文字数不足、文字種要件違反 |
| `FeatureDisabledError` | 機能無効エラー | 400 | `FEATURE_DISABLED` | 無効機能の使用試行 |
| `RolePermissionError` | 権限不足エラー | 403 | `PERMISSION_DENIED` | 必要ロール不足 |

### AuthConfigError

**用途**: DynamoDBAuth の設定エラー  
**ステータスコード**: 500 (Internal Server Error)  
**エラーコード**: `AUTH_CONFIG_ERROR`

**発生場面**:
- 無効な PynamoDB モデルの指定
- 必要な GSI インデックスの不備
- 依存関係の不足

```python
from lambapi.exceptions import AuthConfigError

try:
    auth = DynamoDBAuth(
        user_model=str,  # 無効なモデル
        session_model=UserSession,
        secret_key="secret"
    )
except AuthConfigError as e:
    print(f"設定エラー: {e.message}")
    print(f"設定タイプ: {e.details['config_type']}")
    # 出力: 設定タイプ: user_model
```

### ModelValidationError

**用途**: PynamoDB モデルの定義エラー  
**ステータスコード**: 400 (Bad Request)  
**エラーコード**: `MODEL_VALIDATION_ERROR`

**発生場面**:
- JWT トークンへの password フィールド含有
- モデルに存在しないフィールドの指定
- 必要な属性の不足

```python
from lambapi.exceptions import ModelValidationError

try:
    auth = DynamoDBAuth(
        user_model=User,
        session_model=UserSession,
        secret_key="secret",
        token_include_fields=["id", "password", "nonexistent_field"]
    )
except ModelValidationError as e:
    print(f"モデルエラー: {e.message}")
    print(f"モデル名: {e.details['model_name']}")
    print(f"フィールド名: {e.details['field_name']}")
```

### PasswordValidationError

**用途**: パスワード要件違反  
**ステータスコード**: 400 (Bad Request)  
**エラーコード**: `VALIDATION_ERROR`

**発生場面**:
- パスワードの最小文字数不足
- 大文字・小文字・数字・特殊文字の要件違反

```python
from lambapi.exceptions import PasswordValidationError

try:
    auth.validate_password("abc")  # 短すぎる
except PasswordValidationError as e:
    print(f"パスワードエラー: {e.message}")
    print(f"要件タイプ: {e.details['requirement_type']}")
    # 出力: 要件タイプ: min_length
```

**要件タイプ一覧**:
- `min_length`: 最小文字数不足
- `uppercase`: 大文字不足
- `lowercase`: 小文字不足
- `digit`: 数字不足
- `special_char`: 特殊文字不足

### FeatureDisabledError

**用途**: 無効化された機能の使用  
**ステータスコード**: 400 (Bad Request)  
**エラーコード**: `FEATURE_DISABLED`

**発生場面**:
- `is_email_login=False` 時の email ログイン試行

```python
from lambapi.exceptions import FeatureDisabledError

auth = DynamoDBAuth(
    user_model=User,
    session_model=UserSession,
    secret_key="secret",
    is_email_login=False  # email ログイン無効
)

try:
    token = auth.email_login("user@example.com", "password")
except FeatureDisabledError as e:
    print(f"機能エラー: {e.message}")
    print(f"機能名: {e.details['feature_name']}")
    # 出力: 機能名: email_login
```

### RolePermissionError

**用途**: ロール権限不足エラー  
**ステータスコード**: 403 (Forbidden)  
**エラーコード**: `PERMISSION_DENIED`

**発生場面**:
- `@auth.require_role()` で必要なロールを持たない場合

```python
from lambapi.exceptions import RolePermissionError
from lambapi import API

@app.post("/admin")
@auth.require_role("admin")
def admin_endpoint(user: Authenticated):
    return {"message": "admin access"}

# userロールでadminエンドポイントにアクセスした場合
try:
    # 内部的にrequire_roleデコレータで実行される
    pass
except RolePermissionError as e:
    print(f"権限エラー: {e.message}")
    print(f"ユーザーロール: {e.details['user_role']}")
    print(f"必要なロール: {e.details['required_roles']}")
    print(f"リソース: {e.details['resource']}")
    print(f"アクション: {e.details['action']}")
    # 出力例:
    # 権限エラー: 必要なロール: admin
    # ユーザーロール: user
    # 必要なロール: ['admin']
    # リソース: endpoint
    # アクション: access
```

## 🔧 実装パターン

### 1. セットアップ時のエラーハンドリング

```python
import logging
from lambapi.exceptions import AuthConfigError, ModelValidationError
from lambapi.auth import DynamoDBAuth

logger = logging.getLogger(__name__)

def create_auth_system():
    """認証システムの初期化（開発者向けエラー）"""
    try:
        auth = DynamoDBAuth(
            user_model=User,
            session_model=UserSession,
            secret_key=os.environ["JWT_SECRET"],
            is_email_login=True,
            password_min_length=8,
            password_require_digit=True
        )
        return auth
        
    except AuthConfigError as e:
        # システム設定エラー: ログに記録して異常終了
        logger.critical(f"認証設定エラー: {e.message}")
        logger.critical(f"設定項目: {e.details.get('config_type')}")
        raise SystemExit("認証システムの初期化に失敗しました")
        
    except ModelValidationError as e:
        # モデル定義エラー: 開発者に詳細情報を提供
        logger.error(f"モデル定義エラー: {e.message}")
        logger.error(f"対象モデル: {e.details.get('model_name')}")
        logger.error(f"問題フィールド: {e.details.get('field_name')}")
        raise SystemExit("モデル定義を確認してください")
```

### 2. ユーザー操作のエラーハンドリング

```python
from lambapi.exceptions import PasswordValidationError, FeatureDisabledError, RolePermissionError
from lambapi import API

@app.post("/auth/signup")
def signup(data: dict = Body(...)):
    """ユーザー登録（ユーザー向けエラー）"""
    try:
        user = User(
            id=data["email"],
            password=data["password"],
            email=data["email"],
            name=data["name"]
        )
        token = auth.signup(user)
        return {"token": token, "message": "登録完了"}
        
    except PasswordValidationError as e:
        # ユーザーに分かりやすいエラー応答
        return {
            "error": "password_validation_error",
            "message": "パスワードが要件を満たしていません",
            "details": {
                "requirement": e.details.get('requirement_type'),
                "description": e.message
            }
        }, 400
        
    except ValidationError as e:
        return {
            "error": "validation_error",
            "message": e.message,
            "field": e.details.get('field')
        }, 400

@app.post("/auth/email-login")  
def email_login(data: dict = Body(...)):
    """Emailログイン"""
    try:
        token = auth.email_login(data["email"], data["password"])
        return {"token": token}
        
    except FeatureDisabledError as e:
        return {
            "error": "feature_disabled",
            "message": "Emailログインは利用できません",
            "details": {
                "feature": e.details.get('feature_name'),
                "suggestion": "IDでのログインをご利用ください"
            }
        }, 400
        
    except AuthenticationError as e:
        return {
            "error": "authentication_failed",
            "message": "認証に失敗しました"
        }, 401

@app.post("/admin/users")
@auth.require_role("admin")
def admin_users(user: Authenticated):
    """管理者専用エンドポイント"""
    try:
        # 管理者機能の実行
        return {"users": get_all_users()}
    except RolePermissionError as e:
        return {
            "error": "permission_denied",
            "message": "この機能にはadmin権限が必要です",
            "details": {
                "user_role": e.details.get('user_role'),
                "required_roles": e.details.get('required_roles'),
                "suggestion": "管理者に権限昇格を依頼してください"
            }
        }, 403
```

### 3. エラー情報の活用

```python
def get_password_requirements(auth):
    """パスワード要件の動的取得"""
    requirements = []
    
    try:
        auth.validate_password("")  # 意図的にエラーを発生
    except PasswordValidationError as e:
        # エラー詳細から要件情報を構築
        req_type = e.details.get('requirement_type')
        requirements.append({
            "type": req_type,
            "message": e.message,
            "satisfied": False
        })
    
    return {
        "min_length": auth.password_min_length,
        "require_uppercase": auth.password_require_uppercase,
        "require_lowercase": auth.password_require_lowercase,
        "require_digit": auth.password_require_digit,
        "require_special": auth.password_require_special,
        "current_errors": requirements
    }
```

## 📊 エラー構造

### 共通構造

すべての例外クラスは以下の構造を持ちます：

```python
class CustomException(APIError):
    def to_dict(self) -> Dict[str, Any]:
        return {
            "error": self.error_code,        # 例: "AUTH_CONFIG_ERROR"
            "message": self.message,         # 例: "user_model must be a PynamoDB Model"
            "status_code": self.status_code, # 例: 500
            "details": self.details          # 例: {"config_type": "user_model"}
        }
```

### 詳細情報（details）

各例外クラスが提供する詳細情報：

#### AuthConfigError
```python
{
    "config_type": str  # "user_model", "session_model", "email_index", "dependencies"
}
```

#### ModelValidationError  
```python
{
    "model_name": str,           # 対象モデル名
    "field_name": str,           # 問題のフィールド名（該当する場合）
    "missing_fields": List[str], # 不足フィールド一覧（該当する場合）
    "available_fields": List[str] # 利用可能フィールド一覧（該当する場合）
}
```

#### PasswordValidationError
```python
{
    "field": "password",
    "requirement_type": str  # "min_length", "uppercase", "lowercase", "digit", "special_char"
}
```

#### FeatureDisabledError
```python
{
    "feature_name": str  # "email_login"
}
```

#### RolePermissionError
```python
{
    "user_role": str,          # 現在のユーザーロール
    "required_roles": List[str], # 必要なロール一覧
    "resource": str,           # アクセス対象リソース
    "action": str             # 実行しようとしたアクション
}
```

## 🚀 移行ガイド

### v0.2.14 以前からの移行

**Before (v0.2.14):**
```python
try:
    auth = DynamoDBAuth(user_model=str, session_model=UserSession, secret_key="secret")
except ValueError as e:
    print(f"エラー: {str(e)}")  # 汎用的なエラー
```

**After (v0.2.15+):**
```python
try:
    auth = DynamoDBAuth(user_model=str, session_model=UserSession, secret_key="secret")
except AuthConfigError as e:
    print(f"設定エラー: {e.message}")
    print(f"設定タイプ: {e.details['config_type']}")  # 詳細情報
```

### 後方互換性

- 既存の `ValueError` キャッチは動作しません
- 新しい例外クラスは `APIError` を継承しているため、`APIError` でのキャッチは可能
- 移行のための一時的な対応として、両方の例外を同時にキャッチすることも可能：

```python
try:
    auth = DynamoDBAuth(...)
except (AuthConfigError, ValueError) as e:
    # 移行期間中の暫定対応
    handle_error(e)
```

## 📝 ベストプラクティス

### 1. エラーレベルの分離

```python
# システムレベルエラー（開発者向け）
try:
    auth = create_auth_system()
except (AuthConfigError, ModelValidationError) as e:
    logger.critical(f"システム設定エラー: {e.message}")
    raise SystemExit()

# ユーザーレベルエラー（エンドユーザー向け）  
try:
    result = auth.signup(user)
except (PasswordValidationError, FeatureDisabledError) as e:
    return user_friendly_error(e)
```

### 2. ログ記録の活用

```python
import structlog

logger = structlog.get_logger()

try:
    auth.validate_password(password)
except PasswordValidationError as e:
    logger.warning(
        "password_validation_failed",
        requirement_type=e.details.get('requirement_type'),
        user_id=user.id
    )
    raise
```

### 3. エラーメトリクスの収集

```python
import prometheus_client

password_error_counter = prometheus_client.Counter(
    'auth_password_validation_errors_total',
    'Password validation errors',
    ['requirement_type']
)

try:
    auth.validate_password(password)
except PasswordValidationError as e:
    password_error_counter.labels(
        requirement_type=e.details.get('requirement_type')
    ).inc()
    raise
```

### 4. 例外継承を活用したエラーハンドリング

```python
from lambapi.exceptions import APIError, ValidationError

# 親クラスで全ての認証関連例外をキャッチ
@error_handler.catch(APIError)
def handle_api_error(e: APIError):
    """全てのAPI例外の統一ハンドラ"""
    return {
        "error": e.error_code,
        "message": e.message,
        "status_code": e.status_code,
        "details": e.details
    }

# より具体的な例外を個別にハンドリング  
@error_handler.catch(ValidationError)  
def handle_validation_error(e: ValidationError):
    """バリデーションエラー（PasswordValidationErrorも含む）"""
    return {
        "error": "validation_failed",
        "message": "入力値を確認してください",
        "field": e.details.get('field'),
        "validation_type": e.details.get('requirement_type')
    }

@error_handler.catch(RolePermissionError)
def handle_permission_error(e: RolePermissionError):
    """権限不足エラーの専用ハンドラ"""
    return {
        "error": "access_denied", 
        "message": "この操作には適切な権限が必要です",
        "user_role": e.details.get('user_role'),
        "required_roles": e.details.get('required_roles')
    }
```