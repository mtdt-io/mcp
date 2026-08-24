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

## Connect

Verified copy-paste configs per client (and the `type`-field gotchas between them):
**[CONNECT.md](CONNECT.md)**.

Quick versions:

| Client | One-liner |
|---|---|
| Claude Code | `claude mcp add --transport http mtdt https://mcp.mtdt.io/mcp` |
| Cursor | [![Add mtdt to Cursor](https://cursor.com/deeplink/mcp-install-dark.svg)](https://cursor.com/en/install-mcp?name=mtdt&config=eyJ1cmwiOiJodHRwczovL21jcC5tdGR0LmlvL21jcCJ9) |
| OpenAI Codex | `codex mcp add mtdt --url https://mcp.mtdt.io/mcp` |
| OpenCode | `"mcp": { "mtdt": { "type": "remote", "url": "https://mcp.mtdt.io/mcp" } }` |

## Claude Code plugin

For Claude Code there is also a plugin that bundles the MCP connection with two skills —
`mtdt-deploy` (the full promotion playbook: pre-flight checks, validation-first flow, production
guardrails) and `mtdt-troubleshoot` (reading failed runs: component vs test failures, the 75%
coverage rule, quick-deploy prerequisites):

```
/plugin marketplace add mtdt-io/mcp
/plugin install mtdt@mtdt
```

## Notes

- Requires an mtdt.io account with at least one connected Salesforce org.
- MFA-enrolled accounts are not yet supported by the MCP connection (coming).
