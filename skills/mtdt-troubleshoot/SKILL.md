---
name: mtdt-troubleshoot
description: Diagnose failed or stuck Salesforce deployments run through mtdt.io. Use when a mtdt deployment run failed, a validation shows errors, quick-deploy is rejected, metadata retrieval seems stuck, or the user asks why their Salesforce deploy is red.
---

# Troubleshooting mtdt deployments

Start from `get_deploy_status` for the deployment — it returns a derived status plus the failure
details you need. (To *wait* on a still-running run, use `await_deploy_status` instead — it blocks
up to ~50s server-side; while it returns `timed_out: true`, call it again.) Read the failure
**category** before proposing fixes:

## Component failures vs test failures vs coverage

- **Component failures** (compile/metadata errors): the target is missing something the component
  references. Run `run_impact_analysis` on the same selection — the missing dependency is usually
  in its findings; add it and re-validate.
- **Test failures**: a named Apex test asserted/threw. Read the failure message first — some orgs
  contain intentionally-failing demo/canary tests; if an unrelated pre-existing test fails under
  `test_option: "local"`, switch to `"specific"` with the tests that actually cover your
  components (`recommend_tests`).
- **`codeCoverageWarning` with zero failed tests**: the run "failed" purely on the 75% coverage
  rule — the deployed class has no covering test in the run. Fix: include the test class in the
  selection and run it (`test_option: "specific"`, e.g. `MyClass` + `MyClass_Test`), then
  re-validate.

## Quick-deploy rejected

`quick_deploy` only works after a **Succeeded validation that ran tests** on the same deployment.
If it reports no eligible validation: the last validation failed, ran with `NoTestRun`, or a real
deploy already consumed it. Re-validate with `validate_deployment` and `test_option: "local"` or
`"specific"`, then retry. Salesforce quick-deploy windows also expire (~10 days) — a stale
validation needs a fresh one.

## `items_not_retrieved` from validate_deployment

A component you named was never retrieved for this deployment — the reject lists exactly which.
Run `browse_metadata` for that type first (it retrieves on first call) and check the spelling
against its rows; only retrieved components can be deployed.

## The deployment never populates (repo or backup source)

- `check_deployment_creation_status(deployment_id)` reports each side with the population task
  behind it, so a failed source unpack reads as `"failed"` with `task.error` instead of an endless
  `"in progress"`. `"failed"` never recovers by polling. For a backup source: edit the deployment
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
  running. Rows usually appear within seconds to a couple of minutes depending on type size.
  Transient Salesforce errors (HTTP 404/timeouts) self-heal on a retry before escalating.
- `browse_metadata` returning `{ status: "retrieval_failed", failed_tasks }` is a retrieval that
  failed on the Salesforce side for part of the type, not an empty type: read
  `failed_tasks[].error` (read timeouts on big Profiles are the classic). The component **names**
  returned are complete — only some bodies may not have been read yet. mtdt re-queues the retrieval
  automatically (up to 3 times): call it again with the same args to get the list, and report the
  error to the user only if the failure keeps repeating.
- Re-browsing an already-retrieved type serves the cached rows; metadata is cached per deployment.

## Auth / access

- **"MFA-enrolled user" refusal at connect time**: the mtdt MCP currently supports non-MFA
  accounts only; the user should connect with a non-MFA account or use the web app.
- **Permission errors on deploy actions**: the user's mtdt role may lack direct-deploy on that
  target — mtdt then forces an approval request; that is policy, not a bug.
- **`reauth_required: true` on an org** (in `list_orgs`): the Salesforce connection needs
  re-authentication in the mtdt web app before any retrieval/deploy against it will work.

## The failure a preflight would have named

Before re-validating blind, run `preflight_deployment` on the same selection — several classic
failures show up there with the fix attached: a scheduled Apex (cron) job on a class you are
overwriting (Salesforce refuses the overwrite until the job is aborted), an Entitlement Process
whose Business Hours is missing on the target (deploys "Successfully" and silently drops the
binding), and destructive changes whose components the target still references.

## Deployment blocked by "another deploy in progress"

mtdt deliberately waits when **any** deployment is already running on the target org (including
ones started outside mtdt). This resolves itself; check the target org's deployment status in
Salesforce Setup if it persists.

When the cause is genuinely unclear, gather `get_deploy_status` output plus the run's component
and test failure lists, summarize them for the user, and suggest inspecting the run in the mtdt
web UI where full logs live.
