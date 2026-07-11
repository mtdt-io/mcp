# mtdt — Claude Code plugin

Salesforce DevOps from your IDE. One install connects the [mtdt.io](https://mtdt.io) MCP server
and teaches Claude the deployment workflow.

## Install

```
/plugin marketplace add mtdt-io/claude-code-plugins
/plugin install mtdt@mtdt
```

On first use Claude Code opens your browser to sign in to mtdt (OAuth) — no API keys, no config
files.

## What you get

- **MCP server** (`https://mcp.mtdt.io/mcp`): list orgs, create deployments, retrieve metadata,
  impact analysis, target-conflict checks, Apex test recommendations, validate + quick-deploy.
- **`mtdt-deploy` skill**: the full promotion playbook — pre-flight checks, validation-first flow,
  production guardrails.
- **`mtdt-troubleshoot` skill**: reading failed runs — component vs test failures, the 75%
  coverage rule, quick-deploy prerequisites.

## Notes

- Requires an mtdt.io account with at least one connected Salesforce org.
- MFA-enrolled accounts are not yet supported by the MCP connection (coming).
- Deploy actions respect your team's mtdt roles — approval-gated targets stay approval-gated.
