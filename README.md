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
zip -r deployment-package.zip index.js node_modules package.json
````
