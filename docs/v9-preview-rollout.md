# Additive v9 preview rollout — operator approval required

This is deployment preparation, not a language-acceptance claim. V9 is eligible
for an additive preview/dark release, **not production-default activation**.
Production Admin must continue selecting `legacy` (including its documented default).
No Admin configuration change, deployment or restart is part of this rollout.
Historical acceptance failures remain in the [live report](v9-live-report.md).
There is no successful Full455 claim for the current candidate.

## Reviewed state and compatibility caveat

- Reviewed implementation/report head: `ac49816cdbaf89e7078919af4e6427dd6b55170a`.
- Fetched main and deployed Planner: `2710c57c228bac954ad3acb51a9473ced9119bff`.
- Main is already an ancestor. `git rebase origin/main` reports up to date;
  GitHub reports CLEAN/MERGEABLE. There is no conflict to resolve or history to rewrite.
- `/plan` (schema v3/prompt v7), `/v4/plan`, `/v5/plan` (v5/v10) and
  `/v6/plan` (v6/v11) keep their existing schemas, prompts and handlers.
- `/v9/plan` is additive, authenticated, and does not redirect legacy paths.
- **The full PR is not an unchanged-v7 rollout compared with deployed main.**
  Earlier reviewed work in this PR changes `/v7/plan` from prompt v12 to v13,
  adds its canonical output adapter and corrects local-clock JSON Schema annotations.
  The v7 freeze protects the subsequent v9 addition, not the entire PR against main.
  Operator approval must acknowledge these pre-existing v7 changes. If unchanged
  deployed v7 behavior is mandatory, do not merge this whole PR: a separately reviewed
  release split is required. No v7/v9 production code is changed during rollout prep.

Exactly two v9 Golden overrides are approved: seasonal event_type × month, and
source-update ranking with no substitute metric. All other cases project v7 grouping.
The most recent focused candidate had 29 pass / 13 mismatch / 0 invalid / 0 provider;
knowledge and category-distribution controls regressed. This remains unacceptable as
the Admin default. The preview decision does not change these observations.

## Read-only production inspection

Planner host: `awendelk@89.58.44.151`.
Checkout `/opt/uranus-research-planner` is clean, on main at the SHA above.
`uranus-research-planner.service` is active and uses the **OpenAI/Terra variant**,
provider=openai, listener 127.0.0.1:8090. Its installed unit additionally contains
`Environment=UV_CACHE_DIR=/var/cache/uranus-research-planner`; preserve that unit.
No unit replacement or daemon-reload is needed for this code-only rollout.
The protected `/etc/research-planner/planner.env` is preserved; no contents are printed.

Admin was inspected via the configured SSH alias `webserver`:
active release `8a3868c3b1f26dd791190e9cc2e34529742b836e`.
The selector is absent from `/etc/uranus-admin/runtime.env` and the running backend
process; no checkout `.env` or unit drop-in supplies another value. The deployed
`backend/app/config.py:103` explicitly defaults `research_planner_contract` to `legacy`.
Thus production Admin remains legacy. All these Admin operations were read-only.

## After explicit approval only: merge and pin target

Replace the approved-head placeholder with the exact head in the final operator
approval. The future merge commit cannot be known before the merge. Do not substitute
a hypothetical SHA. Recheck head, base and completed checks before executing.
If main or the approved implementation changed, stop for review.

```bash
APPROVED_HEAD='<exact approved PR head>'
gh pr view 20 --repo sndcds/uranus-research-planner \
  --json headRefOid,baseRefOid,mergeable,statusCheckRollup,isDraft
# Only after the v7 caveat and rollout are approved, if still Draft:
gh pr ready 20 --repo sndcds/uranus-research-planner
gh pr merge 20 --repo sndcds/uranus-research-planner \
  --merge --match-head-commit "$APPROVED_HEAD"
MERGED_TARGET=$(gh pr view 20 --repo sndcds/uranus-research-planner \
  --json mergeCommit --jq '.mergeCommit.oid')
```

Record MERGED_TARGET beside the rollback SHA before updating production. Confirm
that it contains the approved PR head and reviewed base. No other PR is merged.

## Planner-only update

```bash
ssh awendelk@89.58.44.151 sudo -n bash -s -- "$MERGED_TARGET" <<'REMOTE'
set -euo pipefail
set +x
target="$1"
[[ "$target" =~ ^[0-9a-f]{40}$ ]]
cd /opt/uranus-research-planner
test -z "$(sudo -u research-planner git status --porcelain=v1)"
test "$(sudo -u research-planner git rev-parse HEAD)" = \
  2710c57c228bac954ad3acb51a9473ced9119bff
sudo -u research-planner git fetch origin
sudo -u research-planner git merge-base --is-ancestor "$target" origin/main
sudo -u research-planner git checkout main
sudo -u research-planner git merge --ff-only "$target"
test "$(sudo -u research-planner git rev-parse HEAD)" = "$target"
sudo -u research-planner env \
  UV_CACHE_DIR=/var/cache/uranus-research-planner UV_LINK_MODE=copy \
  /usr/local/bin/uv sync --locked --no-dev
# Existing unit and planner.env are not modified: no daemon-reload.
systemctl restart uranus-research-planner.service
systemctl status uranus-research-planner.service --no-pager -l --lines=0
REMOTE
```

Do not discard unexpected checkout changes. If dependency synchronization, restart
or required smoke validation fails, execute the rollback below and report the failure.
Do not retry interpretation or tune the model during deployment.

## Authenticated smoke verification

On the Planner host, use a root shell with tracing disabled to load the existing env.
Only the synthetic smoke response is printed, not configuration or request headers.
Run each plan request once; a smoke success does not establish corpus acceptance.

```bash
sudo bash
set +x
set -euo pipefail
set -a
. /etc/research-planner/planner.env
set +a
curl --fail -sS http://127.0.0.1:8090/health | jq -e '.status == "ok"'
curl --fail -sS -H "Authorization: Bearer $RESEARCH_PLANNER_SERVICE_API_KEY" \
  http://127.0.0.1:8090/ready | jq -e '.status == "ready"'

curl --fail -sS -H "Authorization: Bearer $RESEARCH_PLANNER_SERVICE_API_KEY" \
  -H 'Content-Type: application/json' http://127.0.0.1:8090/plan \
  -d '{"query":"Was ist heute Abend in Flensburg kulturell interessant?","timezone":"Europe/Berlin","language":"de"}' \
  | jq -e 'select(.schema_version == "research-query-plan-v3" and .prompt_version == "research-planner-v7")'

curl --fail -sS -H "Authorization: Bearer $RESEARCH_PLANNER_SERVICE_API_KEY" \
  -H 'Content-Type: application/json' http://127.0.0.1:8090/v6/plan \
  -d '{"query":"Was ist heute in der Bachstraße Flensburg los?","timezone":"Europe/Berlin","language":"de"}' \
  | jq -e 'select(.schema_version == "research-query-plan-v6" and .prompt_version == "research-planner-v11")'

curl --fail -sS -H "Authorization: Bearer $RESEARCH_PLANNER_SERVICE_API_KEY" \
  -H 'Content-Type: application/json' http://127.0.0.1:8090/v9/plan \
  -d '{"query":"Welche Veranstaltungstypen treten saisonal besonders stark auf?","timezone":"Europe/Berlin","language":"de"}' \
  | jq -e 'select(.schema_version == "research-query-plan-v9" and .prompt_version == "research-planner-v15" and .plan.intent == "aggregate" and .plan.entity_type == "event" and .plan.metric.operation == "occurrence_count" and .plan.group_by == ["event_type","month"] and .plan.clarification == "none" and .plan.unsupported_reason == null)'
exit
```

Also validate captured JSON using the deployed Pydantic response models and exact
original_query; HTTP success or jq field matches alone are not complete wire validation.
Recheck Admin's selector read-only after smoke verification. Do not edit its runtime.env
or restart any Admin service. Keep secrets out of command tracing, saved transcripts
and process diagnostics; never dump environment or provider headers.

## Rollback: previous Planner only

Run only after a failed approved deployment, and only with a clean checkout.
The recorded previous revision is the rollback target; do not change Admin.

```bash
ssh awendelk@89.58.44.151 sudo -n bash -s <<'REMOTE'
set -euo pipefail
set +x
cd /opt/uranus-research-planner
test -z "$(sudo -u research-planner git status --porcelain=v1)"
sudo -u research-planner git checkout --detach \
  2710c57c228bac954ad3acb51a9473ced9119bff
sudo -u research-planner env \
  UV_CACHE_DIR=/var/cache/uranus-research-planner UV_LINK_MODE=copy \
  /usr/local/bin/uv sync --locked --no-dev
systemctl restart uranus-research-planner.service
systemctl status uranus-research-planner.service --no-pager -l --lines=0
REMOTE
```

Then repeat health, readiness, `/plan` and `/v6/plan` checks above. V9 availability
is not expected on the rolled-back revision. The existing unit/env stay untouched.
