# Open Brain

An MCP server over a local markdown context vault. Claude and other MCP clients read
curated personal and professional context out of the vault, and write generated work
back into it.

The vault is the single source of truth: plain markdown in git, hand-editable, with no
database and no embeddings. Retrieval is keyword search over frontmatter, headings,
tags, and body text. Grep's failure mode is "no match", which is legible; vector
search's is silent bad recall, which is not acceptable when the output is a document
you are about to send.

## Tools

| Tool | Purpose |
|---|---|
| `list_projects` | Project map. Call first to orient. |
| `search_context` | Ranked keyword matches with snippets. Filter by `project` or `type`. |
| `read_note` | One note in full, frontmatter included. |
| `write_note` | Save generated output into the vault. |

## Write safety

Three layers, all enforced in `app/vault/store.py`:

- **Containment.** Every path is resolved before use and must land inside the vault
  root. Traversal, absolute paths, and symlink escapes are refused.
- **Quarantine.** `write_note` only accepts paths under a `generated/` directory or
  `_inbox/`. Curated notes are read-only through MCP. The check runs on the *resolved*
  path, so `_inbox/../profile/resume.md` is refused rather than silently allowed.
- **Auto-commit.** With `VAULT_AUTO_COMMIT=true` each write is committed, so a bad
  write is one `git revert` away. Make sure the vault has an initial commit, otherwise
  there is no baseline to revert to.

`Vault.write_curated()` exists for deliberate non-agent writes and is not exposed as a tool.

Failures are raised as `ToolError` so the message reaches the model. Anything else is
reported to the client as a generic "error executing tool", which leaves the model no
way to correct itself.

## Vault conventions

Every note carries YAML frontmatter. `type` and `updated` are required; `type` and
`project` are what `search_context` filters on.

```yaml
---
type: profile
project: interview-prep
tags: [swift, healthcare]
updated: 2026-08-28
---
```

A note written without frontmatter is stamped with `type: generated`, today's date, and
the project inferred from its path.

## Setup

Requires Python 3.11+ and **`mcp` 2.x**. Note that `FastMCP` was renamed `MCPServer` in
2.x, so v1 examples found online will not import.

```bash
make install
cp .env.example .env    # set VAULT_ROOT
make test
```

## Running

```bash
make mcp         # stdio, for local clients
make mcp-http    # streamable-http on 127.0.0.1:8000
```

### HTTP transport

```bash
export OPEN_BRAIN_API_TOKEN=$(openssl rand -hex 32)
venv/bin/python -m app.mcp.server --transport streamable-http --port 8000
```

The MCP endpoint is `/mcp`, guarded by a bearer token. `/healthz` is exempt so a
tunnel or load balancer can probe it without a credential.

```bash
curl -s -o /dev/null -w '%{http_code}\n' localhost:8000/healthz          # 200
curl -s -o /dev/null -w '%{http_code}\n' -X POST localhost:8000/mcp      # 401
```

The server refuses to start if `OPEN_BRAIN_API_TOKEN` is unset or still `change-me`,
and again if the vault root does not exist. Both checks run before the socket binds,
so a misconfigured server never accepts a request rather than accepting it wide open.

DNS-rebinding protection is on, which means the `Host` header is checked against an
allowlist that defaults to the bind address. Behind a tunnel the Host is the tunnel
domain, so name it:

```bash
venv/bin/python -m app.mcp.server --transport streamable-http \
  --allowed-host vault.example.com
```

Bind to `127.0.0.1` and put the tunnel in front. Binding a public interface puts
write-capable tools on the network behind one static token; the server warns when
you do it but does not stop you.

### Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`, then fully
quit and reopen the app:

```json
{
  "mcpServers": {
    "context-vault": {
      "command": "/absolute/path/to/open-brain/venv/bin/context-vault-mcp",
      "args": ["--transport", "stdio"],
      "env": {
        "VAULT_ROOT": "/absolute/path/to/context-vault",
        "VAULT_AUTO_COMMIT": "true"
      }
    }
  }
}
```

Uses the installed console script, so no `cwd` is needed.

### Claude Code

Claude Code does **not** read `claude_desktop_config.json`. Register it separately:

```bash
claude mcp add context-vault --scope user \
  --env VAULT_ROOT=/absolute/path/to/context-vault \
  --env VAULT_AUTO_COMMIT=true \
  -- /absolute/path/to/open-brain/venv/bin/context-vault-mcp --transport stdio
```

Restart the session, then confirm with `claude mcp list`.

### claude.ai in a browser, and ChatGPT

Neither can reach localhost. Custom connectors are called from Anthropic's and
OpenAI's IP ranges rather than from your machine, so they need a public HTTPS URL: a
tunnel (Cloudflare Tunnel, ngrok) for development, or a real deployment.

That is necessary but not sufficient for claude.ai. Its connector UI has no field for
a static token; it speaks OAuth 2.1 with mandatory PKCE, so a bearer-token server
cannot be added there no matter how it is exposed. Reaching claude.ai means
implementing an authorization server, which this does not yet do.

Bearer auth is enough for everything that lets you set a header: Claude Code over the
network, curl, and programmatic clients.

### Claude Code over HTTP

```bash
claude mcp add --transport http context-vault https://vault.example.com/mcp \
  --header "Authorization: Bearer $OPEN_BRAIN_API_TOKEN"
```

## Layout

```
app/vault/       Vault store and frontmatter handling. All the real logic.
app/mcp/         MCP server. Tool definitions delegate to app.vault.
app/api/         FastAPI health endpoints.
app/core/        Settings, errors, request IDs, token auth.
```

`app/vault` has no MCP dependency and is tested directly, so the transport is a
launch-time choice rather than a design constraint.

## Status

Working end to end: the four tools over both stdio and streamable-http, containment
and quarantine, auto-commit under a bot identity, bearer auth, 50 tests. The HTTP path
has been exercised with a real MCP client: handshake, `tools/list`, a `list_projects`
call, and a refused quarantine bypass.

Not done: no OAuth, so claude.ai's connector UI is out of reach, and nothing is
deployed behind a public URL.
