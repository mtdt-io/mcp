# Reviewer workspace and rehearsal

These are maintainer instructions, excluded from distribution ZIPs. Enter the final private
account and access instructions through the catalog portal. Do not commit credentials,
private tenant identifiers, OAuth tokens, or a filled account handoff to the public repository.

## Prepare an isolated workspace

Create a dedicated MTDT review team with synthetic data and two Salesforce sandboxes or
scratch orgs labelled **Review Source** and **Review Target**. Connect both through the normal
MTDT UI, check their credentials and subscription entitlements, and grant the reviewer the
roles needed for metadata retrieval, validation, deployment and backups. Do not include
production orgs or actual customer data. For OpenAI review, use an account that signs in
immediately without MFA approval, email/SMS codes or magic links; do not weaken another
team's MFA settings to create it.

Seed Review Source with `fixtures/ReviewHello.cls` and `fixtures/ReviewHelloTest.cls` plus
their Metadata API sidecars. Keep Review Target initially without those classes, or restore
it to a known sandbox baseline before a repeat. Run ReviewHelloTest on Review Source and
check that target validation can run the intended local tests. The selected fixtures exercise
deployment without relying on customer fields, flows or business records.

Create a deployment captioned **Review Baseline** through the MTDT UI and complete a validation
with these two classes and local tests. Keep the deployment and successful result available
for case 2. Check that a repeat quick-deploy or fixture reset will not invalidate the seeded
history. Confirm sufficient plan quota and backup storage for a metadata backup of Review
Source before the rehearsal; `run_metadata_backup` takes the org ID and creates a backup task.

## Rehearse the submitted cases

Connect through the actual OpenAI development plugin and Claude custom connector as the
dedicated reviewer. Run the five positive and three negative prompts in `review-cases.json`.
Use a new chat for the read-only-consent case: grant View without Run, check that no run is
created, then restore the full-scope connection for subsequent cases. Do not mistake an agent
refusal for a server permission check; verify both where applicable.

For the promotion case, verify the new class on Review Target through Salesforce Setup or an
independent Metadata API retrieve, and inspect its MTDT run result. For backups, inspect the
terminal task result and confirm the resulting archive is usable. Record the client, date,
fixture labels, case outcomes and independent observations in the `tt` preparation task.

The eight directory cases are a review sample. Claude additionally requires every tool to be
exercised. Use `tool-inventory.json` as the starting list; collect a current tools/list from
the review connection and cover tools outside those eight cases too, including
set_deployment_description, comparison start/status/latest, the low-level run-selection helper,
create_deployment_run and the workflow recipe. Exercise low-level writes only in the isolated
review sandboxes. Check prompts/resources and graceful invalid-input/permission failures.

## Supply private access in each portal

Include the account sign-in URL, login credentials, review team name, exact connected org
labels, permissions/plan, seed deployment, backup setup and enough instructions to run the
tools without owner intervention. Keep the account and fixtures available during review and
future update reviews. Verify a fresh browser sign-in, OAuth consent, reconnect and token
refresh. Enter only verified results in testing and policy attestations.
