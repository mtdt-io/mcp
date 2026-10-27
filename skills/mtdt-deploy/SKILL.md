---
name: mtdt-deploy
description: Promote Salesforce metadata between orgs with mtdt.io. Use when the user asks to deploy, promote, or push Salesforce metadata (Apex classes, flows, fields, objects, permission sets, ...) from one org to another (dev → QA, QA → staging, staging → production), or to validate such a deployment. Covers the full workflow — create deployment, save its component selection, pre-flight checks, preview actions, validate by ID, quick-deploy.
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
  (`list_metadata_backups`). `list_metadata_backups` returns only the backups actually usable as a
  deploy source by default (status done with the archive present), each with a human `label` — pass
  `include_unusable: true` to also see the rest, each carrying an `unusable_reason`.

## 2. Create the deployment (or resume one)

- Resuming rather than starting fresh? `list_deployments` shows the team's existing deployments
  with source/target labels and each one's latest run — reuse its id instead of creating a
  duplicate. Read `get_deployment_components(deployment_id)` before editing a resumed draft: its
  saved composition may already contain components, deletions or overrides configured in the UI.
- `create_deployment` with exactly one source (`from_org_id` / `from_repo_id` /
  `from_backup_id` / `from_archive_id`) and `to_org_id`. It returns the `deploymentId` used below.
  Pass `caption` (short title) and, when you know what you are shipping, `description` — on a
  push-to-git deploy it becomes the git commit message (`set_deployment_description` can change
  it later). A backup source must be **usable** — finished, with its archive present: otherwise
  `create_deployment` returns `{ error: "backup_not_usable", reason }` and creates nothing, so pick
  another backup from `list_metadata_backups` (its default view lists only usable ones) or run
  `run_metadata_backup` first and wait for it to finish.
- **Repo, backup or archive as the source?** The deployment is populated asynchronously — poll
  `check_deployment_creation_status(deployment_id)` until `deploymentStatus` is `"done"` before
  browsing. It reports each side (`source` / `target`) with the population task behind it, so
  `"failed"` comes with `task.error` (a partial or unfinished backup has no archive to unpack; an
  org may need re-auth). A failed deployment does not recover by polling — tell the user the error
  and create a new deployment from a usable source.

## 3. Browse, then save the components

- `browse_metadata` with the `deployment_id` and a metadata type — it retrieves the type from the
  source org on first call and returns one compact row per component. Filter server-side with
  `name_contains`, `modified_since` (ISO date), or `modified_by` (display names).
- If it returns `{ status: "retrieving", partial: true, task_ids }`, the retrieval is still
  running and `components` holds only what has landed so far — **call it again with the same
  args** (safe to repeat; duplicates are impossible). Treat the list as complete only at
  `status: "ready"` (0 components is a valid ready).
- `{ status: "retrieval_failed", failed_tasks: [{ id, status, error }] }` means the retrieval
  failed on the Salesforce side for **part** of that type (large Profiles timing out is the
  classic). The component **names** in `components` are complete — only the bodies of some of them
  may not have been read yet. mtdt re-queues the retrieval automatically (up to 3 times): call
  `browse_metadata` again with the same args to get the list, and report `failed_tasks[].error` to
  the user only if the failure keeps repeating. The type is **not** empty.
- Types are fuzzy-resolved ("ApexClass" → `classes`); an unknown type comes back as a structured
  reject with `did_you_mean` suggestions — fix and retry.
- If the user already told you exactly which components they changed (or you edited the files
  yourself), you still browse once for the type — it both retrieves the metadata and confirms the
  names exist in the org.

Browsing does not change the deployment selection. Save the chosen full components with
`add_deployment_components` (types can be API names such as `ApexClass` or canonical names such as
`classes`):

```json
{"deployment_id": 42, "items": {"ApexClass": ["FooService", "FooService_Test"]}}
```

- Repeat adds are no-ops. `remove_deployment_components` takes the same shape and removes the
  components from the saved selection; it does **not** delete them from Salesforce.
- Read `get_deployment_components(deployment_id)` to confirm the saved composition. Add/remove
  preserve other settings, including saved deletions and overrides. Editing components with
  partial selections, manual overrides or saved deletions requires the MTDT UI for now.
- An archive source automatically selects its contents. After population finishes, inspect the
  saved selection and proceed to pre-flight; there is no need to pass `all_items` at launch.

## 4. Pre-flight checks (read-only; run them before deploying to shared/prod orgs)

- `preflight_deployment` with just `deployment_id` checks the saved composition, including its
  deletions and destructive timing — the same checks a human gets in the Deploy modal:
  destructive-change impact, which profiles/permission sets grant access to the selection
  (plus profile-applicability warnings),
  record-backup recommendations, scheduled Apex (cron) jobs on classes you'd overwrite, Business
  Hours bindings the target would silently drop, and static-analysis findings. Verdicts are
  **advisory** — read them, act on `suggested_action` where present, and tell the user what you
  found. Optional `items` and `destructive_items` let you assess a hypothetical selection;
  they do not save it. Confirm the final saved composition before launching.
- Two checks live as their own tools and take `selected` keyed by canonical type →
  `[{ "base_component": "Name" }]`, e.g. `{ "classes": [{ "base_component": "FooService" }] }`:
  - `run_impact_analysis` — finds source-org dependencies of your selection you likely must add
    (e.g. a field's global value set, a record type's picklist fields). Add the findings to your
    saved selection with `add_deployment_components` or explain to the user why not.
  - `check_target_conflicts` — detects whether anything you are about to overwrite changed on the
    target since it was retrieved. Surfaces honest `verifiable` vs `not-verifiable` buckets; treat
    a conflict as a stop-and-ask.
- `recommend_tests` — suggests which Apex tests cover a selection; feed `tests_to_run` into the
  validation as `test_option: "specific"`. By default it assesses the saved selection; only
  legacy deployments without a saved selection fall back to the latest run. Optional `items`
  (`{ "type": ["Name"] }`) assesses a hypothetical selection without saving it. If the saved
  selection is empty, add the intended components first.

## 5. Preview the run, then validate

Call `preview_deployment_run` before `validate_deployment` or `create_deployment_run`. Use
`deployment_id`, the intended mode, and the same optional execution settings as the actual launch.
For example, preview a validation with specific tests:

```json
{"deployment_id": 42, "validate": true, "test_option": "specific", "tests_to_run": "FooService_Test"}
```

- `validate: true` previews validation; omitted/false previews a direct deployment. Preview uses
  the same parameter preparation as launch. It creates no tasks, saves no settings, and calls
  no Salesforce APIs.
- Read the component counts, deletions, test option, backups and `execution_settings`. Report
  consequential actions to the user before launch: `after_deploy` includes Apex code, git push,
  Flow/AI activation and Flow tests; `scheduled_jobs` lists saved jobs marked for pause/resume.
  Do not assume validation is free of other actions: saved post-deploy Apex and job pauses can
  still execute during validation, and preview explicitly warns about them.
- Read `warnings`. Preview does not refresh saved jobs or prove permissions, approval, source
  readiness or Salesforce success. Flow activation currently re-reads the saved deployment in
  the worker, so its `enabled` value can differ from the per-run `requested` value; the plan
  names that settings source. Change that saved setting in MTDT when necessary.
- The draft can change between preview and launch. Re-preview after editing the draft or
  changing execution options. There is no config or plan token to send back at launch.

- `validate_deployment` needs only `deployment_id`. It snapshots the full saved config,
  including partial selections, manual overrides, deletions and their timing. Do not pass
  `items`, `all_items`, `selected_items` or a replacement `config` at launch.
- Saved execution settings are used unless explicitly overridden for this run. If no saved test
  level exists, validation defaults to `local`. To make quick-deploy possible, use a level that
  **runs tests** (`"local"`, or `"specific"` + `tests_to_run`). Pass `backup: true` for risky
  deploys (pre-deploy snapshot → rollback). These options do not rewrite the saved config.
- `empty_selection` means nothing is saved yet: browse, add components, inspect, then retry.
  `deployment_not_ready` means archive selection is still populating: wait for creation status.
  Other rejects and recovery steps are covered by the `mtdt-troubleshoot` skill.
- Wait with `await_deploy_status(deployment_id)` — one call blocks up to ~50s server-side and
  returns the moment the run is terminal; **while it returns `timed_out: true`, call it again**.
  `is_success` + `is_validation` means the validation passed.

## 6. Quick-deploy (the safe path to a real deployment)

- After a successful validation-with-tests: `quick_deploy` with just the `deployment_id` (it
  auto-derives the validation job) — this performs the **real deployment** without re-running
  tests. Wait with `await_deploy_status` again.

## Advanced / low-level

- Preview a direct deployment with `preview_deployment_run(deployment_id, validate:false)`,
  then use `create_deployment_run` with only `deploy_id` (and optionally
  `validate: false`). It uses the same full saved config as validation. Execution options such as
  test level, post-deploy flow activation, approval requests and record backups remain optional.
  For shared or production targets, validate first.
- Configure partial selections, overrides and deletions in the UI for now. MCP can inspect and
  run that saved composition; it cannot author those settings yet. Confirm intended target
  deletions with the user before launching a draft that contains them.
- `prepare_deployment_run_selected_items_object` is a legacy name normalizer only. It does not
  save anything, and its output is no longer accepted by run tools. Use
  `add_deployment_components` to save components instead.
- `get_workflow_deployment_recipe` returns the server's current recommended recipe if you need a
  refresher.
- `get_task_status(task_id)` is the generic poller for any async task id you get back (backup,
  comparison, retrieval) when there is no dedicated status tool.

## Adjacent intents on the same connection

- **"What differs between these two orgs?"** — create a deployment between them, then
  `start_full_metadata_deployment_comparison(deployment_id)` (returns a `comparisonId`), poll
  `get_full_metadata_deployment_comparison_status(comparison_id)`, and read
  `get_latest_full_metadata_deployment_comparison` — a full org-to-org metadata diff, no
  deploy involved.
- **"Back up the org's metadata"** — `run_metadata_backup(org_id)` starts a backup task; track
  it with `get_task_status(task_id)`. A finished backup also becomes a valid deploy
  *source* (`from_backup_id`) for restores.
- **Record (data) backup before a risky deploy** — when `preflight_deployment` recommends it
  (`record_backups/recommended` verdict), pass the objects as `objects_to_backup` on
  `create_deployment_run`; mtdt snapshots the records before deploying.

## Guardrails

- **Production / `is_important` targets:** always validate first; never `test_option:
  "NoTestRun"` (Salesforce rejects it on prod anyway); if mtdt forces `request_approval`, tell
  the user an approver must act — do not try to bypass.
- **Coverage:** Salesforce requires ≥75% coverage on the components you deploy. A class with no
  covering test will fail validation with a `codeCoverageWarning` even if it compiles. Save the
  class **together with its test class** using `add_deployment_components`, then validate and run
  that test (`test_option: "specific"`).
- **Rollback safety:** for risky deploys pass `backup: true` on `validate_deployment` (or
  `do_package_backup: true` on `create_deployment_run`) — it snapshots the target pre-deploy so
  the run can be rolled back from the mtdt UI.
