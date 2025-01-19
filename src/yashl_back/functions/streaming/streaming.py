import json
import os
from typing import Any

import boto3


s3_client = boto3.client(
    's3',
)
s3_bucket = os.environ['S3_PREVIEW_BUCKET']


def create_response(
    status_code: int,
    body: dict[str, Any],
    encoder_cls=None,
) -> dict[str, Any]:
    """Create a standardized API Gateway response."""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Allow-Methods': 'OPTIONS,POST,GET',
        },
        'body': json.dumps(body, cls=encoder_cls)
    }

def create_html_page(filename, url):
    mime_type = "video/mp4"

    html_content = template.format(
        FILENAME=filename,
        VIDEO_SRC=url,
        MIME_TYPE=mime_type,
    )

    # Upload HTML content to S3
    s3_client.put_object(
        Bucket=s3_bucket,
        Key=filename,
        Body=html_content,
        ContentType='text/html',
    )
    return create_response(
        200,
        {'url': f"https://{s3_bucket}.s3.{os.environ['S3_REGION']}.amazonaws.com/{filename}"}
    )

def lambda_handler(event, context):
    # Parse the incoming request body
    body = json.loads(event['body']) if isinstance(event.get('body'), str) else event.get('body', {})
        
    # Extract video information
    filename = body.get('filename')
    url = body.get('url')

    if not all([filename, url]):
        return create_response(
            400,
            {'error': 'Missing required parameters'},
        )

    # Generate HTML with embedded video
    return create_html_page(filename, url)

template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Video Stream - {FILENAME}</title>
</head>
<body style="font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; background-color: #f8f9fa;">
    <div style="background-color: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
        <h1 style="color: #333; margin-bottom: 20px;">{FILENAME}</h1>
        <div style="position: relative; width: 100%; padding-top: 56.25%; margin-bottom: 20px;">
            <video controls playsinline style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; border-radius: 4px;">
                <source src='{VIDEO_SRC}' type='{MIME_TYPE}'>
                Your browser does not support the video tag.
            </video>
        </div>
        <div style="padding: 15px; background-color: #f8f9fa; border-radius: 4px; margin-top: 20px;">
            <p><strong>Filename:</strong> {FILENAME}</p>
            <p><strong>Type:</strong> {MIME_TYPE}</p>
        </div>
    </div>
</body>
</html>
"""