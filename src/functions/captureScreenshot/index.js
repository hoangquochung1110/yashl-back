import { PutObjectCommand, S3Client } from "@aws-sdk/client-s3";
// import BrowserAutomation from '../../layers/browser-automation/nodejs/lib/browser-automation.js';
import BrowserAutomation from '/opt/nodejs/lib/browser-automation.js';
import fsPromises from "fs/promises";


// Environment configuration
const ENV_CONFIG = {
  debug: process.env.DEBUG === "true",
  isLocal: process.env.AWS_EXECUTION_ENV === undefined,
  browser: {
    executablePath: process.env.CHROMIUM_EXECUTABLE_PATH,
    headless: false,
  },
  s3: {
    region: process.env.S3_REGION,
    bucket: process.env.S3_BUCKET,
    outputType: "png",
  },
  aws: {
    region: process.env.S3_REGION,
    credentials: {
      accessKeyId: process.env.AWS_ACCESS_KEY_ID,
      secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY,
      sessionToken: process.env.AWS_SESSION_TOKEN,
    }
  }
};


async function handleEventBody(event) {
  if (typeof event.body === 'string') {
    try {
      return JSON.parse(event.body);
    } catch (error) {
      throw new Error('Invalid JSON string');
    }
  } else if (typeof event.body === 'object') {
    return event.body;
  } else {
    throw new Error('Unsupported body type');
  }
}


export const handler = async (event) => {
  const body = await handleEventBody(event)

  const key = body.key;
  const url = body.destinationUrl;

  console.log('Initializing browser automation');
  const automation = new BrowserAutomation({
    isLocal: ENV_CONFIG.isLocal,
    browser: ENV_CONFIG.browser,
  });
  await automation.initialize({
    viewport: { width: 1200, height: 800},
    mobile: true,
  });
  let screenshot;
  console.log('Navigating to URL');
  await automation.navigateAndWait(url, {
    authStrategy: 'dismiss',
  });
  screenshot = await automation.takeScreenshot();

  if (ENV_CONFIG.debug) {
    console.log("writing file locally...");
    await fsPromises.writeFile(
      `./${key}.${ENV_CONFIG.s3.outputType}`,
      screenshot
    );
    return {
      statusCode: 200,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: "Success",
        data: { url: `local://screenshots/${key}.${ENV_CONFIG.s3.outputType}` }
      }),
    };
  } 
    const putResponse = await putToS3(
      key,
      screenshot,
      {
        'destination-url': url,
        'key': key,
        'title': body.title || '',
      }
    );
    return {
      statusCode: putResponse.$metadata.httpStatusCode,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: 'Success',
        data: {
          url: `https://${ENV_CONFIG.s3.bucket}.s3.${ENV_CONFIG.aws.region}.amazonaws.com/${key}.${ENV_CONFIG.s3.outputType}`
        } 
      }),
    };
};


const putToS3 = async (key, data, metadata={}) => {
  console.log("Uploading to S3...");
  const s3Client = new S3Client(ENV_CONFIG.aws);
  const command = new PutObjectCommand({
    Bucket: ENV_CONFIG.s3.bucket,
    Key: `${key}.${ENV_CONFIG.s3.outputType}`,
    Body: data,
    Metadata: metadata,
  });
  return await s3Client.send(command);
}
