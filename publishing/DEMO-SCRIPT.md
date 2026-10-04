# MCP review walkthrough

Record the dedicated reviewer session after the cases pass. Use synthetic sandbox data and
hide passwords, OAuth tokens, private contact details and unrelated tabs. The recording must
show real interactions and observable results. Upload it to a reviewer-accessible URL and
verify that access works without your own browser session.

1. Show the plugin and its listing, connect through browser OAuth and display the isolated
   review orgs. Explain View versus Run consent and the account prerequisites.
2. Run the org-discovery prompt, then inspect Review Baseline and its terminal result.
3. Prepare Review Preflight, browse the two fixture classes, and show dependency, conflict,
   preflight and test-recommendation output. Explain pending checks and advisory findings.
4. Run Review Promotion: validate with local tests and a rollback snapshot. Show the successful
   validation before quick-deploy, then the completed run. Verify ReviewHello in Review Target
   independently. If a check fails, show the stop and the actual error instead of proceeding.
5. Start one Review Source metadata backup and show the finished task and usable backup.
6. Demonstrate all three negative cases: View-only consent, an unspecified production target
   and destructive selection, and inaccessible cross-team data. Show that no unintended run,
   deletion or data disclosure occurred.
7. Finish by showing where users find setup documentation, support, privacy and terms.

Suggested narration: “mtdt.io connects the agent to Salesforce DevOps actions already available
to this MTDT team. Scope consent and team permissions apply to every operation. Preflight
findings guide the selection; a successful validation with tests precedes quick-deploy.”

No recording is fabricated or represented as completed by packaging. Supply its real URL in
the OpenAI Review details form or pass it to the build's `--demo-url` option.
