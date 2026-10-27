---
name: mtdt-troubleshoot
description: Diagnose failed or stuck Salesforce deployments run through mtdt.io. Use when a mtdt deployment run failed, a validation shows errors, quick-deploy is rejected, metadata retrieval seems stuck, or the user asks why their Salesforce deploy is red.
---

# Troubleshooting mtdt deployments

Start from `get_deployment_run` for the deployment — it returns the run's `state`, a one-line
`outcome` and the failure details you need (`component_failures`, `test_failures`,
`code_coverage_warnings`). It answers immediately: while `state` is `queued`, `running` or
`finishing`, call it again every 15–30 s. `waiting` (approval or schedule) does not change by
polling — tell the user. `finishing` means Salesforce is done and post-deploy steps still run; if
one of them fails the run turns `failed` with "Deployed to Salesforce, but a post-deploy step
failed" — the metadata is on the target. Read the failure **category** before proposing fixes:

## Component failures vs test failures vs coverage

- **Component failures** (compile/metadata errors): the target is missing something the component
  references. Run `run_impact_analysis` on the same selection — the missing dependency is usually
  in its findings; retrieve it with `browse_metadata`, save it with `add_deployment_components`,
  then call `validate_deployment` by `deployment_id`.
- **Test failures**: a named Apex test asserted/threw. Read the failure message first — some orgs
  contain intentionally-failing demo/canary tests; if an unrelated pre-existing test fails under
  `test_option: "local"`, switch to `"specific"` with the tests that actually cover your
  components (`recommend_tests`).
- **`codeCoverageWarning` with zero failed tests**: the run "failed" purely on the 75% coverage
  rule — the deployed class has no covering test in the run. Fix: include the test class in the
  saved selection with `add_deployment_components` and run it (`test_option: "specific"`,
  e.g. `MyClass` + `MyClass_Test`), then re-validate by ID.

## Quick-deploy rejected

`quick_deploy` only works after a **Succeeded validation that ran tests** on the same deployment.
`get_deployment_run` on that validation shows `quick_deploy_eligible` and, when false,
`quick_deploy_ineligible_reason`. If it reports no eligible validation: the last validation failed, ran with `NoTestRun`, or a real
deploy already consumed it. Re-validate with `validate_deployment` and `test_option: "local"` or
`"specific"`, then retry. Salesforce quick-deploy windows also expire (~10 days) — a stale
validation needs a fresh one.

## Unexpected settings in the run plan

Use `preview_deployment_run` with the intended `validate` mode and execution options before
starting another run. Its preparation is shared with actual launch, and the call creates no
state or Salesforce work. `execution_settings` exposes inherited settings; `after_deploy` and
`scheduled_jobs` highlight the actions they can cause.

- An unexpected `NoTestRun` is inherited from the saved draft. Preview and validate with
  `test_option: "local"` or `"specific"` + `tests_to_run` when tests are intended.
- `validation_apex` / `saved_jobs`: validation does not automatically disable saved Apex or job
  pause settings. Read the code/jobs and report those actions before launch; do not retry blind.
- Flow activation comes only from the saved deployment config, including its exclusions.
  Review/change it in MTDT, then preview again. If a run or preview rejects the old
  `activate_flows_after_deploy` argument, remove it from the request; configure activation on
  the deployment instead. There is no per-run activation override.
- `flow_tests_target_mismatch`: saved Flow tests belong to a different target; fix the test
  selection in MTDT before launching.
- Preview is a snapshot, not a reservation or a successful preflight. After changing the draft
  or execution options, inspect the plan again. Launch still applies permissions/approval and
  worker checks; a preview alone is not proof that the run will succeed.

## Saved composition rejected before a run

Start with `get_deployment(deployment_id)` to inspect what is saved.
`validate_deployment` takes `deployment_id`; `create_deployment_run` takes `deploy_id`. Neither
accepts a replacement composition. Composition edits follow the UI's last-save-wins model;
concurrent edits are not detected or rejected.

- `inline_config_not_supported` or an input-schema error naming old run arguments: stop passing
  `items`, `all_items`, `selected_items`, `config` or destructive-change arguments at launch.
  Save full components with `add_deployment_components` / `remove_deployment_components`, then
  run by ID. Changing the arguments does not save the previous inline selection automatically.
- `empty_selection`: browse and save the intended components first. A saved deletion or partial
  selection can also make a draft runnable; inspect it before assuming the whole draft is empty.
- `items_not_retrieved` from `add_deployment_components`: a named source component is not in
  this deployment's cache. Run `browse_metadata` for its type and check the spelling against the
  returned rows, then retry the add.
- `deployment_not_ready`: the archive selection is still being populated. Call
  `get_deployment` every ~15s; retry once `ready` is `true`.
- `deployment_population_failed`: read `source.task.error` in `get_deployment` and fix the
  source as described below. Repeating the run cannot repair population.
- `component_has_overrides`: the requested component has an existing partial selection/smart
  intent. Edit that selection in MTDT. Manual file overrides do not cause this reject: add/remove
  preserves them, and a removed component can be re-added with its saved override intact.
- `component_marked_for_deletion`: the component has a saved deletion. Change that intent in
  MTDT before editing its selection; the tools leave the saved deletion intact.
- `saved_config_blocked`: the same partial-selection checks used by the UI found a blocker.
  Read `blockers` and resolve the affected partial selection in MTDT before retrying.
- `permission_denied` mentioning `metadata_deploys.edit`: the user's role cannot edit the draft.
  Ask a team administrator to grant the appropriate permission; do not switch credentials.

## The deployment never populates (repo or backup source)

- `get_deployment(deployment_id)` reports each side's `readiness` with the population task
  behind it, so a failed source unpack reads as `"failed"` with `task.error` instead of an endless
  `"in_progress"`. `"failed"` never recovers by polling. For a backup source: edit the deployment
  in the mtdt web app and pick a finished backup that has an archive, or create a new deployment —
  Refresh does not re-unpack a backup. For an org side: re-authenticate the org, then press Refresh.
- If it shows the source failed with `No value provided for input HTTP label: Key` (or otherwise
  reports there was nothing to download), the backup had no stored package — it finished without an
  archive, so there was never anything to unpack. Newer MCP versions reject such a backup up front
  at `create_deployment` as `{ error: "backup_not_usable", reason: "no_archive" }` and create no
  deployment at all; pick a usable backup from `list_metadata_backups` or run a fresh one.

## Retrieval looks stuck

- `browse_metadata` returning `{ status: "retrieving", partial: true }` just means the retrieval
  is still running and the rows so far are an incomplete snapshot — call it again with the same
  args (safe to repeat; duplicate tasks are impossible). `task_ids` names the JIT tasks still
  running. The names usually arrive within seconds — the answer then turns into
  `status: "names_ready"` and the list is complete — while the contents can take a couple of
  minutes more depending on type size.
  Transient Salesforce errors (HTTP 404/timeouts) self-heal on a retry before escalating.
- `browse_metadata` returning `{ status: "retrieval_failed", failed_tasks }` is a retrieval that
  failed on the Salesforce side for part of the type, not an empty type: read
  `failed_tasks[].error` (read timeouts on big Profiles are the classic). The component **names**
  returned are complete — only some bodies may not have been read yet. mtdt re-queues the retrieval
  automatically (up to 3 times): call it again with the same args to get the list, and report the
  error to the user only if the failure keeps repeating.
- Re-browsing an already-retrieved type serves the cached rows; metadata is cached per deployment.

## Auth / access

- **"MFA required" at connect time**: sign in again and complete the second factor in the
  browser. If sign-in never asks for it, ask the mtdt administrator to enable the MFA step for
  the account. Do not work around the team's MFA policy by switching to an unprotected account.
- **Permission errors on deploy actions**: the user's mtdt role may lack direct-deploy on that
  target — mtdt then forces an approval request; that is policy, not a bug.
- **`reauth_required: true` on an org** (in `list_orgs`): the Salesforce connection needs
  re-authentication in the mtdt web app before any retrieval/deploy against it will work.

## The failure a preflight would have named

Before re-validating blind, run `preflight_deployment` with just `deployment_id` to check the saved
composition — several classic failures show up there with the fix attached: a scheduled Apex (cron) job on a class you are
overwriting (Salesforce refuses the overwrite until the job is aborted), an Entitlement Process
whose Business Hours is missing on the target (deploys "Successfully" and silently drops the
binding), and destructive changes whose components the target still references.

## Deployment blocked by "another deploy in progress"

mtdt deliberately waits when **any** deployment is already running on the target org (including
ones started outside mtdt). This resolves itself; check the target org's deployment status in
Salesforce Setup if it persists.

When the cause is genuinely unclear, gather `get_deployment_run` output plus the run's component
and test failure lists, summarize them for the user, and suggest inspecting the run in the mtdt
web UI where full logs live.

## Work Items

- `project_setup_required`: configure two environments before inserting a new card. It does not
  block operations on an existing card. Always supply the intended project ID.
- `tracker_fields_readonly`: detach the ticket with `update_work_item` and `unlink_ticket:true`
  alone, then edit, or use `force:true` for an intentional user-requested override. Detaching
  retains the text; it does not unlink deployments.
- `group_operation_required`: leave the active group explicitly in the UI before archiving. For
  a locked group deployment, use **Unlink deployment from group** in MTDT UI; ordinary
  `unlink_work_item_deployment` never unlocks the group. An assembled deployment belongs to its master.
  Do not detach deployments or unlock a group automatically.
- `work_item_links_changed`: inspect current links with `get_work_item` and review the intended
  operation again; do not retry blindly. `work_item_link_superseded` means the historical carrier
  was replaced and cannot be reattached; inspect its replacement deployment.
- `ticket_project_mismatch`: the ticket already has a card in another project; use the returned
  project/item IDs explicitly. Do not create a duplicate or move it silently.
- `work_item_link_failed`: keep the returned deployment ID. It was created; only the listed
  `linked_work_item_ids` are confirmed. Inspect `unconfirmed_work_item_ids` and current links
  before using `link_work_item_deployment` for intended missing associations, or finish in the UI.
  Repeating `create_deployment` creates another draft.

## Work Item promotion

- `scope_changed` / `stack_changed`: the promotion changed since preview. Read
  `preview_work_item_promotion` again and review the new donors/carriers or group version before
  creating. Do not blindly substitute the new fingerprint and retry.
- `not_ready` / `nothing_reached_env`: inspect pending deployments and surviving deliveries into
  the source environment. Validation alone does not count as delivery. A green board marker can
  survive rollback while promotion correctly refuses to use that run.
- `no_next_environment`: this is the last environment in the project chain.
- `stack_member`: promote through the group's master. Group creation requires the preview's
  `stack_version`, full mode and no supersede; do not detach participants as a workaround.
- `already_promoted` / preview `reopen`: inspect the existing carrier rather than create another.
  `delta_not_available` carries its reason. `open_draft_exists` needs review of the existing
  open carriers; delta never permits superseding them.
- A successful create with `supersede_failed` still created `deployment_id`. Keep that ID and
  inspect the replacement marks and links in MTDT. A generic failure or lost response also needs
  inspecting the card before retry, because creation is not idempotent.
