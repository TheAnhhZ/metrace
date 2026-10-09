<!--
SPDX-FileCopyrightText: The metrace Authors
SPDX-License-Identifier: Apache-2.0
-->

# Workflows (Flowable)

Only processes that need **timers and people** run in Flowable. The kitchen
flow is a state machine in the API, and incident status is owned by the API.
Only the worker calls Flowable. An API action writes an outbox event in the same
transaction; the worker handles it after commit, so a Flowable outage delays
workflow steps but never blocks the kitchen or a recall.

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
| `qa_triage` | QA | Suspects are confirmed and locked (`incident.suspects_confirmed`) |
| `director_escalation` | Director | Created when the triage SLA passes. Shown as a red "escalated" flag on the incident. Completed when the incident closes |
| `close_approval` | Approver | Completed when the incident closes, i.e. the approver approved the close request (requester ≠ approver, enforced by the API) |

Business key `incident:<id>`. Variables: `incidentId`, `triageSla`
(`INCIDENT_TRIAGE_SLA`, default `PT30M`, demo `PT1M`). A reconciler (every 30 s)
starts the process for any open incident that lacks one and mirrors the escalation.

## cold-chain-alert

```
start ─► [qa_check_fridge] ─► end
            ╎ timer ${checkSla} (non-interrupting)
            └► [director_escalation] ─► end
```

Started when a fridge reports `coldchain_consecutive_n` consecutive readings
outside its safe band (seeded at 3). Readings whose device clock is more than
`coldchain_max_skew_s` (60 s) away from server time are rejected. One open
alert per asset. Business key `coldchain:<alert id>`. Variables: `assetCode`,
`checkSla` (`COLDCHAIN_CHECK_SLA`, default `PT10M`).

QA acknowledging the alert in the app completes `qa_check_fridge` and any open
`director_escalation`.

## Callbacks

Flowable never calls metrace. The worker calls the Flowable REST API to start
processes and to complete tasks, keyed by business key, so Flowable needs
neither the app's URL nor any credential of it.
