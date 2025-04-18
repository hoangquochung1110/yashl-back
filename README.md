### About
**Y**et **A**nother **Sh**ort UR**L** Service

Stack:
- Node.js + Python
- AWS Lambda Function
- AWS API Gateway
- AWS DynamoDB


### How to deploy Nodejs
1. Navigate to the target directory
```
cd .src/captureScreenshot
```

2. Install Dependencies
```
npm install
```

3. Create deployment package
```
zip -r captureScreenshot.zip index.js node_modules package.json
```

4. Deploy it to AWS Lambda
```
aws lambda update-function-code --function-name captureScreenshot --zip-file fileb://captureScreenshot.zip
```


### How to deploy Layer
1. First, create a zip file of your layer (run this from /Users/hunghoang/Development/yashl-back/src/layers):
```
cd browser-automation
zip -r ../browser-automation-layer.zip nodejs/
```

2. Publish the layer using AWS CLI:
```
aws lambda publish-layer-version \
    --layer-name browser-automation \
    --description "Browser automation utilities" \
    --zip-file fileb://../browser-automation-layer.zip \
    --compatible-runtimes nodejs18.x \
    --compatible-architectures x86_64 arm64
```

3. The command above will return a response with the layer ARN. Save the ARN from the response, it will look something like:
```
arn:aws:lambda:<region>:<account-id>:layer:browser-automation:1
```

4. Attach the layer to your trelloScreenshot function:
```
aws lambda update-function-configuration \
    --function-name trelloScreenshot \
    --layers arn:aws:lambda:<region>:<account-id>:layer:browser-automation:1
```

# Lambda Function Usage Notice

## Important: Use Lambda Aliases

The base Lambda function `arn:aws:lambda:ap-southeast-1:838835070561:function:key` should not be invoked directly.

Instead, please use the appropriate aliases:
- Development: `arn:aws:lambda:ap-southeast-1:838835070561:function:key:dev`
- Production: `arn:aws:lambda:ap-southeast-1:838835070561:function:key:prod`

## Benefits of Using Aliases
- Proper version control
- Staged deployments
- Environment-specific configurations
- Improved security
- Better monitoring and metrics separation

## Resource Policy
The base Lambda function has permissions configured to work with API Gateway, but direct invocation should be done through the aliases to ensure proper environment separation.
