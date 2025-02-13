import json
import math
import os
import secrets
import string
from dataclasses import asdict, dataclass
from decimal import Decimal
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError

BASE = 62

UPPERCASE_OFFSET = 55
LOWERCASE_OFFSET = 61
DIGIT_OFFSET = 48

DOMAIN = os.environ["DOMAIN"]
s3_client = boto3.client('s3')
redirect_bucket = os.environ.get('S3_REDIRECT_BUCKET')

class UrlShortener:

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
        self.dynamodb = boto3.resource(
            'dynamodb',
            region_name=self.region,
        )
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


shortener = UrlShortener()

@dataclass
class RequestData:
    user_id: str = "<anonymous>"
    title: str = ""
    description: str = ""
    target_url: str = ""
    segments: list = ()


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
        case "POST":
            return generate_key(body=event['body'])
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

def generate_key(body, *args, **kwargs):
    body = json.loads(body)

    short_path = shortener.generate_short_path()
    key_id = saturate(short_path)
    url = body['target_url']
    title = body.get('title', '')
    segments = body.get('segments', [])
    request_data = RequestData(**body)
    request_data_dict = asdict(request_data)
    key_data = dict(
        **request_data_dict,
        key_id=key_id,
        short_path=short_path,
        hits=0,
    )

    shortener.create(**key_data)

    # Create html document
    keys = segments + [short_path]
    key = "/".join(keys)

    preview_url = (
        f"https://{os.environ['S3_PREVIEW_BUCKET']}.s3.{os.environ['S3_REGION']}"
        f".amazonaws.com/{short_path}.png"
    )
    data = {
        'key': key,
        'target_url': url,
        'title': title,
        'description': '',
        'preview_url': preview_url,        
    }
    create_redirect_page(**data)
    key_data['short_url'] = f"https://{DOMAIN}/{key}"
    return create_response(200, key_data)

def create_redirect_page(
    key,
    target_url,
    title,
    preview_url,
    description=''
) -> str:

    """Create HTML redirect page with normalized data."""
    html_content = TEMPLATE.format(
        target_url=target_url,
        title=title,
        preview_url=preview_url,
        description=description
    )

    # Upload HTML content to S3
    res = s3_client.put_object(
        Bucket=redirect_bucket,
        Key=key,
        Body=html_content,
        ContentType='text/html',
    )
    return res


def resolve_key(path_params, *args, **kwargs):
    short_path = path_params['short_path']
    key = saturate(short_path)
    item = shortener.update(
        key={
            'key_id': key,
        }
    )
    if item:
        return create_response(200, item, encoder_cls=DecimalEncoder)
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

    items = shortener.query(
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


class DecimalEncoder(json.JSONEncoder):
    """Help class to serialize Decimal objects to JSON."""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return str(obj)  # or float(obj)
        return super().default(obj)

TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>

    <!-- Basic Meta Tags -->
    <meta name="description" content="{description}">
    <meta name="keywords" content="">

    <!-- Open Graph Meta Tags -->
    <meta property="og:title" content="{title}">
    <meta property="og:description" content="{description}">
    <meta property="og:image" content="{preview_url}">
    <meta property="og:url" content="{target_url}">
    <meta property="og:site_name" content="{target_url}">

    <!-- Twitter Card Meta Tags -->
    <meta name="twitter:card" content="">
    <meta name="twitter:title" content="{title}">
    <meta name="twitter:description" content="{description}">
    <meta name="twitter:image" content="{preview_url}">
    <meta name="twitter:image:alt" content="">

    <!-- Apple Mobile Web App Meta Tags -->
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black">
    <meta name="apple-mobile-web-app-title" content="{title}">

    <!-- Custom JavaScript -->
    <script>
        window.onload = function() {{
            console.log("Page has loaded. Redirecting...");
            // Redirect to a new URL
            window.location.href = "{target_url}";
        }};
    </script>
</head>
<body>
    <!-- Optional: Add fallback content for users with JavaScript disabled -->
    <noscript>
        <p>If you are not redirected automatically, please <a href="{target_url}">click here</a>.</p>
    </noscript>
</body>
</html>
"""