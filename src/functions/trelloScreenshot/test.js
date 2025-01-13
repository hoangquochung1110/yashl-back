import { handler } from "./index.js"

const event = {
    body: {
        "key": "CDC105",
        "destinationUrl": "https://trello.com/c/df6F3AFl/68-to-display-the-approval-status-on-the-opportunity-list-view-grid",
}}

const res = await handler(event);
console.log(res)
