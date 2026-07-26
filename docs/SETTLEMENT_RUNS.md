# Statement settlement runs

Runs are account artifacts numbered `ST-<account>-<n>`.

## State machine

`start_statement_run(account, operation_id)` records a `started` run.
`issue_statement_run(account, operation_id)` starts it when absent, then
advances it to `issued`.

At start, the next run number, caller `operation_id`, predecessor, previous
cutoff, and current cutoff become fixed. The predecessor is the latest issued
run; its cutoff is the previous cutoff. The current cutoff is the greatest
accepted adjustment ordinal, or zero. Only one run may remain started.

The same operation id always returns the same run. An empty run consumes its
number. `crash_after="started"` stops after start; retry completes that same
run. Once issued, every run field remains fixed.

## Membership

A run has one membership entry per correction record whose ordinal k satisfies
`previous cutoff < k <= cutoff`. The entry names the adjustment, ordinal,
issued invoice, and record. A transfer affecting two issued invoices has two
entries. Zero-delta records remain members. Later accepted events wait for the
next run even when effective earlier.

## Projection equations

`billing(k) = issued invoice amounts + record deltas with ordinal <= k`

For run n at cutoff k, with prior issued demand D(n-1), or zero:

`D(n) = billing(k)`

`incremental demand(n) = D(n) - D(n-1)`

`receivable balance = sum incremental demands through n = D(n)`

`Account.amount_due` is the latest issued D(n). Deliveries after its cutoff may
change billing balance but cannot change amount due until another run issues.
Both policy families use these equations.
