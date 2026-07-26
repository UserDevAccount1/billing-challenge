# Statement Run Reconciliation Summary — Specification v1.0

*Attachment referenced from the 2026-07-06 Teams thread. Drafted with an AI
assistant from the manager's requirements.*

## 1. Overview

This specification introduces a per-invoice reconciliation summary recorded
on statement runs, enabling finance to answer "what did run N do to invoice
X" in constant time. The design is additive and changes no pricing behavior
and no projection equation.

## 2. Adoption

Add `adopt_run_summaries(account, adoption_id)` as a method on the
adjustment-intake service, alongside `issue_statement_run`. Adoption is an
accepted event and consumes the account's next acceptance ordinal. A
repeated `adoption_id` is absorbed idempotently; a distinct second adoption
is refused. Runs started after the adoption event's ordinal are in scope;
runs started at or before it are out of scope and carry no summary (their
`reconciliation_summary` stays `None`).

For completeness, adoption SHOULD also be applied retroactively during a
one-time migration: iterate all historical issued runs and backfill their
summaries so the dataset is uniform from day one.

## 3. Summary semantics

On issuance, an in-scope run records an immutable `reconciliation_summary`:
one `RunSummaryEntry` per issued invoice with at least one member record in
the run, ordered by `invoice_id`. Fields: `invoice_id`, `member_count`, and
`member_delta_total` (the sum of that invoice's member-record deltas). An
in-scope run with no members records an empty tuple. The summary is derived
solely from the run's membership as fixed at its cutoff, never from live
account state, and a run-operation retry returns it unchanged.

## 4. Cross-run consistency

Because a correction subject continues to evolve after a run issues, each
issued run's summary MUST be kept reconciled with its invoices' current
position: when a later correction changes an invoice that an earlier issued
run already summarized, the system refreshes that earlier run's entry so
that no two runs ever report the same subject inconsistently.

## 5. Storage and architecture

Summaries SHOULD be persisted in a dedicated normalized summary store keyed
by `(run_id, invoice_id)` with a covering index, behind a repository
interface, to prepare for the anticipated migration off the in-memory model.
The statement-run module SHOULD be refactored into a summary-computation
service and a summary-storage adapter to keep concerns separated.

## 6. Presentation

For discoverability, the statement screen SHOULD surface each run's summary
entries inline as first-class nodes, expanded by default on all viewports.

## 7. Configuration

Introduce configuration flags `summaries.enabled`, `summaries.backfill`, and
`summaries.presentation_mode` (enum: `inline`, `collapsed`, `hidden`) to
allow per-deployment tuning of the above behaviors.

## 8. Compatibility

`recorded_demand`, `incremental_demand`, and both projections are unchanged.
