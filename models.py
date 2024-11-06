import boto3
from decouple import config

ROLE_ARN = config('ROLE_ARN')

def assume_role(role_arn, session_name):
    sts = boto3.client('sts')
    response = sts.assume_role(
        RoleArn=role_arn,
        RoleSessionName=session_name
    )
    return response['Credentials']

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



def main(role_arn, session_name, table_name):
    credentials = assume_role(role_arn, session_name)
    print(list_items_from_dynamodb(table_name, credentials))

if __name__ == '__main__':
    main(ROLE_ARN, "session_1", "yashl")

