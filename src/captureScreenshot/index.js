import { PutObjectCommand, S3Client } from "@aws-sdk/client-s3";
import chromium from '@sparticuz/chromium-min';
import fsPromises from "fs/promises";
import puppeteer from 'puppeteer-core';


const email = process.env.META_EMAIL;
const password = process.env.META_PASSWORD;
// identify whether we are running locally or in AWS
const isLocal = process.env.AWS_EXECUTION_ENV === undefined;
// should put object to s3 or not
const debug = process.env.DEBUG === "true";

const region = process.env.S3_REGION;
const bucket = process.env.S3_BUCKET;
const type = "png";


export const handler = async (event) => {
  let body;

  // Check if body is a string and attempt to parse it
  if (typeof event.body === 'string') {
      try {
          body = JSON.parse(event.body);
      } catch (error) {
          // Handle the case where parsing fails
          return { error: 'Invalid JSON string' };
      }
  } else if (typeof event.body === 'object') {
      // If it's already an object, just use it directly
      body = event.body;
  } else {
      return { error: 'Unsupported body type' };
  }

  const key = body.key;
  const url = body.destinationUrl;

  const preview = await screenshot(url, email, password);
  if (debug){
      console.log("writing file locally...");
      fsPromises.writeFile("./screenshots/screenshot.png", preview);
      const response = {
          statusCode: 200,
          headers: {
              "Content-Type": "application/json",
          },
          body: JSON.stringify({
              message: "Success",
              data: {
                  "url": `https://mock-bucket.s3.mock-region.amazonaws.com/${key}.${type}`
              }
          }),
      };
      return response
  } else{
      console.log("Putting object to bucket");
      const putResponse = await putScreenshot(key, preview, "png");
      const statusCode = putResponse.$metadata.httpStatusCode;
      if (statusCode === 200){
          const response = {
              statusCode: 200,
              headers: {
                  "Content-Type": "application/json",
              },
              body: JSON.stringify({
                  message: "Success",
                  data: {
                      "url": `https://${bucket}.s3.${region}.amazonaws.com/${key}.${type}`
                  }
              }),
          };
          return response;
      } else{
          throw Error("Fail to put object. Status code: ", statusCode);
      }
  }
};


const screenshot = async (url, email, password) => {
  let browser;
  if (isLocal){
    browser = await puppeteer.launch({
      executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
      headless: false,
    });
    console.log("running locally");
  } else{
    browser = await puppeteer.launch({
      args: chromium.args,
      defaultViewport: {
          width: 392,
          height: 844,
        },
      executablePath: await chromium.executablePath(
          'https://github.com/Sparticuz/chromium/releases/download/v123.0.1/chromium-v123.0.1-pack.tar',
      ),
      headless: chromium.headless,
    });
  }

  const context = browser.defaultBrowserContext();
  await context.overridePermissions('https://www.facebook.com', ['notifications']);

  const page = await browser.newPage();
  await page.setViewport({ 
      width: 412,
      height: 915,
      deviceScaleFactor: 1,
      isMobile: true, 
  });

  // Load cookies if they exist
  const cookiesPath = './cookies.json';
  try {
    console.log("Loading cookies...");
    await loadCookies(page, cookiesPath);
  } catch (error) {
    console.log('No cookies found, proceeding without them.');
  }
  await page.goto(url, {
    waitUntil: 'networkidle2',
  });
  if (await page.$('input[name=email]') !== null) {
    await page.type('input[name="email"]', email, {delay: 100});
    await page.keyboard.press('Tab');
    await page.type('input[name="pass"]', password, {delay: 100});
    try{
      const loginButton = await page.waitForSelector(
        '[aria-label="Accessible login button"]',
        {
          timeout: 2000,
        }
      )
      await loginButton.click();
      console.log('Clicked the login button.');
      // Save cookies after login
      // await saveCookies(page, cookiesPath);
      await page.waitForNavigation({
        timeout: 12000,
      });
    } catch(err){
        // const err_msg = 'Login button not found.'
        // console.log(err);
        throw Error(err);
    }
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
    await browser.close();
    return screenshot;
  } catch(err){
    throw Error('Can not take screenshot');
  }
}


const putScreenshot = async (key, screenshot, extension="png") => {
  try {
    const s3Client = new S3Client({
        region: region,
        credentials: {
            accessKeyId: process.env.AWS_ACCESS_KEY_ID,
            secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY,
            sessionToken: process.env.AWS_SESSION_TOKEN,
        }
    });
    const command = new PutObjectCommand({
        Bucket: bucket,
        Key: `${key}.${extension}`,
        Body: screenshot,
    });
    const response = await s3Client.send(command);
    console.log("Successfully put object");
    return response;
  } catch(err){
    console.log(err);
  }
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