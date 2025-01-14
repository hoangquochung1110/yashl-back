import { PutObjectCommand, S3Client } from "@aws-sdk/client-s3";
// import { MetaBrowserAutomation } from '../../layers/browser-automation/nodejs/lib/browser-automation.js';
import { MetaBrowserAutomation } from '/opt/nodejs/lib/browser-automation.js';
import fsPromises from "fs/promises";


// Environment configuration
const BROWSER_CONFIG = {
  isLocal: process.env.AWS_EXECUTION_ENV === undefined,
  browser: {
    executablePath: process.env.CHROMIUM_EXECUTABLE_PATH,
    headless: false,
  },
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
  const automation = new MetaBrowserAutomation(BROWSER_CONFIG);
  await automation.initialize();
  await automation.navigateAndWait(url);
  const screenshot = await automation.takeScreenshot();
  return putToS3(key, screenshot, {
    'destination-url': url,
    'key': key,
    'title': body.title || '',
  })
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
  const region = process.env.S3_REGION;
  const debug = process.env.DEBUG === "true"
  const outputType = "png";

  if (debug) {
    console.log("writing file locally...");
    await fsPromises.writeFile(
      `./${key}.${outputType}`,
      screenshot
    );
    statusCode = 200;
    url = `local://screenshots/${key}.${outputType}`
  }
  else {
    console.log("Uploading to S3...");

    const s3Client = new S3Client({region: region});
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
