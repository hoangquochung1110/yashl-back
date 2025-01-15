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
            if resource_path.endswith('/{short_path}'):
                return resolve_key(path_params=event['pathParameters'])
            else:                
                return list_keys(query_params=event['queryStringParameters'])
        case  "POST":
            body = json.loads(event['body'])
            user_id = body.get('user_id', '')
            url = body['target_url']
            return generate_key(url=url, user_id=user_id)
        case _:
            return create_response(405, {'error': 'Method not allowed'})


def create_response(status_code: int, body: dict[str, Any], encoder_cls=None) -> dict[str, Any]:
    """Create a standardized API Gateway response."""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Allow-Methods': 'OPTIONS,POST,GET',
        },
        'body': json.dumps(body, cls=encoder_cls)
    }

def generate_key(url, user_id=""):
    shortened_path = ShortUrl.generate_short_path()
    key_id = saturate(shortened_path)
    key_data = dict(
        key_id=key_id,
        short_path=shortened_path,
        target_url=url,
        user_id=user_id or "<anonymous>",
        hits=0,
    )
    short_url = ShortUrl()
    short_url.create(**key_data)            
    return create_response(200, key_data)

def resolve_key(path_params):
    short_path = path_params['short_path']
    key = saturate(short_path)
    short_url = ShortUrl()
    item = short_url.update(
        key={
            'key_id': key,
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


def list_keys(
    query_params,
    *args,
    **kwargs
):
    if not query_params:
        return create_response(
            200,
            {'keys': []},
        )

    user_id = query_params.get('user_id')
    short_url = ShortUrl()

    index_name = ''
    key_conditions = {}

    if user_id:
        index_name = 'user_id-index'
        key_conditions = {
            'user_id': {
                'AttributeValueList': [user_id],
                'ComparisonOperator': 'EQ'
            }
        }

    items = short_url.query(
        index_name=index_name,
        key_conditions=key_conditions,
    )
    return create_response(
        200,
        {'keys': items},
        encoder_cls=DecimalEncoder 
    )


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
        **kwargs,
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
            **kwargs,
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

    def query(self, index_name, key_conditions, **kwargs):
        response = self.table.query(
            IndexName=index_name,
            KeyConditions=key_conditions,
        )
        return response['Items']


class DecimalEncoder(json.JSONEncoder):
    """Help class to serialize Decimal objects to JSON."""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return str(obj)  # or float(obj)
        return super().default(obj)
