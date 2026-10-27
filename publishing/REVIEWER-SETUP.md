# Reviewer workspace and rehearsal

These are maintainer instructions, excluded from distribution ZIPs. Enter the final private
account and access instructions through the catalog portal. Do not commit credentials,
private tenant identifiers, OAuth tokens, or a filled account handoff to the public repository.

## Prepare an isolated workspace

The reviewer account is a dedicated sign-up whose Personal team holds two scratch orgs labelled
**DEV** (source) and **UAT** (target). Scratch orgs live at most 30 days, so rotate them before
expiry: create them on the local stand with `service-tools/create-scratch.js --admin-email=…`,
seed them with `service-tools/claude-review/seed-scratch-metadata.js <id> dev|base`, set a
password with `service-tools/scratch-set-password.js <id>`, and reconnect them in the reviewer's
team through the normal MTDT UI. Do not include production orgs or actual customer data. For
OpenAI review, use an account that signs in immediately without MFA approval, email/SMS codes
or magic links; do not weaken another team's MFA settings to create it.

The seed deploys a `Project__c` object, `ProjectService`, `ProjectTriggerHandler`, their tests,
a trigger, a custom label and the `Project_Manager` permission set. DEV gets a newer variant
(extra field, picklist value, validation rule, method and label text), so comparison and
deployment from DEV to UAT show real differences. Reseeding UAT with `base` restores it after a
promotion case.

Keep a deployment captioned **Test Deployment** with a successful validation for case 2, a
completed full comparison, and completed metadata backups of both orgs.

## Rehearse the submitted cases

Connect through the actual OpenAI development plugin and Claude custom connector as the
dedicated reviewer. Run the five positive and three negative prompts in `review-cases.json`.
Use a new chat for the read-only-consent case: grant View without Run, check that no run is
created, then restore the full-scope connection for subsequent cases. Do not mistake an agent
refusal for a server permission check; verify both where applicable.

For the promotion case, verify the new class on UAT through Salesforce Setup or an
independent Metadata API retrieve, and inspect its MTDT run result. For backups, follow list_sources
until the backup is usable_as_source. Record the client, date,
fixture labels, case outcomes and independent observations in the `tt` preparation task.

The eight directory cases are a review sample. Claude additionally requires every tool to be
exercised. Use `tool-inventory.json` as the starting list; collect a current tools/list from
the review connection and cover tools outside those eight cases too, including list_sources
(repos, backups, archives), compare_orgs (reuse of the latest comparison and start_new),
request_archive_upload and register_archive, and update_deployment for the caption, description
and test level. Exercise the saved-composition path explicitly: add both classes, remove/re-add
the test class and inspect the result with get_deployment. Run validate_deployment and
execute_deployment with dry_run:true and the intended options before each launch; confirm a dry
run creates no run, and launch by deployment ID.
Creating or editing manual override contents still uses MTDT; existing manual overrides do not
block MCP selection edits and must survive removal/re-add of their component. Exercise low-level
writes only in the isolated review sandboxes. Check prompts/resources and graceful invalid-input/permission failures.

## Supply private access in each portal

Include the account sign-in URL, login credentials, review team name, exact connected org
labels, permissions/plan, seed deployment, backup setup and enough instructions to run the
tools without owner intervention. Keep the account and fixtures available during review and
future update reviews. Verify a fresh browser sign-in, OAuth consent, reconnect and token
refresh. Enter only verified results in testing and policy attestations.
