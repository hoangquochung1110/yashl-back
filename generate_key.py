import secrets
import string
import math
import sys
import boto3

BASE = 62

UPPERCASE_OFFSET = 55
LOWERCASE_OFFSET = 61
DIGIT_OFFSET = 48


# from .base_62_converter import dehydrate, saturate

CHARACTERS = string.ascii_letters + string.digits


def generate_key():
    key = ''.join((secrets.choice(CHARACTERS) for _ in range(6)))
    return key

#
# Converts any integer into a base [BASE] number. I have chosen 62
# as it is meant to represent the integers using all the alphanumeric
# characters, [no special characters] = {0..9}, {A..Z}, {a..z}
#
# I plan on using this to shorten the representation of possibly long ids,
# a la url shortenters
#
# saturate()  takes the base 62 key, as a string, and turns it back into an integer
# dehydrate() takes an integer and turns it into the base 62 string
#

BASE = 62

UPPERCASE_OFFSET = 55
LOWERCASE_OFFSET = 61
DIGIT_OFFSET = 48

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


def saturate(key):
    """
    Turn the base [BASE] number [key] into an integer
    """
    int_sum = 0
    reversed_key = key[::-1]
    for idx, char in enumerate(reversed_key):
        int_sum += true_ord(char) * int(math.pow(BASE, idx))
    return int_sum


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


if __name__ == '__main__':
    shortened_path = generate_key()
    print(f"{shortened_path=}")
    key_id = saturate(shortened_path)
    print(f"{key_id=}")
    print(dehydrate(key_id))


def lambda_handler(event, context):
    """
    Accept request with path parameter as url shortened path
    retrieve the url from the path parameter from the table above
    then redirect users to destination url
    """
    shortened_path = event['pathParameters']['shortened_path']
    print(f"{shortened_path=}")
    key_id = saturate(shortened_path)
    print(f"{key_id=}")
    dynamodb = boto3.resource('dynamodb').Table('url_shortener')
    response = dynamodb.get_item(Key={'key_id': key_id})
    print(f"{response=}")
    if 'Item' in response and 'destination_url' in response['Item']:
        destination_url = response['Item']['destination_url']
        print(f"{destination_url=}")
        return {    
            'statusCode': 301,
            'headers': {
                'Location': destination_url
            }
        }
    else:
        return {
            'statusCode': 404,
            'body': 'Not Found'
        }
