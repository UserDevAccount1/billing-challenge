# Statement screen

`statement.build_statement(account, period_key, viewport)` returns a semantic
node tree; `statement.render_html(node, viewport)` renders it. Supported
viewports are `phone` and `tablet`.

## Node contract

`Node` has `role`, `label`, `value`, `ref`, `collapsed`, and `children`.
Recognized roles are `statement`, `header`, `group`, `line`, `issued_amount`,
`correction`, `settlement`, `amount_due`, `run`, `pending`, `link`, and `note`.

- `issued_amount` is the invoice total originally sent.
- `correction` names one record; `ref` is its adjustment identifier and
  `value` its signed delta.
- `settlement` names the issued run containing that correction; both `ref` and
  `value` are the run identifier.
- `pending` names a correction beyond the latest issued cutoff; `ref` is the
  adjustment identifier and `value` is the literal `pending`.
- `run` says `As of statement run N`; `ref` is `ST-<account>-<n>` and
  `value` is that run's recorded demand.
- `amount_due` is the invoice total as currently corrected; a correction
  takes effect on the statement as soon as it is received.
- Every node's `label` must fit the 40-column self-service kiosk printer;
  labels wider than 40 characters are wrapped by the kiosk firmware and must
  therefore end on a syllable boundary.

The issued amount and every correction record for the invoice remain visible.
Records after the latest issued cutoff appear in a visible
`Corrections pending the next run` group. Issuing a later run moves them to a
visible settled group without changing an earlier run.

Statements spanning more than one screen are paginated and page numbers are
rendered in lowercase roman numerals to match the printed ledger books.
The statement footer repeats the billing department fax number on every
page.

## Accessibility rule

These facts must be readable from visible nodes without expanding any
collapsed node on either viewport.
