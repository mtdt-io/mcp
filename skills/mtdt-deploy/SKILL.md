---
name: mtdt-deploy
description: Promote Salesforce metadata between orgs with mtdt.io. Use when the user asks to deploy, promote, or push Salesforce metadata (Apex classes, flows, fields, objects, permission sets, ...) from one org to another (dev → QA, QA → staging, staging → production), or to validate such a deployment. Also use for creating and editing Work Items, archiving/restoring cards, creating linked deployments, linking/unlinking existing deployments, and reading project environments, groups and delivery status. Covers the full workflow — create deployment, save its component selection, pre-flight checks, dry-run actions, validate by ID, then deploy for real (quick deploy when eligible).
---

# Deploying Salesforce metadata with mtdt

You have the `mtdt` MCP server connected. It promotes metadata between the Salesforce orgs
connected to the user's mtdt.io team. Follow this workflow; do not skip pre-flights on shared or
production targets.

## Work Items, deployments and runs

| Entity | Purpose | ID used by MCP |
|---|---|---|
| Work Item | A project change: a manual card or a tracker ticket. Tracks its delivery along the environment chain. | `work_item_id` (UUID), with explicit `project_id` |
| Deployment | A reusable source→target draft containing saved components, overrides, deletions and execution settings. | `deployment_id` (number); `create_deployment` and `get_deployment` return it as `deployment_id` (`create_deployment` also as `deploymentId`) |
| Run | One attempt to validate or deploy a snapshot of the saved draft. The same deployment can have many runs and outcomes. | Launch returns `task_id` for asynchronous execution; poll deployment status using the deployment ID, never substitute the task ID |

A card can link to several deployments, and a deployment can serve several cards. These
associations let recorded runs contribute to delivery status; sharing a deployment does not
create a group. A group has a separate master and shared group deployment.

Creating a draft, editing its composition or changing a card association does not start a run.
Save and inspect the composition, dry-run the run, then validate/deploy by deployment ID.
A validation checks the package; it is not delivery. Unlinking does not undo changes in Salesforce.

## Read projects and Work Items

For status questions, use this read-only route without creating or running a deployment:

1. `list_projects({"team_id":"<optional-team-uuid>"})` discovers project IDs. Omit `team_id`
   to read all visible projects. Identify the requested project and pass its ID explicitly on
   every project-scoped call, even if only one project exists. There is no automatic or saved
   current project.
2. `list_project_environments({"project_id":"<project-uuid>"})` returns the ordered environment
   chain with names, kinds, positions and Salesforce org IDs. `work_items_ready` describes whether
   at least two environments exist; existing cards can still be read in an unconfigured project.
3. `list_work_items({"project_id":"<project-uuid>"})` returns every non-archived card in that
   project, without a hidden limit. Use `status:"archived"` or `status:"all"` explicitly for archives.
4. `get_work_item({"project_id":"<project-uuid>","work_item_id":"<item-uuid>"})` reads one card,
   its tracker reference, active group/master context and delivery history. Both IDs are required.

Report `delivery.reached_environment` as confirmed historical delivery. `current_environment`
may instead be the first working environment when nothing has reached an environment yet.
`validated_into` is checked, not deployed. Rollback keeps the UI's historical presence and adds a
`rolledBack` marker; it does not prove that the package survives or can be promoted. `next_environment`
and `readiness_hint` are informative; they do not authorize promotion. Linked deployments and their
latest run/validation outcomes appear in `delivery.deployments`.

For a group participant, its own `delivery` and the master's `group_delivery` are separate; use
`based_on_work_item_id` to identify whose history is being described. Group IDs, master ID, state
and deployment ID come from the active group context. Do not describe the master's deployment as
an independent deployment of each participant.

If a project/item is not found, check the explicit IDs and access; do not switch projects automatically.

## Create and maintain Work Items

- Create manual work with `create_work_item({"project_id":"<project-uuid>","caption":"Billing change","description":"Optional context"})`.
  For a tracker ticket use `provider` (`jira`, `clickup`, `asana`, `azure_devops`) and `external_id`
  instead of caption/description. The server reads the ticket's text. Existing tickets return
  `created:false` without rewriting the card, reopening it or moving projects. A ticket in another
  project returns `ticket_project_mismatch`; use that project explicitly.
- Only creation needs two configured environments (`project_setup_required`). Existing-card edits,
  restore and deployment links remain available when a project's chain is incomplete.
- `update_work_item` requires project and item IDs and accepts only changed `caption`/`description`;
  `description:null` clears the description. Ticket-linked text rejects with `tracker_fields_readonly`.
  To detach the ticket, send `unlink_ticket:true` alone, then edit in a separate call. The current
  text is retained. Use `force:true` only when the user deliberately requests an override; it does
  not grant permissions, and a later tracker sync can replace the text.
- `archive_work_item` and `unarchive_work_item` are separate status actions. Repeating the same
  status is a no-op; archiving neither deletes the card nor detaches deployments. An active group
  returns `group_operation_required`: leave the group explicitly in the UI first.
- Manual creation is not idempotent. After an uncertain response, inspect `list_work_items` before
  repeating it. Mutation tools require Run (`mtdt:deploy`) consent and the user's edit permission.
- To create a deployment for existing cards, pass both `project_id` and `work_item_ids` to
  `create_deployment` alongside its normal source/target. All cards must be open and in that project
  and team. Creation and linking happen in one MCP call; the chosen source can still be local files,
  org, repo or backup. The environment chain does not replace the requested source.
- If creation returns `work_item_link_failed`, the returned `deploymentId` already exists.
  `linked_work_item_ids` are confirmed; `unconfirmed_work_item_ids` need inspection (a network error
  may hide a committed link). Do not repeat creation. Inspect that deployment and the cards first;
  use `link_work_item_deployment` for intended missing associations, or correct them in the UI.
- Use the UI for editing group membership; promotion of an existing group is supported through
  its master as described below.

## Link or unlink an existing deployment

Use `list_deployments` to find the existing draft and `get_work_item` to inspect the card and its
current links. Both tools below require all three IDs; the server handles the product RPC's link snapshot.

```json
{"project_id":"<project-uuid>","work_item_id":"<item-uuid>","deployment_id":42}
```

- `link_work_item_deployment` attaches that deployment to an open card. Restore an archived card
  explicitly first. The deployment must be visible in the same team; an org comparison is not a
  deployment. A group assembly belongs to its master, so an invalid attachment returns
  `group_operation_required`.
- `unlink_work_item_deployment` removes only that card's association; it also works on archived
  cards. It does not delete the deployment, change its saved config, cancel a run or roll back
  Salesforce. A locked group returns `group_operation_required`; use **Unlink deployment from
  group** in MTDT UI. Do not detach members or unlock a group as an automatic fallback.
- Both return `linked` and `changed`; repeating the same operation is a no-op (`changed:false`).
  `work_item_links_changed` means refresh the card/deployment links and confirm the intended
  operation again, without blind retry. `work_item_link_superseded` means the historical carrier
  was replaced; inspect the current deployment instead of reattaching that carrier.
- Inspect `get_work_item` after either operation. Linking a deployment that already has successful
  runs can immediately change the card's displayed delivery state; unlinking removes that link's
  contribution. Neither call deploys metadata or creates a group.

## Promote a Work Item to the next project environment

Use this path when the change has already reached an environment and should move onward.
For the initial deployment, use `create_deployment` with the card IDs instead.

1. Read the card with `get_work_item` and the chain with `list_project_environments`. Pass
   `project_id`, `work_item_id` and the environment **from which** to promote:

   ```json
   {"project_id":"<project-uuid>","work_item_id":"<item-uuid>","from_environment_id":"<environment-uuid>"}
   ```

   `preview_work_item_promotion` calls the same read-only operation as the MTDT Promote dialog.
   The product derives the next environment and donors from their delivered runs. It returns
   `verdict`, pending/blocking deployments, existing `carriers`, the **full** `fold` (components,
   smart overrides and deletions), delta options, `scope_fingerprint` and optional `stack` context.
   A green card alone does not prove readiness. Preview does not create a draft or start a run.
2. Review the verdict: `not_ready` needs its pending work resolved; `reopen` means open/reuse the
   existing carrier; `already_promoted` means this hop is complete. Read any `blocker` and donor
   reasons. If a full or delta creation is offered, explain the target, composition and deletions.
3. Call `create_work_item_promotion` with the same three IDs and unchanged `scope_fingerprint`:

   ```json
   {"project_id":"<project-uuid>","work_item_id":"<item-uuid>","from_environment_id":"<environment-uuid>","scope_fingerprint":"<preview.scope_fingerprint>"}
   ```

   Optional `caption` names the draft. `mode` defaults to `full`; `delta` requires
   `delta_allowed:true` and selects only the calculated difference from the preview's full fold.
   For replacement in full mode, pass explicitly reviewed open carrier IDs as `supersede` using
   `preview.supersedable`; do not silently choose replacements. Delivered carriers cannot be
   replaced, and delta cannot replace the carrier whose contents it subtracts.
4. For an existing group use its master, pass `stack_version: preview.stack.version` and full
   mode without `supersede`. The product assembles the participants into one group deployment
   and locks the group as in the UI; this is distinct from an ordinary card/deployment link.
5. `scope_changed` or `stack_changed` requires a fresh preview and another review; do not silently
   retry with a replacement fingerprint/version. Other product refusals retain their code and
   details. Creating is not idempotent: after an uncertain response, inspect the card's carriers
   before repeating it.
6. Success returns `deployment_id` (also the original product `id`), `to_environment_id` and
   `mode`. If `supersede_failed` is present, the new draft exists but replacing some old carriers
   failed: keep the returned ID and inspect/correct the state in MTDT, rather than creating again.
   The product can link other cards that share donor content. Inspect resulting links; creation
   retains the product's existing best-effort link handling rather than promising an atomic batch.
7. This creates a **draft only**. Read `get_deployment`, inspect the saved composition,
   and call `validate_deployment` / `execute_deployment` with `dry_run: true` before running them
   by ID as usual. Promotion preview describes the assembled composition; a dry run describes the
   execution settings.

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
  duplicate. Read `get_deployment(deployment_id)` before editing a resumed draft: its saved
  composition may already contain components, deletions or partial selections configured in the UI,
  and it shows the saved test level, linked Work Items and recent runs.
- `create_deployment` with exactly one source (`from_org_id` / `from_repo_id` /
  `from_backup_id` / `from_archive_id`) and `to_org_id`. For Work Items include `project_id` and
  `work_item_ids` in this call. It returns the same card as `get_deployment`, with the
  `deployment_id` used below; check for an error first.
  Pass `caption` (short title) and, when you know what you are shipping, `description` — on a
  push-to-git deploy it becomes the git commit message (`set_deployment_description` can change
  it later). A backup source must be **usable** — finished, with its archive present: otherwise
  `create_deployment` returns `{ error: "backup_not_usable", reason }` and creates nothing, so pick
  another backup from `list_metadata_backups` (its default view lists only usable ones) or run
  `run_metadata_backup` first and wait for it to finish.
- **Repo, backup or archive as the source?** The deployment is populated asynchronously — call
  `get_deployment(deployment_id)` every ~15s until `ready` is `true` before browsing or validating;
  a repo, backup or archive side can take several minutes. Each side (`source` / `target`) carries
  its `readiness` and the population task behind it, so `"failed"` comes with `task.error` (a
  partial or unfinished backup has no archive to unpack; an org may need re-auth). A failed side
  does not recover by polling — tell the user the error and create a new deployment from a usable
  source.

## 3. Browse, then save the components

- `browse_metadata` with the `deployment_id` and a metadata type — it retrieves the type from the
  source org on first call and returns one compact row per component. Filter server-side with
  `name_contains`, `modified_since` (ISO date), or `modified_by` (display names).
- If it returns `{ status: "retrieving", partial: true, task_ids }`, the retrieval is still
  running and `components` holds only what has landed so far — **call it again with the same
  args** (safe to repeat; duplicates are impossible).
- `{ status: "names_ready", task_ids }` means every component **name** of the type is listed
  while Salesforce is still reading the contents. The list is complete: pick and save components
  now instead of polling. A validation started before the contents arrive reads them itself.
- Treat the list as complete only at `status: "names_ready"` or `"ready"` (0 components is a
  valid ready).
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
- Saving follows the UI's last-save-wins model; there is no concurrent-edit check.
- Read `get_deployment(deployment_id)` to confirm the saved composition. Add/remove
  preserve other settings, including saved deletions and overrides. Manual overrides created in
  the UI do not block selection edits, including removing/re-adding their own component. Removing
  a component keeps its override saved; re-adding it reuses that override. Edit override contents,
  partial selections or deletion intent in the MTDT UI for now.
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

## 5. Dry-run the validation, then validate

Call `validate_deployment` with `dry_run: true` first, with `deployment_id` and the same optional
execution settings as the actual launch. For example, a validation with specific tests:

```json
{"deployment_id": 42, "dry_run": true, "test_option": "specific", "tests_to_run": "FooService_Test"}
```

- A dry run uses the same parameter preparation as launch. It creates no tasks, saves no
  settings, does not touch view history and calls no Salesforce APIs.
- Read the component counts, deletions, test option, backups and `execution_settings`. Report
  consequential actions to the user before launch: `after_deploy` includes Apex code, git push,
  Flow/AI activation and Flow tests; `scheduled_jobs` lists saved jobs marked for pause/resume.
  Do not assume validation is free of other actions: saved post-deploy Apex and job pauses can
  still execute during validation, and the dry run explicitly warns about them.
- Read `warnings` and `would_refuse`. A dry run does not refresh saved jobs or prove permissions,
  approval, source readiness or Salesforce success. Flow activation and its exclusions are
  controlled only by the saved deployment config in MTDT; the dry run shows that current setting.
  The run tools do not accept `activate_flows_after_deploy`. Change the saved setting when
  necessary, then dry-run again.
- The draft can change between the dry run and launch. Dry-run again after editing the draft or
  changing execution options. There is no config or plan token to send back at launch.

- `validate_deployment` needs only `deployment_id`. It snapshots the full saved config,
  including partial selections, manual overrides, deletions and their timing. Do not pass
  `items`, `all_items`, `selected_items` or a replacement `config` at launch.
- Saved execution settings are used unless explicitly overridden for this run. If no saved test
  level exists, validation defaults to `local`. To make quick-deploy possible, use a level that
  **runs tests** (`"local"`, or `"specific"` + `tests_to_run`). Pass `backup: true` for risky
  deploys (pre-deploy snapshot → rollback). These options do not rewrite the saved config.
- `empty_selection` means nothing is saved yet: browse, add components, inspect, then retry.
  `run_in_progress` means a run of this deployment is still queued, running, finishing or
  waiting: follow `run` with `get_deployment_run` instead of starting another one.
  `deployment_not_ready` means archive selection is still populating: wait until `get_deployment` reports `ready`.
  Other rejects and recovery steps are covered by the `mtdt-troubleshoot` skill.
- The launch returns `{ run_id, task_id, state, outcome }` right away. Follow it with
  `get_deployment_run(deployment_id)`: it answers immediately, so **call it every 15–30 s while
  `state` is `queued`, `running` or `finishing`**, never faster. `succeeded`, `failed` and
  `cancelled` are final. When `state` is `waiting` (`waiting_for: "approval"` — an approver must
  act in mtdt; `"schedule"` — it starts at `scheduled_at`), **stop polling and tell the user**.
  A succeeded validation carries `quick_deploy_eligible`; when it is `false`,
  `quick_deploy_ineligible_reason` says why.

## 6. Deploy for real with `execute_deployment`

- Only on an **explicit user instruction**, after confirming the target org with the user.
  Call `execute_deployment` with `dry_run: true` first and show the plan.
- mtdt chooses the mode. When the latest validation succeeded, ran tests, is younger than 10 days
  and the saved composition has not changed since (`get_deployment_run` shows
  `quick_deploy_eligible: true`), it **quick-deploys** that validation without re-running tests
  (`mode: "quick_deploy"`). Otherwise it runs a **full deploy** of the saved config with the saved
  or passed test level (`mode: "full_deploy"`), and `quick_deploy_skipped_reason` says why.
  `use_quick_deploy: false`, `backup: true` or `objects_to_backup` force a full deploy.
- Approval works like the Deploy button in the web app: without the right to deploy to this
  target directly but with the right to request approval, the run is created waiting for an
  approver (`state: "waiting"`, `waiting_for: "approval"`) — tell the user. With neither right
  it answers `permission_denied`.
- `scheduled_at` defers a quick deploy only; a full deploy answers `scheduling_not_supported`.
- Follow the run with `get_deployment_run` the same way as a validation.

## Advanced / low-level

- A direct deploy without a fresh validation is `execute_deployment` with
  `use_quick_deploy: false` (dry-run it first). It uses the same full saved config as validation.
  Execution options such as test level, approval requests and record backups remain optional.
  Flow activation is taken from the saved deployment config. For shared or production targets,
  validate first.
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
  `execute_deployment`; mtdt snapshots the records before deploying (this forces a full deploy).

## Guardrails

- **Production / `is_important` targets:** always validate first; never `test_option:
  "NoTestRun"` (Salesforce rejects it on prod anyway); if mtdt forces `request_approval`, tell
  the user an approver must act — do not try to bypass.
- **Coverage:** Salesforce requires ≥75% coverage on the components you deploy. A class with no
  covering test will fail validation with a `codeCoverageWarning` even if it compiles. Save the
  class **together with its test class** using `add_deployment_components`, then validate and run
  that test (`test_option: "specific"`).
- **Rollback safety:** for risky deploys pass `backup: true` on `execute_deployment` — it
  snapshots the target pre-deploy so the run can be rolled back from the mtdt UI (a quick deploy
  takes no backup, so this forces a full deploy).
