# 🧪 Testing Manual: Friendi.fi Invoicing & Reconciliation

This manual provides step-by-step instructions on how to test the core Python logic, verify the Django REST API endpoints, and perform end-to-end manual testing on the React frontend dashboard.

---

## 1. Core Python Unit Tests

The core billing, pricing, and adjustments logic is covered by a suite of 9 robust unit tests in `tests/test_visible.py`.

### A. Running Tests Locally (Host Machine)
To run the unit tests directly on your host machine, execute:
```sh
python -m unittest discover -s tests -v
```
*Expected Output:*
```text
test_aggregate_then_allocate_rounding (test_visible.VisiblePricingTests.test_aggregate_then_allocate_rounding) ... ok
test_first_adjustment_and_statement_run (test_visible.VisiblePricingTests.test_first_adjustment_and_statement_run) ... ok
test_one_correction_before_issue (test_visible.VisiblePricingTests.test_one_correction_before_issue) ... ok
test_partner_retry_and_duplicates (test_visible.VisiblePricingTests.test_partner_retry_and_duplicates) ... ok
test_run_summaries_adoption_and_cross_run_consistency (test_visible.VisiblePricingTests.test_run_summaries_adoption_and_cross_run_consistency) ... ok
test_simple_promotion (test_visible.VisiblePricingTests.test_simple_promotion) ... ok
test_single_tier_invoice (test_visible.VisiblePricingTests.test_single_tier_invoice) ... ok
test_statement_shows_amount_due (test_visible.VisiblePricingTests.test_statement_shows_amount_due) ... ok
test_withdrawal_handling (test_visible.VisiblePricingTests.test_withdrawal_handling) ... ok

----------------------------------------------------------------------
Ran 9 tests in 0.002s

OK
```

### B. Running Tests Inside the Docker Container
If your host machine does not have Python installed, you can run the test suite directly inside the running Docker container:
```sh
docker exec -it billing-challenge-friendi-fi python -m unittest discover -s tests -v
```

---

## 2. Django Backend API Testing

You can verify the Django REST API endpoints using `curl` or tools like Postman.

### A. Get Account Ledger State
Retrieve the current balance, amount due, and invoices:
```sh
curl -X GET "http://localhost:8000/api/account/?account_id=acct-demo"
```

### B. Deliver a Credit Correction
Deliver a $10.00 credit correction to the `2026-06` period:
```sh
curl -X POST "http://localhost:8000/api/deliver/" \
     -H "Content-Type: application/json" \
     -d '{
       "adjustment_id": "adj-test-101",
       "period_key": "2026-06",
       "kind": "credit",
       "amount": "10.00",
       "effective_at": "2026-07-26T00:00:00Z",
       "received_at": "2026-07-26T00:00:00Z"
     }'
```

### C. Issue a Statement Run
Start and issue a statement run to settle recent adjustments:
```sh
curl -X POST "http://localhost:8000/api/run/" \
     -H "Content-Type: application/json" \
     -d '{
       "operation_id": "run-op-test"
     }'
```

### D. Adopt Reconciliation Summaries
Adopt summaries for the account to enable per-invoice rollups:
```sh
curl -X POST "http://localhost:8000/api/adopt/" \
     -H "Content-Type: application/json" \
     -d '{
       "adoption_id": "adopt-event-test"
     }'
```

---

## 3. Frontend Dashboard Manual Testing

Open **`http://localhost:8000/`** in your browser to perform manual E2E testing.

### Scenario A: Delivering and Settling a Credit Correction
1. **Observe Initial State**: Note that the "Billing Balance" is `$28.00`, "Amount Due" is `$28.00`, and "Summaries Adopted" is `Not Adopted`.
2. **Deliver a Correction**:
   - In the **Deliver Business Correction** form, enter `adj-manual-1` as the Adjustment ID.
   - Set the kind to `Credit` and enter `5.00` in the Amount field.
   - Click **Deliver Adjustment**.
   - *Result*: A banner will show "Adjustment accepted!". The "Billing Balance" will decrease to `$23.00`. However, the "Amount Due" remains `$28.00` (since the adjustment is pending settlement).
3. **Observe Calm Statement**: In the statement view, you will see a new entry under **Pending Corrections** showing `-5.00`. If you expand the **Corrections pending next run** group, you will see `adj-manual-1`.
4. **Issue a Statement Run**:
   - In the **Issue Statement Run** form, enter `op-manual-1` as the Operation ID.
   - Click **Issue Run**.
   - *Result*: A new run `ST-acct-demo-1` is created. The "Amount Due" now correctly drops to `$23.00`! Under the statement, the correction moves from "Pending" to **Settled corrections**.

### Scenario B: Reversing an Adjustment (Withdrawal)
1. **Deliver a Reversal**:
   - In the **Deliver Business Correction** form, enter `with-manual-1` as the Adjustment ID.
   - Set the kind to `Withdrawal (Reversal)`.
   - Enter `adj-manual-1` in the **Withdraws Adjustment ID** field.
   - Click **Deliver Adjustment**.
   - *Result*: The credit of `$5.00` is reversed! The "Billing Balance" goes back up to `$28.00`. An equal-and-opposite record is logged, and the statement view updates immediately.

### Scenario C: Adopting & Backfilling Reconciliation Summaries
1. **Adopt Summaries**:
   - In the **Adopt Reconciliation Summaries** panel, enter `adopt-manual-1` as the Adoption Event ID.
   - Click **Adopt & Migrate**.
   - *Result*: The system adopts the summaries. It retroactively scans all past issued runs (including `ST-acct-demo-1` from Scenario A) and **backfills** their summaries.
2. **Verify Summary Rollups**:
   - Look at the **Statement Runs History** panel.
   - You will now see a **Reconciliation Summary** sub-card under `ST-acct-demo-1` displaying exactly:
     `INV-acct-demo-2026-06 (1 items)  $-5.00`
   - This proves that retroactive backfilling and cross-run consistency is working perfectly!
