import { PutObjectCommand, S3Client } from "@aws-sdk/client-s3";
import chromium from '@sparticuz/chromium-min';
import fsPromises from "fs/promises";
import puppeteer from 'puppeteer-core';

// identify whether we are running locally or in AWS
const isLocal = process.env.AWS_EXECUTION_ENV === undefined;
// should put object to s3 or not
const debug = process.env.DEBUG === "true";
const awsExecutionPath = process.env.CHROMIUM_EXECUTABLE_PATH


const AWS_CONFIG = {
  region: process.env.S3_REGION,
  credentials: {
    accessKeyId: process.env.AWS_ACCESS_KEY_ID,
    secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY,
    sessionToken: process.env.AWS_SESSION_TOKEN,
  }
};

const S3_CONFIG = {
  bucket: process.env.S3_BUCKET,
  type: "png",
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

  const preview = await screenshot(url);
  if (debug){
    console.log("writing file locally...");
    await fsPromises.writeFile(`./screenshots/${key}.${S3_CONFIG.type}`, preview);
    return {
      statusCode: 200,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: "Success", data: { url: `https://mock-bucket.s3.mock-region.amazonaws.com/${key}.${S3_CONFIG.type}` } }),
    };
  } else{
      console.log("Putting object to bucket");
      const putResponse = await putScreenshot(
        key,
        preview,
        {
          'destination-url': url,
          'key': key,
          'title': body.title || '',
        }
      );
      return {
        statusCode: putResponse.$metadata.httpStatusCode,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: 'Success', data: { url: `https://${S3_CONFIG.bucket}.s3.${AWS_CONFIG.region}.amazonaws.com/${key}.${S3_CONFIG.type}` } }),
      };
  }
};


const screenshot = async (url) => {
  let browser;
  browser = await puppeteer.launch({
    executablePath: isLocal ? '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' : await chromium.executablePath(awsExecutionPath),
    headless: !isLocal,
    args: isLocal ? [] : chromium.args,
    defaultViewport: isLocal ? null : { width: 392, height: 844 },
  });

  const context = browser.defaultBrowserContext();
  await context.overridePermissions('https://www.facebook.com', ['notifications']);

  const page = await browser.newPage();
  await page.setViewport({ 
      width: 412,
      height: 915,
      deviceScaleFactor: 1,
      isMobile: true, 
  });

  console.log("Going to ", url);
  await page.goto(url, {
    waitUntil: 'networkidle2',
  });
  if (await page.$('input[name=email]') !== null) {
    console.log("Pressing key Escape...");
    await page.keyboard.press("Escape");
  }

  await page.setViewport({ 
    width: 1200,
    height: 800,
    deviceScaleFactor: 1,
    isMobile: true, 
  });
  try{
    const screenshot = await page.screenshot({type: "png"});
    console.log("Screenshot saved. Closing the browser...");
    browser.close().catch(err => console.error('Error closing browser:', err));  // Non-blocking close
    return screenshot;
  } catch(err){
    throw Error('Can not take screenshot');
  }
}


const putScreenshot = async (key, screenshot, metadata={}) => {
  console.log("Uploading to S3...");
  const s3Client = new S3Client(AWS_CONFIG);
  const command = new PutObjectCommand({
    Bucket: S3_CONFIG.bucket,
    Key: `${key}.${S3_CONFIG.type}`,
    Body: screenshot,
    Metadata: metadata,
  });
  return await s3Client.send(command);
}

async function saveCookies(page, filePath) {
  const cookies = await page.cookies();
  console.log("saving cookies...");
  await fsPromises.writeFile(filePath, JSON.stringify(cookies, null, 2));
}

async function loadCookies(page, filePath) {
  const cookiesString = await fsPromises.readFile(filePath);
  const cookies = JSON.parse(cookiesString);
  await page.setCookie(...cookies);
}


// const event = {
//     body: {
//         "key": "BVR202",
//         "destinationUrl": "https://www.facebook.com/share/p/15hxATWxUu/",
// }}

// const res = await handler(event);
// console.log(res)