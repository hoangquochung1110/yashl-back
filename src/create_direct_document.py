import json
import os

import boto3

s3_client = boto3.client('s3')
redirect_bucket = os.environ['REDIRECT_BUCKET']


def lambda_handler(event, context):
    # Extracting details from the S3 event
    preview_bucket_name = event['Records'][0]['s3']['bucket']['name']
    object_key = event['Records'][0]['s3']['object']['key'] # with extension

    response = s3_client.head_object(Bucket=preview_bucket_name, Key=object_key)
    metadata = response['Metadata']

    destination_url = metadata.get('destination-url', '')
    title = metadata.get('title', '')
    key = metadata['key']
    screenshot_preview_url = f"https://{preview_bucket_name}.s3.ap-southeast-1.amazonaws.com/{object_key}"
    # Generate HTML content
    html_content = _create_redirect_document(
        title,
        screenshot_preview_url,
        destination_url
    )

    # Define the output bucket and file name
    output_key = f"{key}.html"  # Change extension

    # Upload HTML content to S3
    s3_client.put_object(
        Bucket=redirect_bucket,
        Key=output_key,
        Body=html_content,
        ContentType='text/html'
    )

    return {
        'statusCode': 200,
        'body': json.dumps(
            {
                'message': 'HTML redirect page created successfully!',
                'url': f'https://{redirect_bucket}.s3.amazonaws.com/{output_key}'}
            )
    }


def _create_redirect_document(title, screenshot_preview_url, destination_url):
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    
    <!-- Open Graph Meta Tags -->
    <meta property="og:title" content="{title}">
    <meta property="og:description" content="">
    <meta property="og:image" content="{screenshot_preview_url}">
    <meta property="og:url" content="{screenshot_preview_url}">
    <meta property="og:site_name" content="yashl">

    <!-- Custom JavaScript -->
    <script>
        window.onload = function() {{
            console.log("Page has loaded. Redirecting...");
            // Redirect to a new URL
            window.location.href = "{destination_url}";
        }};
    </script>
</head>
<body>
</body>
</html>"""

    return html_content
