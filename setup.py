"""
lambapi セットアップファイル
"""

from setuptools import setup, find_packages
import os


# README を読み込み
def read_readme():
    try:
        with open("README.md", "r", encoding="utf-8") as fh:
            return fh.read()
    except FileNotFoundError:
        return "モダンな AWS Lambda 用 API フレームワーク"


# バージョンを取得
def get_version():
    version_file = os.path.join("lambapi", "__init__.py")
    with open(version_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("__version__"):
                return line.split('"')[1]
    return "0.1.0"


setup(
    name="lambapi",
    version=get_version(),
    author="Yoshihiro Sasaki",
    author_email="sskyh1988@gmail.com",
    description="モダンな AWS Lambda 用 API フレームワーク",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/sskyh0208/lambapi",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Topic :: Internet :: WWW/HTTP :: HTTP Servers",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.10",
    install_requires=[
        # Lambda 環境では標準ライブラリのみを使用
    ],
    extras_require={
        "auth": [
            "boto3>=1.28.0",
            "PyJWT>=2.8.0",
            "bcrypt>=4.0.0",
            "pynamodb>=5.0.0",
        ],
        "dev": [
            "pytest>=6.0",
            "pytest-cov>=2.0",
            "black>=22.0",
            "flake8>=4.0",
            "mypy>=0.900",
            "isort>=5.0",
            "bandit[toml]>=1.7",
            "safety>=2.0",
            "orjson>=3.9.0",
        ],
    },
    keywords="lambda api aws serverless http rest",
    project_urls={
        "Bug Reports": "https://github.com/sskyh0208/lambapi/issues",
        "Source": "https://github.com/sskyh0208/lambapi",
        "Documentation": "https://sskyh0208.github.io/lambapi/",
    },
)
