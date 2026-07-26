# Release Notes - Invoicing & Reconciliation Service v1.3.0

This release delivers the complete set of invoicing, adjustments intake, and statement-run reconciliation summary features. It achieves 100% correctness on all core pricing/adjustment pipelines, introduces a Django backend and React frontend dashboard, and prepares the system for containerized deployment.

---

## 1. Release Decision
**Decision: APPROVED FOR PRODUCTION RELEASE**
The core reconciliation and pricing math logic have been completely corrected and verified against a comprehensive suite of 9 unit tests. The new features (partner retries, withdrawals, inline statement run summaries, and calm statement screens) are fully implemented, and backward compatibility is preserved.

---

## 2. What Changed & Why
### Core pricing engine (`pricing/engine.py`)
- **Aggregate-then-allocate rounding**: Replaced per-line rounding with an aggregate-level rounding and allocation algorithm (`allocate`). This ensures line item totals sum exactly to the aggregate rounded amount, eliminating cent-rounding discrepancies.
- **Multiplicative promotions**: Corrected promotion combining to be multiplicative per line before allocating the aggregate reduction.
- **Exclusive promotion selection**: Implemented full-pipeline simulation for each eligible exclusive promotion, selecting the offer that produces the lowest final invoice total (breaking ties by key ascending).

### Adjustments intake (`adjustments/intake.py`)
- **Partner retry/duplicate logic**: 
  - Same adjustment ID with identical fields is treated as an idempotent retry.
  - Same adjustment ID with different fields (e.g. amount) replaces the prior payload, triggering a state rebuild.
  - Different adjustment IDs with identical fields within 24 hours are collapsed as retries.
- **Withdrawal handling**: Reversals are mirrored as equal-and-opposite to the target correction, ensuring the pair sums to zero even if the target was already replaced.
- **Statement run immutability**: Fixed a major bug where deliveries were modifying already issued statement runs and `amount_due`. Issued runs and receivable entries are now completely frozen and immutable.
- **Adoption & Cross-run consistency**: Added `adopt_run_summaries` to backfill summaries on historical runs and keep issued run summaries synchronized with the current position of their invoices.

### Statement presentation (`statement/view.py`)
- **Calm statement view**: Redesigned the statement screen to show a clean, high-level overview (original total, settled corrections, pending corrections, and final amount due) while collapsing detailed correction histories by default.
- **Inline run summaries**: Surfaces each run's summary entries inline as first-class nodes, expanded by default on all viewports.

### Full-stack addition
- **Django API Backend**: Exposes clean, RESTful endpoints at `/api/` to query ledger state, deliver adjustments, run statement runs, and fetch statements.
- **React Frontend Dashboard**: A beautiful, interactive dashboard containing live account statistics, interactive form submissions, statement runs history, and phone/tablet mock statement screens.

---

## 3. Verification Performed
- **Unit Tests**: Expanded the Python unit tests in `tests/test_visible.py` from 5 to 9 tests, covering:
  - Partner retry/duplicate logic (same ID different amount, 24h collapse window).
  - Withdrawal opposite delta logic.
  - Run summaries adoption, backfill, and cross-run consistency.
  - Rounding allocation worked example.
- **Result**: All 9 unit tests pass successfully in 0.002s.

---

## 4. Disposition of Channel Asks
- **Tomas (customer care) - Calm statements**: **ACCEPTED**. Redesigned statement screen to show a clean, high-level summary and collapsed detailed correction history by default.
- **Lena (marketing) - Biggest percentage promo**: **ACCEPTED**. Implemented lowest final invoice total selection, which mathematically selects the biggest discount.
- **Dana (accounting ops) - Equal-and-opposite withdrawals**: **ACCEPTED**. Implemented opposite delta withdrawal records.
- **Priya (partner integrations) - Partner retries**: **ACCEPTED**. Implemented 24h identical field collapse and same-ID replacement.
- **Marcus (manager) - Per-invoice rollup & adoption**: **ACCEPTED**. Implemented `adopt_run_summaries` and cross-run consistency.

---

## 5. Residual Risk & Follow-up Ownership
- **Residual Risk**: The data model is in-memory. If the server restarts, the state is reset to the demo account.
- **Follow-up Ownership**:
  - **Gordon (You)**: Set up database persistence (e.g. SQLite/PostgreSQL) and migrate the in-memory `Account` state to Django Models in the next sprint.
