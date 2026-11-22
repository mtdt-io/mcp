# mtdt.io: Salesforce DevOps for AI agents

This extension adds the [mtdt.io](https://mtdt.io) MCP server to VS Code and Cursor. Your AI agent
(GitHub Copilot in VS Code, Cursor Agent) can then run your Salesforce DevOps workflow through
mtdt.io:

- find orgs and deployment sources: git repos, metadata backups, uploaded archives;
- create a deployment, browse metadata and pick components, set the Apex test level;
- run the pre-deploy checks a human gets in the Deploy modal: missing dependencies, target
  conflicts, profile and permission warnings, record-backup recommendations, Apex test
  recommendations;
- validate with tests, deploy, or quick-deploy an earlier validation;
- compare two orgs, back up org metadata, read an org's deploy log and Setup changes;
- move Work Items through a project's environments.

The extension contains no tools of its own. It registers one remote server,
`https://mcp.mtdt.io`, and your editor connects to it.

## Requirements

- An mtdt.io account with at least one connected Salesforce org.
- VS Code 1.101 or later with GitHub Copilot, or Cursor.

## Get started

1. Install the extension.
2. **VS Code:** open Chat. The server is listed as **mtdt.io** under **MCP Servers - Installed** in
   the Extensions view and in **MCP: List Servers** in the Command Palette. Start it there, or let
   Chat start it when your agent first needs it.
   **Cursor:** the server appears under **Cursor Settings → MCP**.
3. On first connection your editor opens the browser. Sign in to mtdt.io and approve the scopes on
   the consent screen. If your account or team requires multi-factor authentication, complete the
   second factor during sign-in.

Sign-in uses OAuth 2.0 with PKCE and Dynamic Client Registration. There are no API keys or tokens
to copy.

## Permissions

- Reading needs the **View** (`mtdt:read`) scope.
- Creating and editing deployments and Work Items, browsing metadata, comparing orgs, validating,
  deploying, backups and archive uploads need the **Run** (`mtdt:deploy`) scope, granted
  separately on the consent screen.
- Every call runs under your mtdt user and your team roles. Approval-gated targets stay
  approval-gated. A real deploy to an org marked important waits for your explicit confirmation.

Revoke access at any time from your mtdt account.

## Other editors

If your editor does not let extensions add MCP servers, the extension shows a one-time message
with the server URL to add in the editor's MCP settings. The commands **mtdt.io: Copy MCP server
URL** and **mtdt.io: Open MCP setup guide** are always available in the Command Palette.

Setup for Claude Code, OpenAI Codex, OpenCode and other clients:
[docs.mtdt.io/docs/mcp](https://docs.mtdt.io/docs/mcp).

## Privacy and support

The server processes the Salesforce metadata and deployment and backup information you request
through the mtdt.io service. Review the
[privacy policy](https://docs.mtdt.io/docs/legal-information/privacy-policy/) and
[terms of service](https://docs.mtdt.io/docs/legal-information/terms/) before connecting.

Support: support@mtdt.io or the [contact form](https://mtdt.io/#contact).
