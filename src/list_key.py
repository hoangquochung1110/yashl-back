from decimal import Decimal
import json
import boto3
from boto3.dynamodb.conditions import Key


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return str(obj)  # or float(obj)
        return super().default(obj)


def lambda_handler(event, context):
    """Lambda to handle list key request."""
    query_params = event['queryStringParameters']
    user_id = query_params['user_id']
    keys = list_keys_by_user_id(user_id)
    return {
        'statusCode': 200,
        'body': json.dumps(keys, cls=DecimalEncoder)
    }


def list_keys_by_user_id(user_id):
    dynamodb = boto3.resource('dynamodb')
    table_name = 'yashl'
    table = dynamodb.Table(table_name)

    response = table.query(
        IndexName='user_id-index',
        KeyConditionExpression=Key("user_id").eq(user_id)
    )
    return response['Items']
