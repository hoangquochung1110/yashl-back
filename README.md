### Project to experiment how to deploy AWS Lambda via different methods

- AWS CLI + GH Actions
- Terraform


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
