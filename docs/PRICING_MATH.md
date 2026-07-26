# Pricing arithmetic (normative)

This document is the authoritative definition of period calculations.

## Money and rounding

All money is `decimal.Decimal`, presented to the cent. Rounded values use
half-up to the cent (`ROUND_HALF_UP`). Rounding happens only at named aggregate
steps, never per intermediate multiplication.

## Aggregate-then-allocate

Every shared reduction or charge is computed once at the aggregate level,
rounded there, and allocated so line cents sum exactly to the aggregate:

- Compute each ideal share using the weights named for that step.
- Give each line the floor of its share in cents.
- Distribute remaining cents by descending fractional remainder, breaking ties
  by line key ascending.

Worked example: a 0.05 reduction shared equally by a, b, c allocates 0.02,
0.02, 0.01.

## Pipeline order

For a period:

1. Usage bases use marginal tiers. Round the aggregate and allocate using raw
   line amounts.
2. Promotions combine multiplicatively. Aggregate and allocate their reduction
   using raw per-line reductions.
3. Credits, capped at the remaining subtotal, allocate using post-promotion
   amounts.
4. The lowest cap removes excess, allocated using current amounts.
5. Summed tax rates apply to the post-cap subtotal; allocate using current
   amounts.

## Exclusive promotion selection

Among eligible exclusive promotions, select the offer producing the lowest
final invoice total through the complete pipeline. Ties break by promotion key
ascending. Record the selected and eligible non-selected offers. Rule-list
order has no effect.

## Adjustment lineages and effective order

Every non-withdrawal adjustment names a `subject_key`. When omitted it means
`adjustment:<adjustment_id>`, an independent subject. A subject has one
lineage: one root followed by versions linked through
`replaces_adjustment_id`.

- A replacement parent must already be accepted and have the same account and
  subject.
- A node has at most one replacement child. A subject has at most one root.
- A missing parent is refused. These constraints also prevent cycles.
- Refused deliveries receive no acceptance ordinal or economic effect.

The active version is the first non-withdrawn node found by walking from the
lineage leaf toward its root. A `withdrawal` names
`withdraws_adjustment_id`; it makes that node inactive without removing
accepted history. Withdrawing the active leaf reactivates its nearest
non-withdrawn ancestor. A withdrawal may arrive before its target and remains
effective when the target arrives. Withdrawals cannot target withdrawals.

A period resolves its base state plus the active version of every subject in
ascending `(effective_at, adjustment_id)` order. Arrival order controls
attribution and run membership, not effective-order resolution.

For period P and acceptance cutoff k, let `T(P,k)` be its resolved total using
only ordinals at most k. The correction record for event k is:

`record delta(P,k) = T(P,k) - T(P,k-1)`.

That attribution is fixed when committed. Later events get their own records.

A usage transfer moves one usage quantity from `period_key` to
`target_period_key`. Both periods re-resolve. Each affected issued invoice
gets one linked record for that accepted event.

## Closed periods

`Account.settlement_policy` selects one family for the whole account:

- `credit_forward`: `applied_period` is the earliest open period later than
  the target, or `next-open-period`.
- `restate`: the record names `<original invoice id>-R<n>`, the next closed
  replacement revision. `void_amount` negates the prior recorded total and
  `reissue_amount` is the resulting total.

Issued invoice fields never change. Under both families:

`billing balance = sum(original issued invoice amounts) + sum(record deltas)`.

Replacement documents explain settlement and are not counted again.
