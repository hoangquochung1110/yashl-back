resource "aws_lambda_function" "generate_key" {
  function_name    = "generate_key"
  role             = "arn:aws:iam::838835070561:role/url-shortener-lambda"
  handler          = "generate_key.lambda_handler" # Adjust based on your function's entry point
  runtime          = "python3.10"
  filename         = data.archive_file.generate_key_zip.output_path
  source_code_hash = data.archive_file.generate_key_zip.output_base64sha256
  publish          = true # This will publish a new version when the function changes

  environment {
    # Add any environment variables here if needed
  }
}

resource "aws_lambda_function" "resolve_key" {
  function_name    = "resolve_key"
  role             = "arn:aws:iam::838835070561:role/url-shortener-lambda"
  handler          = "resolve_key.lambda_handler" # Adjust based on your function's entry point
  runtime          = "python3.10"
  filename         = data.archive_file.resolve_key_zip.output_path
  source_code_hash = data.archive_file.resolve_key_zip.output_base64sha256

  environment {
    # Add any environment variables here if needed
  }
}

data "archive_file" "generate_key_zip" {
  type        = "zip"
  source_file = "${path.root}/../src/generate_key.py" # Adjust this path if needed
  output_path = "${path.module}/generate_key_function.zip"
}

data "archive_file" "resolve_key_zip" {
  type        = "zip"
  source_file = "${path.root}/../src/resolve_key.py" # Adjust this path if needed
  output_path = "${path.module}/resolve_key_function.zip"
}
