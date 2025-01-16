import os
import base64
from .redirect import lambda_handler


if __name__ == "__main__":
    import pathlib

    obj_name = 'filename.ext'
    script_dir = os.path.dirname(os.path.abspath(__file__))
    video_path = os.path.join(script_dir, obj_name)

    # Read and encode with verification
    with open(video_path, 'rb') as f:
        video_data = f.read()
        print(f"Original video size: {len(video_data)} bytes")
        video_base64 = base64.b64encode(video_data).decode('utf-8')
        print(f"Base64 encoded length: {len(video_base64)}")

        # Verify we can decode it back
        test_decode = base64.b64decode(video_base64)
        print(f"Test decode size: {len(test_decode)} bytes")
        
        # Verify the decoded data matches original
        print(f"Decoded data matches original: {len(test_decode) == len(video_data)}")

        event = {
            'key': f"ALN-351/{pathlib.Path(video_path).stem}",
            'target_url': "",
            'title': 'Video to reproduce an issue',
            'description': '',
            'preview_url': '',
            'asset': {
                'binary': video_base64,
                'extension': pathlib.Path(video_path).suffix,
            }
        }
        print(event['key'])

    # Verify event data
    print(f"Asset field in event: {len(event['asset'])} bytes")
    lambda_handler(event, None)
