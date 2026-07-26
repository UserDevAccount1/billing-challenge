# Billing contracts

The following product outcomes govern reconciliation. The calculation rules
themselves are normatively defined in `PRICING_MATH.md`.

- An issued invoice is a stable business artifact. Later corrections remain
  separately attributable to that invoice.
- The account balance equals issued invoice amounts plus the marginal records
  produced by the resolved active adjustment lineages.
- An accepted adjustment identifier has one stable economic meaning. Receipt
  timestamps are transport facts, while different identifiers may represent
  separate corrections even when their other fields match.
- An eligible exclusive promotion is selected by the lowest final
  customer-payable amount produced by the complete period pipeline. The
  selected offer and eligible non-selected candidates remain explainable.
- A correction that spans two periods affects both: every affected issued
  invoice stays stable and gains its own separately attributable correction,
  and the whole move nets exactly once.
- After an interruption and re-delivery, the account must agree with an
  uninterrupted processing of the same corrections, and the balance must
  reconcile with the issued invoices plus the recorded corrections.
- A statement run records which corrections it settles and the demand it made.
  Corrections accepted after its cutoff wait for a later run; they cannot
  alter a demand that has already issued.
- A customer reading the statement can tie what they owe now to what was
  billed and demanded: corrections to an issued invoice, their run status, and
  the latest issued run are visible facts on the statement.

These are outcome contracts. The closed-period settlement policy and the
internal representation used to satisfy them are engineering decisions that
must be applied consistently and defended.
