# HackerOne MCP Server for Claude Desktop

Fetch H1 program scope, guidelines, bounties, and your reports directly inside Claude.

---

## 1. Get Your API Token

1. Log into HackerOne
2. Go to → **Settings → API Token** → https://hackerone.com/settings/api_token/edit
3. Create a token (save the username shown there too)

---

## 2. Place the Server File

Copy `h1_mcp_server.py` anywhere on your machine, e.g.:

```
~/mcp-servers/h1_mcp_server.py
```

Install dependencies (once):

```bash
pip install "mcp[cli]" httpx
```

---

## 3. Configure Claude Desktop

Edit your Claude Desktop config file:

- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

Merge this into the file (create it if it doesn't exist):

```json
{
  "mcpServers": {
    "hackerone": {
      "command": "python3",
      "args": ["/Users/yourname/mcp-servers/h1_mcp_server.py"],
      "env": {
        "H1_USERNAME": "your_h1_username",
        "H1_API_TOKEN": "your_api_token_here"
      }
    }
  }
}
```

> ⚠️ Replace `/Users/yourname/mcp-servers/h1_mcp_server.py` with the actual path.  
> ⚠️ On Windows use: `"command": "python"` instead of `"python3"`.

---

## 4. Restart Claude Desktop

Fully quit and reopen Claude Desktop. You should see the 🔌 MCP icon.

---

## Available Tools (ask Claude naturally)

| What you say | Tool triggered |
|---|---|
| "Show me Shopify's scope on HackerOne" | `get_scope("shopify")` |
| "What are the guidelines for GitHub's H1 program?" | `get_program_guidelines("github")` |
| "What are Twitter's bounty payouts?" | `get_bounties("twitter")` |
| "Full details for NordVPN program" | `get_program("nordvpn")` |
| "Search for crypto programs on H1" | `search_program("crypto")` |
| "List open bug bounty programs" | `list_programs(bounties_only=True)` |
| "Show my triaged reports" | `get_my_reports(state="triaged")` |
| "What's my H1 reputation and rank?" | `get_my_profile()` |

---

## Example Prompts

```
"Is api.shopify.com in scope for their H1 program? What's the max severity?"

"Compare the scope of github and gitlab on HackerOne"

"Show me my bounty-awarded reports from H1"

"What does Grab's safe harbor policy say?"

"List all programs that offer bounties on HackerOne, page 2"
```

---

## Troubleshooting

| Error | Fix |
|---|---|
| `Missing H1_USERNAME or H1_API_TOKEN` | Add env vars to claude_desktop_config.json |
| `401 Unauthorized` | Token is wrong or expired — regenerate at H1 settings |
| `404 Not Found` | Check program handle spelling (use `search_program` first) |
| MCP not loading | Check Claude Desktop logs: Help → Show Logs |

---

## API Rate Limits

HackerOne API allows **~5 requests/second**. This server makes 1–2 calls per tool.
No issues in normal use.

Programs API docs: https://api.hackerone.com/
