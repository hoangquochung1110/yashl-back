import { PutObjectCommand, S3Client, GetObjectCommand } from "@aws-sdk/client-s3";
// import { BrowserAutomation } from '../../layers/browser-automation/nodejs/lib/browser-automation.js';
import { BrowserAutomation } from '/opt/nodejs/lib/browser-automation.js';
import fsPromises from "fs/promises";


// Environment configuration
const BROWSER_CONFIG = {
  isLocal: process.env.AWS_EXECUTION_ENV === undefined,
  browser: {
    executablePath: process.env.CHROMIUM_EXECUTABLE_PATH,
    headless: false,
  },
};

const region = process.env.S3_REGION;

const s3Client = new S3Client({region: region});


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

  const shortPath = body.short_path;
  const url = body.target_url;
  const cookiesPath = body.cookies_path;
  const userAgent = body.user_agent || {};
  let cookies = null;
  if (cookiesPath) {
    cookies = await getCookies(cookiesPath);
  }
  try {
    console.log('Initializing browser automation');
    const automation = new BrowserAutomation(BROWSER_CONFIG);
    await automation.initialize({
      cookies: cookies,
      userAgent: userAgent,
    });
    const screenshot = await automation.takeScreenshot(url);
    return putToS3(shortPath, screenshot);
  } catch (error) {
    console.error(error);
  }
};


const putToS3 = async (key, data, metadata={}) => {
  /**
   * Puts a screenshot to S3. If ENV_CONFIG.debug is true, writes
   * the file locally instead. Returns a response object with a
   * statusCode, headers, and a body with a JSON object containing
   * the URL of the uploaded file.
   *
   * @param {string} key the key to use for the screenshot
   * @param {Buffer} data the screenshot data
   * @param {Object} metadata additional metadata to store with the screenshot
   * @returns {Promise<Object>}
   */  
  let statusCode;
  let url;
  const bucket = process.env.S3_PREVIEW_BUCKET;
  const debug = process.env.DEBUG === "true"
  const outputType = "png";

  if (debug) {
    console.log("writing file locally...");
    await fsPromises.writeFile(
      `./${key}.${outputType}`,
      data
    );
    statusCode = 200;
    url = `local://screenshots/${key}.${outputType}`
  }
  else {
    console.log("Uploading to S3...");

    const command = new PutObjectCommand({
      Bucket: bucket,
      Key: `${key}.${outputType}`,
      Body: data,
      Metadata: metadata,
    });
    const putResponse = await s3Client.send(command);
    statusCode = putResponse.$metadata.httpStatusCode
    url = `https://${bucket}.s3.${region}.amazonaws.com/${key}.${outputType}`
  }

  return {
    statusCode: statusCode,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message: "Success",
      data: { url: url }
    }),
  };
}

const getCookies = async (cookiesPath) => {
  try {
      if (!cookiesPath) {
          throw new Error('Cookies path is required');
      }

      let content;
      
      // Check if path starts with http(s) - simple URL check
      if (cookiesPath.startsWith('http://') || cookiesPath.startsWith('https://')) {
          // Simple S3 URL check
          if (!cookiesPath.includes(`s3.${region}.amazonaws.com`)) {
              throw new Error('Only S3 URLs are supported');
          }

          // Handle S3 URL
          const url = new URL(cookiesPath);
          const bucketName = url.hostname.split('.')[0];
          const objectKey = url.pathname.substring(1);

          const response = await s3Client.send(new GetObjectCommand({
              Bucket: bucketName,
              Key: objectKey
          }));
          content = await response.Body.transformToString();
      } else {
          // Handle local file
          const absolutePath = path.resolve(cookiesPath);
          content = await fsPromises.readFile(absolutePath, 'utf8');
      }

      return JSON.parse(content).cookies;

  } catch (error) {
      console.error('Error in getCookies:', error);
      throw error;
  }
};
