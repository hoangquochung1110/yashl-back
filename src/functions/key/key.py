import json
import math
import os
import secrets
import string
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError

BASE = 62

UPPERCASE_OFFSET = 55
LOWERCASE_OFFSET = 61
DIGIT_OFFSET = 48


def lambda_handler(event, context):
    """
    Create or resolve key for a destination URL.
    """
    request_ctx = event['requestContext']
    method = request_ctx['httpMethod']
    match method:
        case "GET":
            path_params = event['pathParameters']
            short_key = path_params['short_key']
            key = saturate(short_key)
            return resolve_key(key=key)
        case  "POST":
            body = json.loads(event['body'])
            user_id = body.get('user_id', '')
            url = body['destination_url']
            return generate_key(url=url, user_id=user_id)
        case _:
            return create_response(405, {'error': 'Method not allowed'})


def create_response(status_code: int, body: dict[str, Any]) -> dict[str, Any]:
    """Create a standardized API Gateway response."""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Allow-Methods': 'OPTIONS,POST,GET',
        },
        'body': json.dumps(body)
    }

def generate_key(url, user_id=""):
    shortened_path = generate_shorten_path()
    key_id = saturate(shortened_path)
    attrs_to_create = dict(
        key_id=key_id,
        shorten_path=shortened_path,
        destination_url=url,
    )
    if user_id:
        attrs_to_create.update({'user_id': user_id})
    create_entry(**attrs_to_create)
    return create_response(200, {'key': shortened_path})

def resolve_key(key):
    db_client = DynamoDBWrapper(table=os.environ["DYNAMO_DB"])
    item = db_client.update_item(key={'key_id': key})
    if item:
        return {    
                'statusCode': 200,
                'headers': {
                    'Access-Control-Allow-Headers': 'Content-Type',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'OPTIONS,POST,GET',
                },
                'body': json.dumps({
                    'destination_url': item.get('destination_url'),
                }),
            }
    else:
        return create_response(
            404,
            {'error': f"Item with key_id {key} not found"},
        )

def generate_shorten_path():
    CHARACTERS = string.ascii_letters + string.digits
    return ''.join((secrets.choice(CHARACTERS) for _ in range(6)))

def saturate(key) -> int:
    """
    Turn the base [BASE] number [key] into an integer
    """
    int_sum = 0
    reversed_key = key[::-1]
    for idx, char in enumerate(reversed_key):
        int_sum += true_ord(char) * int(math.pow(BASE, idx))
    return int_sum

def true_ord(char):
    """
    Turns a digit [char] in character representation
    from the number system with base [BASE] into an integer.
    """
    
    if char.isdigit():
        return ord(char) - DIGIT_OFFSET
    elif 'A' <= char <= 'Z':
        return ord(char) - UPPERCASE_OFFSET
    elif 'a' <= char <= 'z':
        return ord(char) - LOWERCASE_OFFSET
    else:
        raise ValueError("%s is not a valid character" % char)

def true_chr(integer):
    """
    Turns an integer [integer] into digit in base [BASE]
    as a character representation.
    """

    if integer < 10:
        return chr(integer + DIGIT_OFFSET)
    elif 10 <= integer <= 35:
        return chr(integer + UPPERCASE_OFFSET)
    elif 36 <= integer < 62:
        return chr(integer + LOWERCASE_OFFSET)
    else:
        raise ValueError("%d is not a valid integer in the range of base %d" % (integer, BASE))

def create_entry(**kwargs):
    db_client = DynamoDBWrapper(table=os.environ["DYNAMO_DB"])
    db_client.create_item({
        'click_count': 0,
        **kwargs,
    })


class DynamoDBWrapper:
    def __init__(self, table, region=''):
        """
        Initialize the DynamoDBWrapper with the table name and AWS region.
        
        :param table_name: Name of the DynamoDB table.
        :param region_name: AWS region where the table is located. Default is 'us-east-1'.
        """
        self.table = table
        self.region = region or 'ap-southeast-1'
        self.dynamodb = boto3.resource('dynamodb', region_name=self.region)
        self.table = self.dynamodb.Table(self.table)

    def create_item(self, item):
        """
        Inserts a new item into the DynamoDB table.

        :param item: A dictionary representing the item to be inserted.
                     Example: {'id': '123', 'name': 'John Doe'}
        :return: Response from the DynamoDB service.
        :raises: Exception if the operation fails.
        """
        try:
            response = self.table.put_item(Item=item)
            return response
        except (BotoCoreError, ClientError) as e:
            print(f"Error creating item in DynamoDB: {e}")
            raise

    def get_item(self, key):
        """
        Retrieves an item from the DynamoDB table by its primary key.

        :param key: A dictionary representing the key of the item to be fetched.
                    Example: {'id': '123'}
        :return: The retrieved item as a dictionary, or None if the item does not exist.
        :raises: Exception if the operation fails.
        """
        try:
            response = self.table.get_item(Key=key)
            return response.get('Item')
        except (BotoCoreError, ClientError) as e:
            print(f"Error retrieving item from DynamoDB: {e}")
            raise
    
    def update_item(self, key):
        try:
            response = self.table.update_item(
                Key=key,
                UpdateExpression="SET click_count = click_count + :inc",
                ExpressionAttributeValues={
                    ':inc': 1
                },
                ConditionExpression="attribute_exists(key_id)",
                ReturnValues='ALL_NEW',
            )
            item = response.get('Attributes')
            return item
        except (BotoCoreError, ClientError) as e:
            print(f"Error retrieving item from DynamoDB: {e}")
            raise