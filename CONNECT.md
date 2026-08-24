# Connect mtdt to your AI coding agent

The [mtdt.io](https://mtdt.io) MCP server is one endpoint that works with every MCP-capable
client:

```
https://mcp.mtdt.io/mcp
```

Transport is Streamable HTTP. Authentication is OAuth 2.0 (authorization code + PKCE, with
Dynamic Client Registration) — your client opens a browser to sign in to mtdt. **No API keys,
no tokens to copy.**

Requirements:

- An mtdt.io account with at least one connected Salesforce org.
- MFA-enrolled mtdt accounts are not yet supported by the MCP connection (coming).
- On the consent screen you grant **View** (`mtdt:read`) and optionally **Run** (`mtdt:deploy`)
  privileges. Deploy-capable tools refuse without the Run scope, and always respect your team's
  mtdt roles — approval-gated targets stay approval-gated.

---

## Claude Code

The plugin gives you the MCP connection **plus** the deploy/troubleshoot skills:

```
/plugin marketplace add mtdt-io/mcp
/plugin install mtdt@mtdt
```

MCP server only (no skills):

```bash
claude mcp add --transport http mtdt https://mcp.mtdt.io/mcp
```

or in `.mcp.json`:

```json
{
  "mcpServers": {
    "mtdt": {
      "type": "http",
      "url": "https://mcp.mtdt.io/mcp"
    }
  }
}
```

> Claude Code requires the `"type": "http"` field — a bare `url` entry is skipped with a warning.

To sign in: run `/mcp` inside a session and pick **Authenticate**, or `claude mcp login mtdt`.

## Cursor

[![Add mtdt to Cursor](https://cursor.com/deeplink/mcp-install-dark.svg)](https://cursor.com/en/install-mcp?name=mtdt&config=eyJ1cmwiOiJodHRwczovL21jcC5tdGR0LmlvL21jcCJ9)

Or manually in `~/.cursor/mcp.json` (global) or `.cursor/mcp.json` (project):

```json
{
  "mcpServers": {
    "mtdt": {
      "url": "https://mcp.mtdt.io/mcp"
    }
  }
}
```

Cursor infers the remote transport from `url` (no `type` field) and starts the OAuth browser
flow on first connection. Verify under **Cursor Settings → MCP**.

## OpenAI Codex

Codex supports remote Streamable HTTP MCP servers with OAuth natively:

```bash
codex mcp add mtdt --url https://mcp.mtdt.io/mcp
codex mcp login mtdt
```

or in `~/.codex/config.toml`:

```toml
[mcp_servers.mtdt]
url = "https://mcp.mtdt.io/mcp"
```

OAuth is the default when no bearer token is configured — nothing else to set.

> **Known issue in Codex ≥ 0.143** ([openai/codex#31573](https://github.com/openai/codex/issues/31573)):
> login fails with `Authorization server response missing required issuer` — Codex's OAuth callback
> drops the RFC 9207 `iss` parameter its own validator then requires. Until the fix ships, use
> Codex 0.141: `npm install -g @openai/codex@0.141.0` (check `which -a codex` for a newer binary
> shadowing it, e.g. `~/.local/bin/codex`). Verified working end-to-end on 0.141.0.

## OpenCode

In `opencode.json` (project) or the global config:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "mtdt": {
      "type": "remote",
      "url": "https://mcp.mtdt.io/mcp",
      "enabled": true
    }
  }
}
```

> OpenCode uses the `mcp` key (not `mcpServers`) and requires `"type": "remote"`.

OpenCode detects the 401 and runs the OAuth flow automatically; trigger it manually with
`opencode mcp auth mtdt` if needed.

---

## The `type` field gotcha

Copy-pasting one client's snippet into another silently fails — the required `type` differs:

| Client | Config key | `type` field |
|---|---|---|
| Claude Code | `mcpServers` | required, `"http"` |
| Cursor | `mcpServers` | omit |
| Codex | `[mcp_servers.*]` | none (inferred from `url`) |
| OpenCode | `mcp` | required, `"remote"` |

## What you get

Salesforce DevOps tools in your agent: list orgs, create deployments, retrieve metadata,
impact analysis, target-conflict checks, Apex test recommendations, validate with tests,
quick-deploy. Long-running deploys are awaitable server-side (`await_deploy_status`) so your
agent doesn't busy-poll.
