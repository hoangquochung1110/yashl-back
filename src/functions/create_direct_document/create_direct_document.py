import json
import os
from urllib.parse import unquote, urlparse

import boto3

s3_client = boto3.client('s3')
redirect_bucket = os.environ.get('REDIRECT_BUCKET', '')


def lambda_handler(event, context):
    """
    Create HTML redirect page if new object is uploaded to trigger bucket
    """

    # Extracting trigger bucket name and object key from the S3 event
    trigger_bucket_name = event['Records'][0]['s3']['bucket']['name']
    object_key = event['Records'][0]['s3']['object']['key'] # with extension

    # Retrieve metadata for HTML redirect page
    response = s3_client.head_object(Bucket=trigger_bucket_name, Key=object_key)
    metadata = response['Metadata']

    preview_url = f"https://{trigger_bucket_name}.s3.ap-southeast-1.amazonaws.com/{object_key}"

    # Generate HTML content
    html_content = create_redirect_document(metadata, preview_url)

    # Define the output bucket and file name
    key = metadata['key']
    output_key = f"{key}.html"  # Change extension

    # Upload HTML content to S3
    s3_client.put_object(
        Bucket=redirect_bucket,
        Key=output_key,
        Body=html_content,
        ContentType='text/html',
    )

    return {
        'statusCode': 200,
        'body': json.dumps(
            {
                'message': 'HTML redirect page created successfully!',
                'url': f'https://s3.ap-southeast-1.amazonaws.com/{redirect_bucket}/{output_key}'
            }
        )
    }


def create_redirect_document(preview_metadata, preview_url, *args, **kwargs):
    """
    Retrieve url and title from s3 object metadata.

    Generate title if needed.
    """
    destination_url = preview_metadata['destination-url']
    title = preview_metadata.get('title', '')
    if title == '':
        title = guess_title(destination_url)
    return _create_redirect_document(
        title,
        preview_url,
        destination_url,
    )


def _create_redirect_document(title, preview_url, destination_url, description='', *args, **kwargs):
    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    
    <!-- Basic Meta Tags -->
    <meta name="description" content="{description}">
    <meta name="keywords" content="">
    
    <!-- Open Graph Meta Tags -->
    <meta property="og:title" content="{title}">
    <meta property="og:description" content="{description}">
    <meta property="og:image" content="{preview_url}">
    <meta property="og:url" content="{destination_url}">
    <meta property="og:site_name" content="{destination_url}">

    <!-- Twitter Card Meta Tags -->
    <meta name="twitter:card" content="">
    <meta name="twitter:title" content="{title}">
    <meta name="twitter:description" content="{description}">
    <meta name="twitter:image" content="{preview_url}">
    <meta name="twitter:image:alt" content="">
    
    <!-- Apple Mobile Web App Meta Tags -->
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black">
    <meta name="apple-mobile-web-app-title" content="{title}">

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
    <!-- Optional: Add fallback content for users with JavaScript disabled -->
    <noscript>
        <p>If you are not redirected automatically, please <a href="{destination_url}">click here</a>.</p>
    </noscript>
</body>
</html>
"""

    return html_content


def de_slugify(slug):
    # Split by hyphens and remove any empty strings
    words = [word for word in slug.split('-') if word]
    
    # Remove any leading/trailing numbers and convert to title case
    result = ' '.join(word for word in words if not word.isdigit()).title()
    
    return result


def guess_title(url):
    parsed_url = urlparse(url)
    if parsed_url.netloc == 'trello.com':
        path_segments = parsed_url.path.split('/')
        if path_segments:
            last_segment = path_segments[-1]
            return de_slugify(unquote(last_segment))
    return ''
