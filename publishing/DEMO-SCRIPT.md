# MCP review walkthrough

Record the dedicated reviewer session after the cases pass. Use synthetic sandbox data and
hide passwords, OAuth tokens, private contact details and unrelated tabs. The recording must
show real interactions and observable results. Upload it to a reviewer-accessible URL and
verify that access works without your own browser session.

1. Show the plugin and its listing, connect through browser OAuth and display the isolated
   review orgs. Explain View versus Run consent and the account prerequisites.
2. Run the org-discovery prompt, then inspect Test Deployment and its terminal result.
3. Prepare Review Preflight: browse and save both fixture classes, remove/re-add the test class,
   then inspect the saved composition. Show dependency, conflict, preflight and recommendation
   output. Preview validation with local tests and a rollback snapshot; explain configured actions
   and pending checks. Stop before starting a run for this case.
4. Run Review Promotion: save and inspect the two-class selection, then preview validation with
   local tests and a rollback snapshot. Launch by ID with those same execution options. Show the
   successful validation before quick-deploy, then the completed run. Verify ProjectService in UAT
   independently. If a check fails, show the stop and the actual error instead of proceeding.
5. Start one DEV metadata backup and show the finished task and usable backup.
6. Demonstrate all three negative cases: View-only consent, an unspecified production target
   and destructive selection, and inaccessible cross-team data. Show that no unintended run,
   deletion or data disclosure occurred.
7. In the configured isolated review project, create Review Card, update its description, archive
   and restore it, then create Review Card Deployment with project_id/work_item_ids in the same
   call. Show the card delivery response and deployment link, stopping before a run.
8. Finish by showing where users find setup documentation, support, privacy and terms.

Suggested narration: “mtdt.io connects the agent to Salesforce DevOps actions already available
to this MTDT team. Scope consent and team permissions apply to every operation. Preflight
findings guide the saved selection. The preview reveals inherited execution actions without
starting them; a successful validation with tests precedes quick-deploy.”

No recording is fabricated or represented as completed by packaging. Supply its real URL in
the OpenAI Review details form or pass it to the build's `--demo-url` option.

## Work Item association with an existing draft

In a prepared sandbox project, explain: a Work Item tracks a change, a deployment holds the saved
source→target composition, and each validation/deployment run executes one snapshot. Discover the
project explicitly, inspect the card with `get_work_item`, and select the existing draft from
`list_deployments`. Call `link_work_item_deployment` with project/item/deployment IDs, inspect the
card, unlink with `unlink_work_item_deployment`, then relink. Repeated identical calls should
return `changed:false`. Show that the draft and saved composition remain intact and no run starts.
For a locked group, show `group_operation_required` and direct the user to the explicit group UI
action; do not automatically unlock or detach members.
