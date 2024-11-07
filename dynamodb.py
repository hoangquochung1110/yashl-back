from contextlib import contextmanager

import boto3
from decouple import config

ROLE_ARN = config('ROLE_ARN')


@contextmanager
def assume_role(role_arn, session_name):
    sts = boto3.client('sts')
    response = sts.assume_role(
        RoleArn=role_arn,
        RoleSessionName=session_name
    )
    try:
        yield response['Credentials']
    finally:
        sts_assumed_role = boto3.client('sts',
                                        aws_access_key_id=response['Credentials']['AccessKeyId'],
                                        aws_secret_access_key=response['Credentials']['SecretAccessKey'],
                                        aws_session_token=response['Credentials']['SessionToken'])
        sts_assumed_role.revoke_role_session(RoleSessionName=session_name)


def list_items_from_dynamodb(table_name, credentials):
    dynamodb = boto3.resource('dynamodb', aws_access_key_id=credentials['AccessKeyId'],
                              aws_secret_access_key=credentials['SecretAccessKey'],
                              aws_session_token=credentials['SessionToken'])
    table = dynamodb.Table(table_name)
    response = table.scan()
    return response['Items']


def create_item_in_dynamodb(table_name, credentials, key_id, shorten_path, destination_url, click_count=0):
    dynamodb = boto3.resource('dynamodb', aws_access_key_id=credentials['AccessKeyId'],
                              aws_secret_access_key=credentials['SecretAccessKey'],
                              aws_session_token=credentials['SessionToken'])
    table = dynamodb.Table(table_name)
    table.put_item(
        Item={
            'key_id': key_id,
            'shorten_path': shorten_path,
            'destination_url': destination_url,
            'click_count': click_count
        }
    )


def get_item(table_name, credentials, key_id):
    dynamodb = boto3.resource('dynamodb', aws_access_key_id=credentials['AccessKeyId'],
                              aws_secret_access_key=credentials['SecretAccessKey'],
                              aws_session_token=credentials['SessionToken'])
    table = dynamodb.Table(table_name)
    response = table.get_item(
        Key={
            'key_id': key_id
        }
    )
    return response.get('Item')


if __name__ == '__main__':
    with assume_role(ROLE_ARN, "session_1") as credentials:
        print(list_items_from_dynamodb(table_name="yashl", credentials=credentials))
