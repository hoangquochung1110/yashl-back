import json
import boto3
from boto3.dynamodb.conditions import Key


def lambda_handler(event, context):
    """Lambda to handle list key request."""
    user_id = event['user_id']
    keys = list_keys_by_user_id(user_id)
    return {
        'statusCode': 200,
        'body': json.dumps(keys)
    }


def list_keys_by_user_id(user_id):
    dynamodb = boto3.resource('dynamodb')
    table_name = 'yashl'
    table = dynamodb.Table(table_name)

    response = table.table.query(
        IndexName='user_id-index',
        KeyConditionExpression=Key("user_id").eq(user_id)
    )
    return response['Items']
