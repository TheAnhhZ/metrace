<!--
SPDX-FileCopyrightText: The metrace Authors
SPDX-License-Identifier: Apache-2.0
-->

# Demo guide (15 minutes)

Before starting: `make demo-preflight` (keeps the laptop awake, checks clocks
and health, resets data with the outbreak scenario, warms up). Open one browser
profile per persona and log in. Use device mode: tablet (landscape) for `/ops`,
phone for `/portal`. For a short escalation timer start the stack with
`INCIDENT_TRIAGE_SLA=PT1M COLDCHAIN_CHECK_SLA=PT1M`.

## 1. Kitchen: mistakes are impossible (≈4 min, tablet, `/ops`)

1. **Receiving** as `procurement-mai`: pick *Gia vị DEMO* → blocked, certificate
   expired. Pick *Thủy sản DEMO* → accepted with a yellow "certificate expires in
   10 days" warning. Enter 6 °C for chilled meat → blocked with the threshold and
   its basis.
2. **Cooking** as `chef-hung`: start a batch, add a lot, finish at 70 °C →
   blocked (core temperature); finish at 82 °C → done.
3. **Samples** as `qa-lan`: store 90 g → blocked; 150 g → sealed with a QR code
   and a countdown that cannot be cut short.
4. **Dispatch**: the shipment shows what is missing (Mẫu 3, sample); record the
   check → the truck can leave. Print Mẫu 2 as PDF.

## 2. Incident: from three complaints to every school in seconds (≈5 min)

1. Two schools have already reported children with stomach aches after
   yesterday's lunch. On the phone (`/portal`, `truong-c`) file the third report.
2. As `qa-lan`, the **cluster suggestion** points at yesterday's lunch batches
   reaching 3 delivery points; the broth batch sits behind the soup.
3. Open the incident, look at the **graph**: the bones lot behind the broth was
   also used **today**. Confirm the broth batch with "lock lots": the lock is
   committed in well under a second; today's lunch trucks are **held**, the
   delivery points that already ate get **recall notices**.
4. On the phone, the school sees its notice (only its own) and acknowledges it.
5. Optional: "Soạn nháp" — the report draft (AI or template), QA edits, approves.
6. A dispatch attempt for a held truck is blocked.
7. Close: `qa-lan` requests, `approver-ha` approves (the same person cannot).

## 3. Operating system, not an app (≈3 min)

- Switch the portal to `nha-may-x`: same code, a factory with two shifts and a
  12-hour answer deadline (profile data, not code branches).
- CLI: `metrace trace lot LOT-…-XUONG-LON -d forward`, `metrace shipments list
  --status held`, `metrace drill run lot LOT-…` (dry run, coverage %).
- Cold chain: run the simulator in `breach` mode for the sample fridge → an
  alert opens, lists the retained samples inside, and escalates if nobody acts.
- Tamper evidence: copy the anchor printed on a recall notice or the PDF footer,
  verify it; change one audit row in the database → verification names the seq.

## 4. Close (≈1 min)

Roadmap: health-authority adapter, parents' view, EPCIS/FSMA export.
