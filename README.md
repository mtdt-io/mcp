# mtdt — MCP server for your AI agent

Salesforce DevOps in any MCP-capable coding agent. One remote endpoint:

```
https://mcp.mtdt.io/mcp
```

Streamable HTTP + OAuth 2.0 (browser sign-in, Dynamic Client Registration) — **no API keys, no
tokens to copy**. Works with Claude Code, Cursor, OpenAI Codex, OpenCode, and anything else that
speaks MCP.

## What your agent gets

Deploy metadata between Salesforce orgs through [mtdt.io](https://mtdt.io): list orgs, create
deployments, browse/retrieve metadata, pre-deploy checks (impact analysis, target conflicts,
profile & permission warnings, record-backup recommendations), Apex test recommendations,
validate with tests, quick-deploy. Long-running deploys are awaitable server-side
(`await_deploy_status`) so your agent doesn't busy-poll.

Deploy-capable tools require the **Run** (`mtdt:deploy`) consent scope and always respect your
team's mtdt roles — approval-gated targets stay approval-gated.

## Claude Code plugin — connection + built-in skills

The plugin is more than the connection: it ships the deployment know-how as skills, so Claude
doesn't just *have* the tools — it knows the playbook.

- **`mtdt-deploy`** — the full promotion workflow: resolve the target safely (production targets
  get confirmed, never assumed), browse & pick components, the pre-flight battery (the same
  checks a human gets in the Deploy modal), validation-first flow, quick-deploy, and the
  guardrails: the 75% coverage rule, rollback snapshots, approval gates.
- **`mtdt-troubleshoot`** — reading failed runs: component vs test vs coverage failures,
  quick-deploy prerequisites and expiry, stuck retrievals, auth pitfalls — each with the fix,
  not just the diagnosis.

```
/plugin marketplace add mtdt-io/mcp
/plugin install mtdt@mtdt
```

On first use Claude Code opens your browser to sign in to mtdt (OAuth) — no config files.

## Connect (any MCP client)

Verified copy-paste configs per client (and the `type`-field gotchas between them):
**[CONNECT.md](CONNECT.md)**.

Quick versions:

| Client | One-liner |
|---|---|
| Claude Code | `claude mcp add --transport http mtdt https://mcp.mtdt.io/mcp` |
| Cursor | [![Add mtdt to Cursor](https://cursor.com/deeplink/mcp-install-dark.svg)](https://cursor.com/en/install-mcp?name=mtdt&config=eyJ1cmwiOiJodHRwczovL21jcC5tdGR0LmlvL21jcCJ9) |
| OpenAI Codex | `codex mcp add mtdt --url https://mcp.mtdt.io/mcp` |
| OpenCode | `"mcp": { "mtdt": { "type": "remote", "url": "https://mcp.mtdt.io/mcp" } }` |

## Notes

- Requires an mtdt.io account with at least one connected Salesforce org.
- MFA-enrolled accounts are not yet supported by the MCP connection (coming).
