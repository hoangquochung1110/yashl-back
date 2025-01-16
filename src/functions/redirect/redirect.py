import base64
import mimetypes
import os

from dataclasses import dataclass
from urllib.parse import unquote, urlparse

import boto3

redirect_bucket = os.environ.get('S3_REDIRECT_BUCKET')
s3_client = boto3.client('s3')


@dataclass
class Asset:
    binary: bytes
    extension: str


@dataclass
class Document:
    """Metadata on HTML document."""
    key: str
    asset: Asset = None
    title: str = ""
    description: str = ""
    redirect_url: str = ""
    preview_url: str = ""


def lambda_handler(event, context):
    """
    Handle both S3 events and API Gateway requests to create HTML redirect pages
    """
    page_data = Document(**event)
    return create_redirect_page(page_data)


def create_redirect_page(document: Document):
    """
    Create HTML redirect page with normalized data
    """
    # Get or generate title
    title = document.title or guess_title(document.redirect_url)

    if document.redirect_url:
        html_content = _create_redirect_document(
            target_url=document.redirect_url,
            title=title,
            preview_url=document.preview_url,
            description=document.description,
        )
    else:
        asset = document.asset
        if not asset.binary:
            raise ValueError("Asset data is empty")
        key = document.key
        content_type = get_video_content_type(asset.extension)

        try:
            decoded_data = base64.b64decode(asset.binary)
            if len(decoded_data) == 0:
                raise ValueError("Decoded data is empty")
        except Exception as decode_error:
            print(f"Base64 decoding failed: {decode_error}")
            raise
        target_url = (
            f"https://{os.environ['S3_PREVIEW_BUCKET']}.s3.{os.environ['S3_REGION']}"
            f".amazonaws.com/{key}"
        )
        # Upload to S3 only if we have valid data
        s3_client.put_object(
            Bucket=os.environ['S3_PREVIEW_BUCKET'],
            Key=key,
            Body=decoded_data,
            ContentType=content_type,
        )

        html_content = _create_streaming_document(
            target_url=target_url,
            title=document.title,
        )

    # Upload HTML content to S3
    resp = s3_client.put_object(
        Bucket=redirect_bucket,
        Key=document.key,
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
    <meta property="og:type" content="website" />
    <meta property="og:title" content="{title}">
    <meta property="og:description" content="{description}">
    <meta property="og:url" content="{target_url}">
    <meta property="og:image" content="{preview_url}">

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

def _create_streaming_document(target_url, title, content_type="video/mp4", preview_url='', description=''):
    css_styles = '''
        body {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            margin: 0;
            background-color: #f0f0f0;
            font-family: Arial, sans-serif;
        }
        .video-container {
            max-width: 800px;
            width: 95%;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            border-radius: 8px;
            overflow: hidden;
        }
        video {
            width: 100%;
            display: block;
        }
    '''

    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        {css_styles}
    </style>
</head>
<body>
    <div class="video-container">
        <video controls>
            <source id="videoSource" src="{target_url}" type="{content_type}">
            Your browser does not support the video tag.
        </video>
    </div>
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


def get_video_content_type(filename):
    mime_type, _ = mimetypes.guess_type(filename)
    if mime_type and mime_type.startswith('video/'):
        return mime_type
    # Fallback mappings
    extensions = {
        '.mov': 'video/quicktime',
        '.mp4': 'video/mp4',
        '.webm': 'video/webm',
        '.avi': 'video/x-msvideo',
    }
    ext = os.path.splitext(filename.lower())[1]
    return extensions.get(ext, 'video/mp4')
