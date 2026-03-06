# Basic documentation for this tool.

## What is my OPEN_BRAIN_API_TOKEN?

OPEN_BRAIN_API_TOKEN is a simple secret token your own clients (or MCP tools) send to authenticate to your Open
Brain API.

Set any long random string in .env, for example:

OPEN_BRAIN_API_TOKEN=ob_4f9c1d8a2b7e6f1c9d3a8e5b2f7c1d4

How it’s used:

- Your API expects header: Authorization: Bearer <OPEN_BRAIN_API_TOKEN>
- If it doesn’t match, requests to protected routes (/memories, /search) are rejected

Quick test example:

curl -X GET http://127.0.0.1:8000/memories \
 -H "Authorization: Bearer ob_4f9c1d8a2b7e6f1c9d3a8e5b2f7c1d4"

Generate one safely:

python3 -c "import secrets; print('ob\_' + secrets.token_hex(24))"
