import json
import math
import secrets
import string

import boto3

CHARACTERS = string.ascii_letters + string.digits
BASE = 62

UPPERCASE_OFFSET = 55
LOWERCASE_OFFSET = 61
DIGIT_OFFSET = 48


def lambda_handler(event, context):
    """Generate a shorten path for a destination URL."""
    destination_url = event.get('destination_url', '')
    user_id = event.get('user_id', '')
    shorten_path = generate_shorten_path()

    if destination_url:
        key_id = saturate(shorten_path)
        create_entry(
            table_name="yashl",
            key_id=key_id,
            user_id=user_id,
            shorten_path=shorten_path,
            destination_url=destination_url,
        )
    return {
        'statusCode': 200,
        'body': json.dumps({'key': shorten_path}),
    }


def generate_shorten_path():
    key = ''.join((secrets.choice(CHARACTERS) for _ in range(6)))
    return key


def create_entry(
    table_name,
    key_id,
    user_id,
    shorten_path,
    destination_url,
    click_count=0,
):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(table_name)
    table.put_item(
        Item={
            'key_id': key_id,
            'shorten_path': shorten_path,
            'destination_url': destination_url,
            'click_count': click_count,
            'user_id': user_id,
        }
    )


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
