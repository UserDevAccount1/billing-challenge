# Architecture

Billing reconciliation is split across:

- `pricing` turns period usage and a rule set into line items and an invoice;
- `adjustments` accepts later business corrections, resolves account state,
  and issues statement runs;
- `statement` builds the customer-facing semantic statement tree.

`PricingEngine.price_period` registers one working invoice per account and
period. `PricingEngine.issue` closes that invoice and records its amount in the
billing projection. The intake service accepts later adjustments, resolves the
affected periods, and records corrections. `AdjustmentIntake.issue_statement_run`
starts or resumes a customer-demand run.

The data model is in memory. Persistence, transport, currency conversion, and
payment collection are owned by surrounding systems.

## Reporting queries (keep these stable)

Finance and partner-operations tooling reads the following surface directly.
Automation depends on these names and meanings, so keep them working whatever
you change internally:

- `Account.settlement_policy` — either `credit_forward` or `restate`; this
  account-level value selects one closed-period policy family for all records.
- `Account.balance` — the billing projection balance: issued invoice amounts
  plus every recorded correction delta.
- `Account.amount_due` — the recorded demand on the latest issued statement
  run, or `0.00` before the first run issues.
- `Account.invoices[period_key]` — the invoice for a period.
- `Account.received_adjustments` — the accepted corrections, one entry per
  accepted adjustment identifier, in acceptance order.
- `Account.acceptance_ordinals[adjustment_id]` — the positive, strictly
  increasing acceptance ordinal assigned to that correction. Accepted
  administrative events (such as a reporting rollout) also consume
  ordinals, so adjustment ordinals are ordered but not necessarily
  contiguous; `Account.summaries_adopted_ordinal` exposes the rollout
  event's ordinal once adopted.
- `Account.adjustment_records` — the finance reconciliation export: one record
  per accepted correction and affected already-issued invoice. Each record
  has `record_id`, `adjustment_id`, `acceptance_ordinal`,
  `original_invoice_id`, `target_period`, the signed `delta`,
  `prior_recorded_total`, `resulting_total`, `policy`, `effective_at`,
  `replaces_adjustment_id`, and `withdraws_adjustment_id`. A
  credit-forward record names `applied_period`; a restate record names
  `replacement_invoice_id`, `void_amount`, and `reissue_amount`.
  `AdjustmentIntake.export_corrections` serializes this list for finance.
- `Account.statement_runs` — statement runs in number order. Each
  `StatementRun` has `run_id`, `account_id`, `run_number`, `operation_id`,
  `predecessor_run_id`, `previous_cutoff_ordinal`, `cutoff_ordinal`, `status`,
  `membership`, `recorded_demand`, and `incremental_demand`.
- `StatementRun.membership` — immutable `RunMembership` entries. Each entry
  names `adjustment_id`, `acceptance_ordinal`, `original_invoice_id`, and
  `record_id`.
- `Account.billing_entries` — recorded issued-invoice and correction amounts
  used by the billing projection.
- `Account.receivable_entries` — one `ReceivableEntry` per issued statement
  run with `run_id`, `predecessor_run_id`, `prior_demand`, `demand`, and
  `incremental_demand`.
- `Invoice.selected_exclusive_promotion` and
  `Invoice.non_selected_exclusive_promotions` — customer support uses these to
  explain which exclusive offer applied and which did not.

An adjustment record's attribution is fixed when the record is committed. Its
`delta` is the adjustment's marginal effect against the resolved state of the
earlier acceptance prefix. Later accepted corrections get their own records
and never redistribute an earlier record.

The exact projection equations and statement-run transitions are published in
`SETTLEMENT_RUNS.md`.

## Operability

Partner delivery is at-least-once and unordered: the same adjustment can arrive
more than once, and corrections can arrive in any order, including after the
period's invoice was issued.

The intake process can stop at any point. For deterministic testing,
`AdjustmentIntake.deliver(..., crash_after=<checkpoint>)` raises
`InjectedCrash` at one of four checkpoints: `accepted`, `resolved`, `applied`,
`posted`. After a stop, the operator's runbook is to restart the process and
re-deliver recent adjustments; the account must end in the same state as an
uninterrupted run.

`AdjustmentIntake.issue_statement_run(account, operation_id,
crash_after="started")` can likewise stop after the run start is recorded.
Retrying that operation resumes the same run.
