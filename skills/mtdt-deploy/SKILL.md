---
name: mtdt-deploy
description: Promote Salesforce metadata between orgs with mtdt.io. Use when the user asks to deploy, promote, or push Salesforce metadata (Apex classes, flows, fields, objects, permission sets, ...) from one org to another (dev → QA, QA → staging, staging → production), or to validate such a deployment. Covers the full workflow — create deployment, browse & pick components, pre-flight checks, validate, quick-deploy.
---

# Deploying Salesforce metadata with mtdt

You have the `mtdt` MCP server connected. It promotes metadata between the Salesforce orgs
connected to the user's mtdt.io team. Follow this workflow; do not skip pre-flights on shared or
production targets.

## 1. Resolve the target (and source)

- `list_orgs` to see connected orgs, or `resolve_target` with the user's free-text name ("QA",
  "acme prod"). **Never assume the top hit** — confirm with the user, especially when a candidate
  has `org_type: production` or `is_important: true`.
- Source can be an org, a git repo (`list_git_repos`), or a metadata backup
  (`list_metadata_backups`).

## 2. Create the deployment

- `create_deployment` with exactly one source (`from_org_id` / `from_repo_id` /
  `from_backup_id`) and `to_org_id`. It returns the `deploymentId` you use everywhere below.

## 3. Browse & pick components

- `browse_metadata` with the `deployment_id` and a metadata type — it retrieves the type from the
  source org on first call and returns one compact row per component. Filter server-side with
  `name_contains`, `modified_since` (ISO date), or `modified_by` (display names).
- If it returns `{ status: "retrieving", timed_out: true }`, the retrieval is still running —
  **call it again with the same args** (safe to repeat; duplicates are impossible).
- Types are fuzzy-resolved ("ApexClass" → `classes`); an unknown type comes back as a structured
  reject with `did_you_mean` suggestions — fix and retry.
- If the user already told you exactly which components they changed (or you edited the files
  yourself), you still browse once for the type — it both retrieves the metadata and confirms the
  names exist in the org.

## 4. Pre-flight checks (read-only; run all three before deploying to shared/prod orgs)

These take a `selected` object keyed by canonical type → `[{ "base_component": "Name" }]`, e.g.
`{ "classes": [{ "base_component": "FooService" }] }`.

- `run_impact_analysis` — finds source-org dependencies of your selection you likely must add
  (e.g. a field's global value set, a record type's picklist fields). Add the findings to your
  selection or explain to the user why not.
- `check_target_conflicts` — detects whether anything you are about to overwrite changed on the
  target since it was retrieved. Surfaces honest `verifiable` vs `not-verifiable` buckets; treat
  a conflict as a stop-and-ask.
- `recommend_tests` — suggests which Apex tests cover the selection; feed `tests_to_run` into the
  validation as `test_option: "specific"`.

## 5. Validate

- `validate_deployment` with `deployment_id`, `items` as `{ "type": ["Name1", "Name2"] }` (loose
  type names are fine — they are fuzzy-resolved), and a `test_option` that **runs tests**
  (`"local"`, or `"specific"` + `tests_to_run`) — a validation that ran tests is what makes
  quick-deploy possible. Pass `backup: true` for risky deploys (pre-deploy snapshot → rollback).
- If it returns `items_not_retrieved`, a named component was never retrieved — run
  `browse_metadata` for that type first and check the spelling against its rows.
- Wait with `await_deploy_status(deployment_id)` — one call blocks up to ~50s server-side and
  returns the moment the run is terminal; **while it returns `timed_out: true`, call it again**.
  `is_success` + `is_validation` means the validation passed.

## 6. Quick-deploy (the safe path to a real deployment)

- After a successful validation-with-tests: `quick_deploy` with just the `deployment_id` (it
  auto-derives the validation job) — this performs the **real deployment** without re-running
  tests. Wait with `await_deploy_status` again.

## Advanced / low-level

- Direct (non-validate) deploy, destructive changes (`destructive_changes` — deletes metadata on
  the target; confirm each item with the user explicitly), post-deploy flow activation, and
  record backups go through the low-level `create_deployment_run`. For anything shared, validate
  first.
- `prepare_deployment_run_selected_items_object` still exists to build the `selected_items`
  object for `create_deployment_run` by hand, but `browse_metadata` + `validate_deployment`
  cover the normal flow in two calls.
- `get_workflow_deployment_recipe` returns the server's current recommended recipe if you need a
  refresher.

## Guardrails

- **Production / `is_important` targets:** always validate first; never `test_option:
  "NoTestRun"` (Salesforce rejects it on prod anyway); if mtdt forces `request_approval`, tell
  the user an approver must act — do not try to bypass.
- **Coverage:** Salesforce requires ≥75% coverage on the components you deploy. A class with no
  covering test will fail validation with a `codeCoverageWarning` even if it compiles. Fix: deploy
  the class **together with its test class** and run that test (`test_option: "specific"`).
- **Rollback safety:** for risky deploys pass `backup: true` on `validate_deployment` (or
  `do_package_backup: true` on `create_deployment_run`) — it snapshots the target pre-deploy so
  the run can be rolled back from the mtdt UI.
