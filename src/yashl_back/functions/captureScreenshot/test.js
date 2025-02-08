import { handler } from './index.js'

// Get command line arguments
const key = process.argv[2]; // First argument after node and script name
const target_url = process.argv[3]; // Second argument


const event = {
    body: {
    "short_path": key,
    "target_url": target_url,
    "cookies_path": "",
}}

const res = await handler(event);
console.log(res)
