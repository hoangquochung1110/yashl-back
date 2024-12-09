import shutil
from screenshotone import Client, TakeOptions


def lambda_handler(event, context):
    """Capture a screenshot."""
    return {
        "statusCode": 200,
    }
