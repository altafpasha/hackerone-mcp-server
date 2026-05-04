# HackerOne MCP Server

A [Model Context Protocol (MCP)](https://modelcontextprotocol.io) server that connects Claude Desktop (or any MCP-compatible AI client) directly to the HackerOne API.

Ask Claude things like **"Show me Shopify's scope on HackerOne"** or **"What are my triaged reports?"** — no browser needed.

---

## Features

- Fetch full program details (policy, stats, response SLAs)
- View structured in-scope / out-of-scope targets with bounty eligibility
- Check bounty payout tables per severity
- Search and browse public programs
- Read your own submitted reports filtered by state
- View your hacker profile (reputation, signal, rank)

---

## Prerequisites

- Python 3.10+
- A [HackerOne account](https://hackerone.com) with an API token
- [Claude Desktop](https://claude.ai/download) (or any MCP-compatible client)

---

## Quick Start

### 1. Get Your HackerOne API Token

1. Log in to HackerOne
2. Go to **Settings → API Token**: https://hackerone.com/settings/api_token/edit
3. Create a new token and note both the **username** shown and the **token value**

### 2. Clone the Repository

```bash
git clone https://github.com/altafpasha/hackerone-mcp-server.git
cd hackerone-mcp-server
```

### 3. Install Dependencies

```bash
pip install "mcp[cli]" httpx
```

Or use the requirements file:

```bash
pip install -r requirements.txt
```

### 4. Set Your Credentials

Copy the example env file and fill it in:

```bash
cp .env.example .env
```

Edit `.env`:

```
H1_USERNAME=your_h1_username
H1_API_TOKEN=your_api_token_here
```

> **Never commit your `.env` file.** It is listed in `.gitignore` by default.

---

## Connect to Claude Desktop

Edit your Claude Desktop config file:

| OS | Config file path |
|---|---|
| Linux | `~/.config/Claude/claude_desktop_config.json` |
| macOS | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Windows | `%APPDATA%\Claude\claude_desktop_config.json` |

Add the following block (create the file if it doesn't exist).

**Linux / macOS:**

```json
{
  "mcpServers": {
    "hackerone": {
      "command": "python3",
      "args": ["/home/yourname/hackerone-mcp-server/h1_mcp_server.py"],
      "env": {
        "H1_USERNAME": "your_h1_username",
        "H1_API_TOKEN": "your_api_token_here"
      }
    }
  }
}
```

**Windows:**

```json
{
  "mcpServers": {
    "hackerone": {
      "command": "python",
      "args": ["C:\\Users\\yourname\\hackerone-mcp-server\\h1_mcp_server.py"],
      "env": {
        "H1_USERNAME": "your_h1_username",
        "H1_API_TOKEN": "your_api_token_here"
      }
    }
  }
}
```

> Replace the path with the actual absolute path to `h1_mcp_server.py` on your machine.

Fully quit and reopen Claude Desktop. You should see the MCP plug icon in the toolbar.

---

## Linux Setup (Full Walkthrough)

This covers a clean install on Ubuntu/Debian and similar distros.

```bash
# 1. Install Python 3 if not already present
sudo apt update && sudo apt install -y python3 python3-pip git

# 2. Clone the repo
git clone https://github.com/altafpasha/hackerone-mcp-server.git
cd hackerone-mcp-server

# 3. Install dependencies
pip3 install -r requirements.txt

# 4. Set credentials
cp .env.example .env
nano .env   # fill in H1_USERNAME and H1_API_TOKEN

# 5. Test the server runs (Ctrl+C to stop)
python3 h1_mcp_server.py
```

Then create the Claude Desktop config:

```bash
mkdir -p ~/.config/Claude
nano ~/.config/Claude/claude_desktop_config.json
```

Paste:

```json
{
  "mcpServers": {
    "hackerone": {
      "command": "python3",
      "args": ["/home/yourname/hackerone-mcp-server/h1_mcp_server.py"],
      "env": {
        "H1_USERNAME": "your_h1_username",
        "H1_API_TOKEN": "your_api_token_here"
      }
    }
  }
}
```

Use `which python3` if you need the full interpreter path (e.g. `/usr/bin/python3`).

Restart Claude Desktop. The MCP plug icon should appear in the toolbar.

> **Using a virtualenv?** Point `"command"` to the venv interpreter instead:  
> `"command": "/home/yourname/hackerone-mcp-server/.venv/bin/python3"`

---

## Connect via Docker

Build the image:

```bash
docker build -t hackerone-mcp-server .
```

Use this config in `claude_desktop_config.json` instead:

```json
{
  "mcpServers": {
    "hackerone": {
      "command": "docker",
      "args": [
        "run", "--rm", "-i",
        "-e", "H1_USERNAME",
        "-e", "H1_API_TOKEN",
        "hackerone-mcp-server"
      ],
      "env": {
        "H1_USERNAME": "your_h1_username",
        "H1_API_TOKEN": "your_api_token_here"
      }
    }
  }
}
```

---

## Available Tools

The server exposes these tools to Claude. You can call them naturally in conversation:

| Tool | What it does |
|---|---|
| `get_program(handle)` | Full program details: policy, stats, SLAs |
| `get_scope(handle)` | In-scope and out-of-scope targets with bounty tags |
| `get_bounties(handle)` | Bounty payout table by severity |
| `list_programs(page, bounties_only, keyword)` | Browse public programs |
| `search_program(query)` | Search programs by name or handle |
| `get_program_guidelines(handle)` | Rules of engagement / policy text |
| `get_my_reports(state, page)` | Your submitted reports filtered by state |
| `get_my_profile()` | Your reputation, signal, impact, and rank |

---

## Example Prompts

```
"Show me the full scope for Shopify on HackerOne"

"Is api.github.com in scope for GitHub's program? What's the max severity?"

"What are Twitter's bounty payouts for critical findings?"

"Search for crypto-related bug bounty programs on HackerOne"

"List all programs that offer monetary bounties, page 2"

"What does Grab's safe harbor policy say?"

"Show my triaged reports"

"What's my HackerOne reputation and rank?"

"Compare the scope of gitlab and github on HackerOne"
```

---

## `get_my_reports` State Values

| State | Meaning |
|---|---|
| `all` | All reports (default) |
| `new` | Submitted, not yet triaged |
| `triaged` | Accepted and being investigated |
| `resolved` | Fixed and closed |
| `bounty-awarded` | Bounty paid out |
| `informative` | Acknowledged but no action |
| `duplicate` | Already reported |
| `not-applicable` | Out of scope or not a bug |

---

## Troubleshooting

| Error | Fix |
|---|---|
| `Missing H1_USERNAME or H1_API_TOKEN` | Add credentials to the `env` block in `claude_desktop_config.json` |
| `401 Unauthorized` | Token is wrong or expired — regenerate at HackerOne settings |
| `404 Not Found` | Program handle is wrong — use `search_program` to find the correct handle |
| MCP server not loading | Check Claude Desktop logs: **Help → Show Logs** |
| `python: command not found` | Use `python3` on Linux/macOS; run `which python3` to get the full path and use that in the config |
| MCP server crashes on Linux | Run `python3 h1_mcp_server.py` manually in a terminal to see the error output |

---

## API Rate Limits

HackerOne allows approximately **5 requests/second**. Each tool call makes 1–2 API requests. You will not hit limits during normal use.

API reference: https://api.hackerone.com/

---

## Project Structure

```
hackerone-mcp-server/
├── h1_mcp_server.py          # MCP server (all tools)
├── requirements.txt          # Python dependencies
├── Dockerfile                # Docker build
├── docker-compose.yml        # Docker Compose helper
├── claude_desktop_config_snippet.json  # Config example (Docker)
├── .env.example              # Credential template
├── .gitignore
├── LICENSE
└── README.md
```

---

## Contributing

Pull requests are welcome. For major changes, open an issue first to discuss what you'd like to change.

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Commit your changes
4. Open a pull request

---

## License

[MIT](LICENSE)
