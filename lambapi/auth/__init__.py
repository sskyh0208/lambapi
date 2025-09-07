"""
DynamoDB 認証機能

LambAPI の DynamoDB 認証システムを提供します。
"""

from .dynamodb_auth import DynamoDBAuth

__all__ = ["DynamoDBAuth"]
