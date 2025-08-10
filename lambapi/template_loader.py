"""
CLI テンプレート読み込み用ユーティリティ
"""

import os
from typing import Dict


class TemplateLoader:
    """テンプレートファイルを読み込むクラス"""

    def __init__(self) -> None:
        self.templates_dir = os.path.join(os.path.dirname(__file__), "templates")

    def load_template(self, template_name: str, **kwargs: str) -> str:
        """
        テンプレートファイルを読み込み、変数置換を行う

        Args:
            template_name: テンプレートファイル名（拡張子込み）
            **kwargs: テンプレート内の変数置換用パラメータ

        Returns:
            str: 置換済みのテンプレート内容
        """
        template_path = os.path.join(self.templates_dir, template_name)

        if not os.path.exists(template_path):
            raise FileNotFoundError(f"Template file not found: {template_path}")

        with open(template_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 変数置換（kwargs が空の場合はそのまま返す）
        if kwargs:
            return content.format(**kwargs)
        else:
            return content

    def get_template_files(self, template_type: str) -> Dict[str, str]:
        """
        指定されたテンプレートタイプの全ファイルを取得

        Args:
            template_type: "basic" または "crud"

        Returns:
            Dict[str, str]: ファイル名 -> テンプレート内容のマッピング
        """
        templates = {}

        # テンプレートファイルのマッピング
        file_mapping = {
            "app.py": f"{template_type}_app.py",
            "requirements.txt": f"{template_type}_requirements.txt",
            "README.md": f"{template_type}_readme.md",
            "template.yaml": f"{template_type}_template.yaml",
        }

        for target_file, template_file in file_mapping.items():
            try:
                templates[target_file] = self.load_template(template_file)
            except FileNotFoundError:
                # テンプレートファイルが存在しない場合はスキップ
                pass

        return templates
