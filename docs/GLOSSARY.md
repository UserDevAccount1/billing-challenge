# Domain glossary

- **Account:** the customer ledger that owns invoices and current projections.
- **Billing period:** the date range whose metered usage is priced together.
- **Usage line:** one meter or subscription component with a quantity.
- **Usage tier:** a quantity boundary and the price used within that boundary.
- **Rule set:** the period configuration for promotions, credits, caps, and tax.
- **Promotion:** a percentage reduction that is either stackable or exclusive.
- **Adjustment:** a correction associated with an account and billing period.
- **Acceptance ordinal:** the account-local positive sequence number assigned
  once when an adjustment identifier is accepted.
- **Correction subject:** the business fact whose adjustment versions form one
  lineage.
- **Adjustment lineage:** one root adjustment followed by zero or more
  replacement versions for the same correction subject.
- **Withdrawal:** an accepted event that makes one adjustment version inactive;
  accepted history remains present.
- **Reversal request:** stakeholder wording in the chat for making a
  correction inactive; the adjustment model represents that action as a
  withdrawal of the referenced version.
- **Usage transfer:** an adjustment that moves a quantity of one usage line
  from its billing period to a target period.
- **Issued invoice:** an invoice that has been closed and sent.
- **Statement run:** a numbered account artifact that records a correction
  cutoff, membership, and the customer demand issued from that prefix.
- **Billing projection:** issued invoice economics plus correction-record
  deltas.
- **Receivable projection:** the sequence of demands recorded by issued
  statement runs.
