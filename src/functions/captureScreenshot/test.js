import { handler } from './index.js'

// Get command line arguments
const key = process.argv[2]; // First argument after node and script name
const destinationUrl = process.argv[3]; // Second argument


const event = {
    body: {
    "key": key,
    "destinationUrl": destinationUrl
}}

const res = await handler(event);
console.log(res)
