import json
import math
import os
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

    secret_key = os.environ.get('SECRET_KEY')
    if event['HTTPAuthorization'] != secret_key:
        return {
            'statusCode': 401,
        }

    body = json.loads(event['body'])
    destination_url = body['destination_url']
    user_id = body.get('user_id',  '')

    if destination_url:
        shorten_path = generate_shorten_path()
        key_id = saturate(shorten_path)
        attrs_to_create = dict(
            key_id=key_id,
            shorten_path=shorten_path,
            destination_url=destination_url,
        )
        if user_id:
            attrs_to_create.update({'user_id': user_id})
        create_entry(
            table_name="yashl",
            **attrs_to_create,
        )
        return {
            'statusCode': 200,
            'body': json.dumps({'key': shorten_path}),
        }
    return {
        'statusCode': 400,
    }


def generate_shorten_path():
    key = ''.join((secrets.choice(CHARACTERS) for _ in range(6)))
    return key


def create_entry(
    table_name,
    **kwargs,
):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(table_name)
    table.put_item(
        Item={
            'click_count': 0,
            **kwargs,
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
