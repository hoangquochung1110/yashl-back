import boto3
import math

BASE = 62

UPPERCASE_OFFSET = 55
LOWERCASE_OFFSET = 61
DIGIT_OFFSET = 48


def lambda_handler(event, context):
    """
    Accept request with path parameter as url shortened path
    retrieve the url from the path parameter from the table above
    then redirect users to destination url
    """
    pathParameters = event['pathParameters']
    shorten_path = pathParameters['shorten_path']

    key_id = saturate(shorten_path)

    destination_url = resolve_url('yashl', key_id)

    return {    
            'statusCode': 301,
            'headers': {
                'Location': destination_url,
            }
        }

def resolve_url(table_name, key_id):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(table_name)
    response = table.get_item(
        Key={
            'key_id': key_id
        }
    )
    item = response.get('Item', {})
    if item:
        table.update_item(
            Key={
                'key_id': key_id,
            },
            UpdateExpression="SET click_count = click_count + :inc",
            ExpressionAttributeValues={
                ':inc': 1
            }
        )
    return item.get('destination_url')


def saturate(key):
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
