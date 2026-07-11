---
name: mtdt-deploy
description: Promote Salesforce metadata between orgs with mtdt.io. Use when the user asks to deploy, promote, or push Salesforce metadata (Apex classes, flows, fields, objects, permission sets, ...) from one org to another (dev → QA, QA → staging, staging → production), or to validate such a deployment. Covers the full workflow — create deployment, retrieve, select, pre-flight checks, validate, quick-deploy.
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
  `from_backup_id`) and `to_org_id`. Poll `check_deployment_creation_status` until `done`.
- Repo/backup sources arrive pre-populated; org sources need retrieval (step 3).

## 3. Retrieve the metadata you need (org sources only)

- `start_metadata_retrieval` per metadata type on the **source** org, then poll
  `list_retrieved_metadata` until rows appear. Types use Salesforce directory names (`classes`,
  `objects`, `flows`, `fields`, ...) — when unsure, run `resolve_metadata_type` first; it
  autofixes common guesses ("ApexClass" → `classes`) and suggests corrections for typos.

## 4. Select items

- `prepare_deployment_run_selected_items_object` with `{ "type": ["Name1", "Name2"] }`. If it
  returns `unresolved_types`, fix the type names (it tells you the closest matches) and retry —
  it never returns a partial selection.

## 5. Pre-flight checks (read-only; run all three before deploying to shared/prod orgs)

- `run_impact_analysis` — finds source-org dependencies of your selection you likely must add
  (e.g. a field's global value set, a record type's picklist fields). Add the findings to your
  selection or explain to the user why not.
- `check_target_conflicts` — detects whether anything you are about to overwrite changed on the
  target since it was retrieved. Surfaces honest `verifiable` vs `not-verifiable` buckets; treat
  a conflict as a stop-and-ask.
- `recommend_tests` — suggests which Apex tests cover the selection; feed `testsToRun` into the
  run as `test_option: "specific"`.

## 6. Validate, then quick-deploy (the safe path)

- `create_deployment_run` with `validate: true` and a test option that **runs tests**
  (`"local"`, or `"specific"` + `tests_to_run`) — a validation that ran tests is what makes
  quick-deploy possible.
- Poll `get_deploy_status` until `is_terminal`. On success, `quick_deploy` with just the
  `deployment_id` (it auto-derives the validation job) — this performs the **real deployment**
  without re-running tests. Poll `get_deploy_status` again until terminal.
- A direct (non-validate) `create_deployment_run` is acceptable for scratch/dev targets the user
  owns; for anything shared, validate first.

## Guardrails

- **Production / `is_important` targets:** always validate first; never `test_option:
  "NoTestRun"` (Salesforce rejects it on prod anyway); if mtdt forces `request_approval`, tell
  the user an approver must act — do not try to bypass.
- **Coverage:** Salesforce requires ≥75% coverage on the components you deploy. A class with no
  covering test will fail validation with a `codeCoverageWarning` even if it compiles. Fix: deploy
  the class **together with its test class** and run that test (`test_option: "specific"`).
- **Rollback safety:** for risky deploys pass `do_package_backup: true` — it snapshots the target
  pre-deploy so the run can be rolled back from the mtdt UI.
- **Destructive changes** (`destructive_changes`) delete metadata on the target — confirm each
  item with the user explicitly before including it.
- Before deploying, `get_workflow_deployment_recipe` returns the server's current recommended
  recipe if you need a refresher.
