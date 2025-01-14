import json
import math
import os
import secrets
import string
from decimal import Decimal
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
            resource_path = request_ctx['resourcePath']
            if resource_path.endswith('/{short_key}'):
                path_params = event['pathParameters']
                short_key = path_params['short_key']
                key = saturate(short_key)
                return resolve_key(key=key, short_path=short_key)
            else:
                query_params = event['queryStringParameters']
                user_id = query_params.get('user_id')
                return list_keys(user_id=user_id)
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
    shortened_path = ShortUrl.generate_short_path()
    key_id = saturate(shortened_path)
    key_data = dict(
        key_id=key_id,
        short_path=shortened_path,
        target_url=url,
    )
    short_url = ShortUrl()
    short_url.create(**key_data)
    if user_id:
        user = User()
        user_data = {"key_id": key_id}
        user_item = user.get(user_id)
        if user_item is None:
            user.create(user_id=user_id, keys=[user_data])
        else:
            user.update(user_id, user_data) 
            
    return create_response(200, {'short_path': shortened_path})

def resolve_key(key, short_path):
    short_url = ShortUrl()
    item = short_url.update(
        key={
            'key_id': key,
            'short_path': short_path,
        }
    )
    if item:
        return {    
                'statusCode': 200,
                'headers': {
                    'Access-Control-Allow-Headers': 'Content-Type',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'OPTIONS,POST,GET',
                },
                'body': json.dumps({
                    'target_url': item.get('target_url'),
                }),
            }
    else:
        return create_response(
            404,
            {'error': f"Item with key_id {key} not found"},
        )


def list_keys(user_id, *args, **kwargs):
    user = User()
    short_url = ShortUrl()
    user_item = user.get(user_id=user_id)
    key_ids = [item["key_id"] for item in user_item["keys"]]
    keys = [
        {
            'key_id': int(key_id),
            'short_path': dehydrate(int(key_id))
        }
        for key_id in key_ids
    ]
    res = short_url.get_batch(keys)
    return {
        'statusCode': 200,
        'body': json.dumps({'keys': res}, cls=DecimalEncoder),
        'headers': {
            'Access-Control-Allow-Origin': '*',
        }
    }


def dehydrate(integer):
    """
    Turn an integer [integer] into a base [BASE] number
    in string representation
    """
    # we won't step into the while if integer is 0
    # so we just solve for that case here
    if integer == 0:
        return '0'
    
    string = ""
    while integer > 0:
        remainder = integer % BASE
        string = true_chr(remainder) + string
        integer //= BASE
    return string

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


class ShortUrl:

    def __init__(self):
        """
        To represent ShortUrl item.

        Attrs:
        - key_id (partition key)
        - short_path (sort key)
        - hits
        """
        self.table_name = os.environ["DYNAMO_DB_KEY"]
        self.region = 'ap-southeast-1'
        self.dynamodb = boto3.resource('dynamodb', region_name=self.region)
        self.table = self.dynamodb.Table(self.table_name)


    @classmethod
    def generate_short_path(cls: str):
        CHARACTERS = string.ascii_letters + string.digits
        return ''.join((secrets.choice(CHARACTERS) for _ in range(6)))

    def create(
        self,
        key_id,
        short_path,
        target_url,
        hits=0,
    ):
        """
        Inserts a new item into the DynamoDB table.

        :param item: A dictionary representing the item to be inserted.
                     Example: {'id': '123', 'name': 'John Doe'}
        :return: Response from the DynamoDB service.
        :raises: Exception if the operation fails.
        """
        item = {
            'key_id': key_id,
            'short_path': short_path,
            'target_url': target_url,
            'hits': hits
        }
        try:
            response = self.table.put_item(Item=item)
            return response
        except (BotoCoreError, ClientError) as e:
            print(f"Error creating item in DynamoDB: {e}")
            raise

    def get_batch(self, keys):
        # Perform the batch get item operation
        print(keys)
        response = self.dynamodb.batch_get_item(
            RequestItems={
                self.table_name: {
                    'Keys': keys
                }
            }
        )

        # Extract and return the items from the response
        items = response.get('Responses', {}).get(self.table_name, [])
        return items

    def update(self, key):
        try:
            response = self.table.update_item(
                Key=key,
                UpdateExpression="SET hits = hits + :inc",
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


class User:
    def __init__(self):
        """
        To represent User item.

        Attrs:
        - user_id (partition key)
        - keys: List of keys
            - key_id
        """
        self.table_name = os.environ["DYNAMO_DB_USER"]
        self.region = 'ap-southeast-1'
        self.dynamodb = boto3.resource('dynamodb', region_name=self.region)
        self.table = self.dynamodb.Table(self.table_name)

    def create(self, user_id: str, keys: list = None):
        """
        Create or update a user item in DynamoDB.

        Args:
            user_id: Unique identifier for the user
            keys: List of key dictionaries containing key_id, short_path, target_url, and hits
        
        Returns:
            Response from DynamoDB
        
        Raises:
            BotoCoreError, ClientError: If DynamoDB operation fails
        """
        item = {
            'user_id': user_id,
            'keys': keys or []
        }

        try:
            response = self.table.put_item(Item=item)
            return response
        except (BotoCoreError, ClientError) as e:
            print(f"Error creating user in DynamoDB: {e}")
            raise

    def get(self, user_id: str):
        """
        Retrieve a user item from DynamoDB.

        Args:
            user_id: Unique identifier for the user
        
        Returns:
            Dict containing user data if found, None otherwise
        
        Raises:
            BotoCoreError, ClientError: If DynamoDB operation fails
        """
        try:
            response = self.table.get_item(
                Key={
                    'user_id': user_id
                }
            )
            return response.get('Item')
        except (BotoCoreError, ClientError) as e:
            print(f"Error retrieving user from DynamoDB: {e}")
            raise

    def update(self, user_id: str, user_data: dict):
        """
        Update a user's keys list by adding a new key.
        
        Returns:
            Updated user data if successful
        
        Raises:
            BotoCoreError, ClientError: If DynamoDB operation fails
        """
        try:
            response = self.table.update_item(
                Key={
                    'user_id': user_id,
                },
                UpdateExpression="SET #keys = list_append(if_not_exists(#keys, :empty_list), :new_key)",
                ExpressionAttributeNames={
                    '#keys': 'keys'
                },
                ExpressionAttributeValues={
                    ':new_key': [user_data],
                    ':empty_list': []
                },
                ReturnValues='ALL_NEW'
            )
            return response.get('Attributes')
        except (BotoCoreError, ClientError) as e:
            print(f"Error updating user in DynamoDB: {e}")
            raise


class DecimalEncoder(json.JSONEncoder):
    """Help class to serialize Decimal objects to JSON."""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return str(obj)  # or float(obj)
        return super().default(obj)
