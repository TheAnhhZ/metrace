<!--
SPDX-FileCopyrightText: The metrace Authors
SPDX-License-Identifier: Apache-2.0
-->

# Workflows (Flowable)

Only processes that need **timers and people** run in Flowable. The kitchen
flow is a state machine in the API, and incident status is owned by the API.
Only the worker calls Flowable, always through the transactional outbox, so a
Flowable outage delays workflow steps but never blocks the kitchen or a recall.

Files live in `workflows/bpmn/` and are deployed by the worker at start-up.
Deployment is idempotent: the deployment name embeds a hash of the file, so an
unchanged file never creates a new process version.

## incident-recall

```
start ─► [qa_triage] ───────────────► [close_approval] ─► end
            ╎ timer ${triageSla} (non-interrupting)
            └► [director_escalation] ─► end
```

| Step | Who | Completed when |
|---|---|---|
| `qa_triage` | QA | QA confirms suspects (locks applied) |
| `director_escalation` | Director | Shown as a red "escalated" flag on the incident |
| `close_approval` | Approver | Four-eyes close approved (requester ≠ approver) |

Business key `incident:<id>`. Variables: `incidentId`, `triageSla`
(`INCIDENT_TRIAGE_SLA`, default `PT30M`, demo `PT1M`). A reconciler starts the
process for any open incident that lacks one and mirrors the escalation.

## cold-chain-alert

```
start ─► [qa_check_fridge] ─► end
            ╎ timer ${checkSla} (non-interrupting)
            └► [director_escalation] ─► end
```

Started when a fridge reports N consecutive readings outside its band
(one open alert per asset). Business key `coldchain:<alert id>`. Variables:
`assetCode`, `checkSla` (`COLDCHAIN_CHECK_SLA`, default `PT10M`). QA
acknowledging the alert in the app completes `qa_check_fridge`.

## Callbacks

Flowable never calls metrace. The worker acquires external-worker jobs or
polls tasks by business key, so Flowable needs neither the app's URL nor any
credential of it.
