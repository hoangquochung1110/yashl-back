import os
from urllib.parse import unquote, urlparse

import boto3

s3_client = boto3.client('s3')
redirect_bucket = os.environ.get('S3_REDIRECT_BUCKET')

def lambda_handler(event, context):
    """
    Handle both S3 events and API Gateway requests to create HTML redirect pages
    """
    page_data = {
            'key': event['key'],
            'target_url': event['target_url'],
            'title': event.get('title', ''),
            'description': event.get('description', ''),
            'preview_url': event.get('preview_url', ''),
        }
    return create_redirect_page(page_data)


def create_redirect_page(page_data):
    """
    Create HTML redirect page with normalized data
    """
    # Get or generate title
    title = page_data['title'] or guess_title(page_data['target_url'])

    # Generate HTML content
    html_content = _create_redirect_document(
        target_url=page_data['target_url'],
        title=title,
        preview_url=page_data['preview_url'],
        description=page_data['description'],
    )

    # Upload HTML content to S3
    resp = s3_client.put_object(
        Bucket=redirect_bucket,
        Key=page_data['key'],
        Body=html_content,
        ContentType='text/html',
    )
    return resp

def _create_redirect_document(target_url, title, preview_url, description=''):
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
    <meta property="og:url" content="{target_url}">
    <meta property="og:site_name" content="{target_url}">

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
            window.location.href = "{target_url}";
        }};
    </script>
</head>
<body>
    <!-- Optional: Add fallback content for users with JavaScript disabled -->
    <noscript>
        <p>If you are not redirected automatically, please <a href="{target_url}">click here</a>.</p>
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
