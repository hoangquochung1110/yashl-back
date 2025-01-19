import { PutObjectCommand, S3Client } from "@aws-sdk/client-s3";
import fsPromises from "fs/promises";
// import BrowserAutomation from '../../layers/browser-automation/nodejs/lib/browser-automation.js';
import BrowserAutomation from '/opt/nodejs/lib/browser-automation.js';  // more verbose


// Environment configuration
const ENV_CONFIG = {
  debug: process.env.DEBUG === "true",
  isLocal: process.env.AWS_EXECUTION_ENV === undefined,
  browser: {
    executablePath: process.env.CHROMIUM_EXECUTABLE_PATH
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

class TrelloBrowserAutomation extends BrowserAutomation {

  async performLogin(credentials) {
    if (!credentials.username || !credentials.password) {
      throw new Error('Credentials required for login strategy');
    }

    try {
      const { username, password, selectors } = credentials;

      await this.page.waitForSelector(selectors.username);
      await this.page.type(selectors.username, username, {delay: 10});
      await this.page.click(selectors.submit);
      await this.page.waitForSelector(selectors.password);
      await this.page.type(selectors.password, password, {delay: 500});

      // Wait for navigation
      try{
        await Promise.all([
          this.page.click(selectors.submit), // Submit form
          this.page.waitForNavigation({ waitUntil: 'networkidle2' }), // Wait for navigation to complete
        ]);
        console.log("Navigation done")
      } catch(err){
        console.log("Navigation timeout: ", err);
      }
    } catch (error) {
      throw new Error(`Login failed: ${error.message}`);
    }
  }
}


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


async function putToS3(key, data, metadata = {}) {
  const s3Client = new S3Client(ENV_CONFIG.aws);
  const command = new PutObjectCommand({
    Bucket: ENV_CONFIG.s3.bucket,
    Key: `${key}.${ENV_CONFIG.s3.outputType}`,
    Body: data,
    Metadata: metadata,
  });
  return await s3Client.send(command);
}


export const handler = async (event) => {
  console.log('Handler started');
  const body = await handleEventBody(event)

  const key = body.key;
  const url = body.destinationUrl;

  console.log('Initializing browser automation');
  const automation = new TrelloBrowserAutomation({
    isLocal: ENV_CONFIG.isLocal,
    browser: ENV_CONFIG.browser,
  });
  await automation.initialize();
  let screenshot;
  try {
    await fsPromises.access('./cookies.json');
    console.log('Navigating to URL');
    await automation.navigateAndWait(url, {
      authStrategy: 'none',
    });
    screenshot = await automation.takeScreenshot();
  } catch(err){
    console.error('Error accessing cookies or during navigation:', err.message);
    const returnPath = url.replace('https://trello.com', ''); // 
    const encodedReturnUrl = encodeURIComponent(returnPath);
    console.log("navigated to ", `https://trello.com/login?returnUrl=${encodedReturnUrl}`)
    const loginUrl = `https://trello.com/login?returnUrl=${encodedReturnUrl}`;
    await automation.navigateAndWait(loginUrl, {
      authStrategy: 'login',
      // should specify credentials
    });
    await Promise.all([
      this.page.waitForNavigation({ waitUntil: 'networkidle2' }),
      this.page.goto(url)
    ]);
    screenshot = await automation.takeScreenshot();
  }

  if (ENV_CONFIG.debug) {
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
  const putResponse = await putToS3(key, screenshot, {
    'destination-url': url,
    'key': key,
    'title': '',
    ...body.metadata
  });

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
}
