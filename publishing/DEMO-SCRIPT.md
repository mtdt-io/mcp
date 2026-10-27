# MCP review walkthrough

Record the dedicated reviewer session after the cases pass. Use synthetic sandbox data and
hide passwords, OAuth tokens, private contact details and unrelated tabs. The recording must
show real interactions and observable results. Upload it to a reviewer-accessible URL and
verify that access works without your own browser session.

1. Show the plugin and its listing, connect through browser OAuth and display the isolated
   review orgs. Explain View versus Run consent and the account prerequisites.
2. Run the org-discovery prompt, then inspect Test Deployment and its terminal result.
3. Prepare Review Preflight: browse and save both fixture classes with `update_deployment`,
   remove/re-add the test class, then inspect the saved composition with `get_deployment`. Show the
   `check_deployment` output (dependencies, conflicts, preflight warnings, recommended tests) and save
   the recommended test level. Show the validation plan (`validate_deployment` with `dry_run:true`,
   local tests and a rollback snapshot); explain configured actions and pending checks. Stop before
   starting a run for this case.
4. Run Review Promotion: save and inspect the two-class composition, then show the validation plan
   with local tests and a rollback snapshot. Launch by ID with those same options and follow
   `get_deployment_run`. Show the successful validation, then the `execute_deployment` dry run
   choosing a quick deploy of it, then the completed run. Verify ProjectService in UAT
   independently. If a check fails, show the stop and the actual error instead of proceeding.
5. Start one DEV metadata backup and follow it in `list_sources` until it is usable.
6. Demonstrate all three negative cases: View-only consent, an unspecified production target
   and destructive selection, and inaccessible cross-team data. Show that no unintended run,
   deletion or data disclosure occurred.
7. In the configured isolated review project, create Review Card, update its description, archive
   and restore it with `update_work_item`, then create Review Card Deployment with
   project_id/work_item_ids in the same call. Show the card delivery response and deployment link, stopping before a run.
8. Finish by showing where users find setup documentation, support, privacy and terms.

Suggested narration: “mtdt.io connects the agent to Salesforce DevOps actions already available
to this MTDT team. Scope consent and team permissions apply to every operation. Preflight
findings guide the saved composition. The dry run reveals inherited execution actions without
starting them; a successful validation with tests lets mtdt quick-deploy it.”

No recording is fabricated or represented as completed by packaging. Supply its real URL in
the OpenAI Review details form or pass it to the build's `--demo-url` option.

## Work Item association with an existing draft

In a prepared sandbox project, explain: a Work Item tracks a change, a deployment holds the saved
source→target composition, and each validation/deployment run executes one snapshot. Discover the
project explicitly, inspect the card with `get_work_item`, and select the existing draft from
`list_deployments`. Call `update_deployment` with the deployment ID and `link_work_items`, inspect
the card, unlink with `unlink_work_items`, then relink. Repeated identical calls should report no
change. Show that the draft and saved composition remain intact and no run starts.
For a locked group, show `group_operation_required` and direct the user to the explicit group UI
action; do not automatically unlock or detach members.

## Work Item promotion preview and draft

Use a prepared card delivered into UAT. Explain that promotion creates a draft for the next
project environment; it does not execute that draft. Call `promote_work_item` with `dry_run:true`
and explicit project/card/from-environment IDs. Show the target, donors, full fold including
overrides and deletions, verdict, existing carriers and delta options. If the verdict offers
creation, call `promote_work_item` again without `dry_run`, with the unchanged fingerprint and
reviewed mode/replacements.
For a group pass its master and preview stack version, full mode only. Keep the returned
`deployment_id`, inspect its saved composition and links, then stop before run launch. A stale
scope/version requires preview/review again. If already promoted or an equivalent draft exists,
show/reuse that carrier; do not force a duplicate draft for the demo.
