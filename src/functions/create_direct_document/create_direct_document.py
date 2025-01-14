import json
import os
from urllib.parse import unquote, urlparse

import boto3

s3_client = boto3.client('s3')
redirect_bucket = os.environ.get('REDIRECT_BUCKET', '')

def lambda_handler(event, context):
    """
    Handle both S3 events and API Gateway requests to create HTML redirect pages
    """
    try:
        # Parse event and get normalized data
        page_data = parse_event(event)
        return create_redirect_page(page_data)
    except ValueError as e:
        return {
            'statusCode': 400,
            'body': json.dumps({'message': str(e)})
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'message': f'Internal error: {str(e)}'})
        }

def parse_event(event):
    """
    Parse different event types and return normalized data
    Returns: {
        'key': str,
        'title': str,
        'destination_url': str,
        'image_url': str
    }
    """
    # S3 Event
    if 'Records' in event and event['Records'][0].get('eventSource') == 'aws:s3':
        trigger_bucket_name = event['Records'][0]['s3']['bucket']['name']
        object_key = event['Records'][0]['s3']['object']['key']
        
        # Get metadata from S3 object
        response = s3_client.head_object(Bucket=trigger_bucket_name, Key=object_key)
        metadata = response['Metadata']
        
        if 'destination-url' not in metadata:
            raise ValueError("Missing destination-url in S3 object metadata")
            
        return {
            'key': metadata['key'],
            'title': metadata.get('title', ''),
            'destination_url': metadata['destination-url'],
            'image_url': f"https://{trigger_bucket_name}.s3.ap-southeast-1.amazonaws.com/{object_key}"
        }
    
    # API Gateway Event
    else:
        try:
            body = json.loads(event.get('body', '{}'))
        except json.JSONDecodeError:
            raise ValueError('Invalid JSON in request body')
            
        # Validate required fields
        required_fields = ['key', 'destination_url', 'image_url']
        missing_fields = [field for field in required_fields if field not in body]
        if missing_fields:
            raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")
            
        return {
            'key': body['key'],
            'title': body.get('title', ''),
            'destination_url': body['destination_url'],
            'image_url': body['image_url']
        }

def create_redirect_page(page_data):
    """
    Create HTML redirect page with normalized data
    """
    try:
        # Get or generate title
        title = page_data['title'] or guess_title(page_data['destination_url'])

        # Generate HTML content
        html_content = _create_redirect_document(
            title=title,
            destination_url=page_data['destination_url'],
            image_url=page_data['image_url'],
        )

        # Upload HTML content to S3
        output_key = f"{page_data['key']}.html"
        s3_client.put_object(
            Bucket=redirect_bucket,
            Key=output_key,
            Body=html_content,
            ContentType='text/html',
        )

        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'HTML redirect page created successfully!',
                'url': f'https://s3.ap-southeast-1.amazonaws.com/{redirect_bucket}/{output_key}'
            })
        }

    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': f'Error creating redirect page: {str(e)}'
            })
        }

def _create_redirect_document(title, destination_url, image_url, description=''):
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
    <meta property="og:image" content="{image_url}">
    <meta property="og:url" content="{destination_url}">
    <meta property="og:site_name" content="{destination_url}">

    <!-- Twitter Card Meta Tags -->
    <meta name="twitter:card" content="">
    <meta name="twitter:title" content="{title}">
    <meta name="twitter:description" content="{description}">
    <meta name="twitter:image" content="{image_url}">
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
