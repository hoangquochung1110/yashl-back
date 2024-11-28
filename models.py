import boto3
from boto3.dynamodb.conditions import Key
from decouple import config
from botocore.exceptions import ClientError

ROLE_ARN = config('ROLE_ARN')

def assume_role(role_arn, session_name):
    sts = boto3.client('sts')
    response = sts.assume_role(
        RoleArn=role_arn,
        RoleSessionName=session_name
    )
    return response['Credentials']


class YashlTable:
    """Encapsulates an Amazon DynamoDB table of Yashl."""
    def __init__(self, dyn_resource):
        """
        :param dyn_resource: A Boto3 DynamoDB resource.
        """
        self.dyn_resource = dyn_resource
        # The table variable is set during the scenario in the call to
        # 'exists' if the table exists. Otherwise, it is set by 'create_table'.
        self.table = self.dyn_resource.Table('yashl')

    def scan_user_id(self, user_id):
        """Scan rows with a given user_id."""
        try:
            response = self.table.query(
                IndexName='user_id-index',
                KeyConditionExpression=Key("user_id").eq(user_id)
            )
            items = response.get('Items', [])
            # Print out the results
            if items:
                print(f"Items with user_id '{user_id}':")
                for item in items:
                    print(item)
            else:
                print(f"No items found with user_id '{user_id}'.")
            return items

        except ClientError as e:
            print(f"Error scanning DynamoDB table: {e.response['Error']['Message']}")


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
    dynamodb = boto3.resource('dynamodb', aws_access_key_id=credentials['AccessKeyId'],
                              aws_secret_access_key=credentials['SecretAccessKey'],
                              aws_session_token=credentials['SessionToken'])
    yashl_table = YashlTable(dyn_resource=dynamodb)
    response = yashl_table.scan_user_id('dwdwww')


if __name__ == '__main__':
    main(ROLE_ARN, "session_1", "yashl")

