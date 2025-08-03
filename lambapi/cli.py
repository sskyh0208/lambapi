"""
lambapi CLI ツール
pip install lambapi 後に使用可能なコマンドライン インターフェース
"""

import argparse
import sys
import os
from .local_server import main as server_main


def create_project() -> None:
    """新しい lambapi プロジェクトを作成（旧形式、下位互換性のため保持）"""
    parser = argparse.ArgumentParser(description="新しい lambapi プロジェクトを作成")
    parser.add_argument("project_name", help="プロジェクト名")
    parser.add_argument(
        "--template",
        choices=["basic", "crud"],
        default="basic",
        help="プロジェクトテンプレート (デフォルト: basic)",
    )

    args = parser.parse_args(sys.argv[2:])
    create_project_with_args(args.project_name, args.template)


def create_project_with_args(project_name: str, template: str = "basic") -> None:
    """新しい lambapi プロジェクトを作成"""
    project_dir = project_name

    if os.path.exists(project_dir):
        print(f"❌ エラー: ディレクトリ '{project_dir}' は既に存在します")
        sys.exit(1)

    # プロジェクトディレクトリを作成
    os.makedirs(project_dir)

    if template == "basic":
        create_basic_project(project_dir)
    elif template == "crud":
        create_crud_project(project_dir)

    print(
        f"""
✅ プロジェクト '{project_name}' を作成しました！

🚀 開始方法:
   cd {project_dir}
   pip install -r requirements.txt
   lambapi serve app
   
📖 詳細: README.md を参照してください
"""
    )


def create_basic_project(project_dir: str) -> None:
    """基本的なプロジェクトテンプレートを作成"""

    # app.py
    app_content = '''"""
基本的な lambapi アプリケーション
"""

from lambapi import API, create_lambda_handler


def create_app(event, context):
    app = API(event, context)
    
    @app.get("/")
    def root():
        return {
            "message": "Hello, lambapi!",
            "version": "1.0.0"
        }
    
    @app.get("/hello/{name}")
    def hello(name: str):
        return {"message": f"Hello, {name}!"}
    
    return app


# Lambda エントリーポイント
lambda_handler = create_lambda_handler(create_app)


if __name__ == "__main__":
    # ローカルテスト用
    import json
    
    test_event = {
        'httpMethod': 'GET',
        'path': '/',
        'queryStringParameters': {},
        'headers': {},
        'body': None
    }
    
    context = type('Context', (), {'aws_request_id': 'test-123'})()
    result = lambda_handler(test_event, context)
    print(json.dumps(result, indent=2, ensure_ascii=False))
'''

    # requirements.txt
    requirements_content = """lambapi
"""

    # README.md
    readme_content = f"""# {os.path.basename(project_dir)}

lambapi を使用した基本的な API プロジェクトです。

## 開発

### ローカルサーバーの起動

```bash
lambapi serve app
```

### テスト

```bash
curl http://localhost:8000/
curl http://localhost:8000/hello/world
```

## デプロイ

### SAM

```bash
sam build
sam deploy --guided
```

### Serverless Framework

```bash
serverless deploy
```

## 構成

- `app.py` - メインアプリケーション
- `requirements.txt` - Python 依存関係
- `template.yaml` - SAM テンプレート（オプション）
"""

    # template.yaml (SAM)
    template_content = """AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31

Description: lambapi サンプルアプリケーション

Globals:
  Function:
    Timeout: 30
    Runtime: python3.13

Resources:
  lambapiFunction:
    Type: AWS::Serverless::Function
    Properties:
      CodeUri: .
      Handler: app.lambda_handler
      Events:
        ApiGateway:
          Type: Api
          Properties:
            Path: /{proxy+}
            Method: ANY

Outputs:
  ApiUrl:
    Description: "API Gateway URL"
    Value: !Sub "https://${ServerlessRestApi}.execute-api.${AWS::Region}.amazonaws.com/Prod"
"""

    # ファイル作成
    with open(os.path.join(project_dir, "app.py"), "w", encoding="utf-8") as f:
        f.write(app_content)

    with open(os.path.join(project_dir, "requirements.txt"), "w", encoding="utf-8") as f:
        f.write(requirements_content)

    with open(os.path.join(project_dir, "README.md"), "w", encoding="utf-8") as f:
        f.write(readme_content)

    with open(os.path.join(project_dir, "template.yaml"), "w", encoding="utf-8") as f:
        f.write(template_content)


def create_crud_project(project_dir: str) -> None:
    """CRUD プロジェクトテンプレートを作成"""

    # app.py
    app_content = '''"""
CRUD API を含む lambapi アプリケーション
"""

from lambapi import API, Response, create_lambda_handler
from lambapi.exceptions import ValidationError, NotFoundError
import uuid
from datetime import datetime


def create_app(event, context):
    app = API(event, context)
    
    # インメモリデータストア（本番では DB を使用）
    items_db = {}
    
    @app.get("/")
    def root():
        return {
            "name": "CRUD API",
            "version": "1.0.0",
            "endpoints": [
                "GET /",
                "GET /items",
                "POST /items",
                "GET /items/{item_id}",
                "PUT /items/{item_id}",
                "DELETE /items/{item_id}"
            ]
        }
    
    @app.get("/items")
    def list_items(limit: int = 10, search: str = ""):
        """アイテム一覧取得"""
        items = list(items_db.values())
        
        # 検索フィルタ
        if search:
            items = [
                item for item in items 
                if search.lower() in item["name"].lower()
            ]
        
        # リミット適用
        items = items[:limit]
        
        return {
            "items": items,
            "total": len(items),
            "limit": limit
        }
    
    @app.post("/items")
    def create_item(request):
        """新しいアイテム作成"""
        data = request.json()
        
        # バリデーション
        if not data.get("name"):
            raise ValidationError("Name is required", field="name")
        
        # アイテム作成
        item_id = str(uuid.uuid4())
        item = {
            "id": item_id,
            "name": data["name"],
            "description": data.get("description", ""),
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        items_db[item_id] = item
        
        return Response({
            "message": "Item created successfully",
            "item": item
        }, status_code=201)
    
    @app.get("/items/{item_id}")
    def get_item(item_id: str):
        """特定のアイテム取得"""
        if item_id not in items_db:
            raise NotFoundError("Item", item_id)
        
        return {"item": items_db[item_id]}
    
    @app.put("/items/{item_id}")
    def update_item(item_id: str, request):
        """アイテム更新"""
        if item_id not in items_db:
            raise NotFoundError("Item", item_id)
        
        data = request.json()
        item = items_db[item_id]
        
        # 更新可能なフィールド
        if "name" in data:
            item["name"] = data["name"]
        if "description" in data:
            item["description"] = data["description"]
        
        item["updated_at"] = datetime.now().isoformat()
        
        return {
            "message": "Item updated successfully",
            "item": item
        }
    
    @app.delete("/items/{item_id}")
    def delete_item(item_id: str):
        """アイテム削除"""
        if item_id not in items_db:
            raise NotFoundError("Item", item_id)
        
        deleted_item = items_db.pop(item_id)
        
        return {
            "message": f"Item '{deleted_item['name']}' deleted successfully",
            "deleted_item_id": item_id
        }
    
    return app


# Lambda エントリーポイント
lambda_handler = create_lambda_handler(create_app)
'''

    # requirements.txt
    requirements_content = """lambapi
"""

    # README.md
    readme_content = f"""# {os.path.basename(project_dir)}

lambapi を使用した CRUD API プロジェクトです。

## 機能

- ✅ アイテムの作成・読み取り・更新・削除 (CRUD)
- ✅ バリデーション
- ✅ エラーハンドリング
- ✅ 検索・フィルタリング

## 開発

### ローカルサーバーの起動

```bash
lambapi serve app
```

### API テスト

```bash
# 一覧取得
curl http://localhost:8000/items

# 作成
curl -X POST http://localhost:8000/items \\
  -H "Content-Type: application/json" \\
  -d '{{"name":"テストアイテム","description":"説明"}}'

# 取得
curl http://localhost:8000/items/{{item_id}}

# 更新
curl -X PUT http://localhost:8000/items/{{item_id}} \\
  -H "Content-Type: application/json" \\
  -d '{{"name":"更新されたアイテム"}}'

# 削除
curl -X DELETE http://localhost:8000/items/{{item_id}}
```

## デプロイ

### SAM

```bash
sam build
sam deploy --guided
```

## 構成

- `app.py` - メインアプリケーション
- `requirements.txt` - Python 依存関係
- `template.yaml` - SAM テンプレート
"""

    # template.yaml
    template_content = """AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31

Description: lambapi CRUD API アプリケーション

Globals:
  Function:
    Timeout: 30
    Runtime: python3.13
    Environment:
      Variables:
        ENVIRONMENT: production

Resources:
  lambapiFunction:
    Type: AWS::Serverless::Function
    Properties:
      CodeUri: .
      Handler: app.lambda_handler
      Events:
        ApiGateway:
          Type: Api
          Properties:
            Path: /{proxy+}
            Method: ANY
            RestApiId: !Ref lambapiApi
  
  lambapiApi:
    Type: AWS::Serverless::Api
    Properties:
      StageName: prod
      Cors:
        AllowMethods: "'GET,POST,PUT,DELETE,OPTIONS'"
        AllowHeaders: "'Content-Type,Authorization'"
        AllowOrigin: "'*'"

Outputs:
  ApiUrl:
    Description: "API Gateway URL"
    Value: !Sub "https://${lambapiApi}.execute-api.${AWS::Region}.amazonaws.com/prod"
"""

    # ファイル作成
    with open(os.path.join(project_dir, "app.py"), "w", encoding="utf-8") as f:
        f.write(app_content)

    with open(os.path.join(project_dir, "requirements.txt"), "w", encoding="utf-8") as f:
        f.write(requirements_content)

    with open(os.path.join(project_dir, "README.md"), "w", encoding="utf-8") as f:
        f.write(readme_content)

    with open(os.path.join(project_dir, "template.yaml"), "w", encoding="utf-8") as f:
        f.write(template_content)


def main() -> None:
    """メイン CLI エントリーポイント"""
    parser = argparse.ArgumentParser(description="lambapi CLI")
    subparsers = parser.add_subparsers(dest="command", help="利用可能なコマンド")

    # serve コマンド
    serve_parser = subparsers.add_parser("serve", help="ローカル開発サーバーを起動")
    serve_parser.add_argument("app", help="アプリケーションファイル (例: app, app.py)")
    serve_parser.add_argument("--host", default="localhost", help="バインドするホスト")
    serve_parser.add_argument("--port", type=int, default=8000, help="ポート番号")

    # create コマンド
    create_parser = subparsers.add_parser("create", help="新しいプロジェクトを作成")
    create_parser.add_argument("project_name", help="プロジェクト名")
    create_parser.add_argument(
        "--template", choices=["basic", "crud"], default="basic", help="プロジェクトテンプレート"
    )

    args = parser.parse_args()

    if args.command == "serve":
        # ローカルサーバー起動
        sys.argv = ["lambapi", args.app, "--host", args.host, "--port", str(args.port)]
        server_main()
    elif args.command == "create":
        # プロジェクト作成
        create_project_with_args(args.project_name, args.template)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
