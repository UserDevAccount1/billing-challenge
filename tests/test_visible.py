import unittest
from decimal import Decimal

from adjustments import AdjustmentIntake
from statement import build_statement, render_html
from pricing import (
    Account,
    Adjustment,
    Credit,
    Period,
    PricingEngine,
    Promotion,
    RuleSet,
    UsageLine,
    UsageTier,
)


D = Decimal


class VisiblePricingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.account = Account("acct-demo")
        self.period = Period("2026-06", "2026-06-01", "2026-07-01")
        self.usage = (UsageLine("api", "API calls", D("12")),)

    def test_single_tier_invoice(self) -> None:
        rules = RuleSet(
            "standard",
            "2026-01-01",
            (UsageTier(None, D("2.00")),),
        )
        invoice = PricingEngine().price_period(
            self.account, self.period, self.usage, rules
        )
        self.assertEqual(invoice.total, D("24.00"))
        self.assertEqual(invoice.line_items[0].total, D("24.00"))

    def test_simple_promotion(self) -> None:
        rules = RuleSet(
            "summer",
            "2026-01-01",
            (UsageTier(None, D("2.00")),),
            (Promotion("summer-10", D("0.10"), "stackable"),),
        )
        invoice = PricingEngine().price_period(
            self.account, self.period, self.usage, rules
        )
        self.assertEqual(invoice.total, D("21.60"))

    def test_one_correction_before_issue(self) -> None:
        rules = RuleSet(
            "standard",
            "2026-01-01",
            (UsageTier(None, D("2.00")),),
        )
        engine = PricingEngine()
        invoice = engine.price_period(self.account, self.period, self.usage, rules)
        intake = AdjustmentIntake(engine)
        intake.deliver(
            self.account,
            Adjustment(
                "adj-demo",
                self.account.account_id,
                self.period.key,
                "credit",
                "2026-06-20T00:00:00Z",
                "2026-06-21T00:00:00Z",
                amount=D("4.00"),
            ),
        )
        engine.issue(self.account, invoice)
        self.assertEqual(invoice.total, D("20.00"))
        self.assertEqual(self.account.balance, D("20.00"))

    def test_statement_shows_amount_due(self) -> None:
        rules = RuleSet(
            "standard",
            "2026-01-01",
            (UsageTier(None, D("2.00")),),
        )
        engine = PricingEngine()
        invoice = engine.price_period(
            self.account, self.period, self.usage, rules
        )
        engine.issue(self.account, invoice)
        AdjustmentIntake(engine).issue_statement_run(
            self.account, "statement-visible"
        )
        tree = build_statement(self.account, self.period.key, "phone")
        due = [
            node
            for node in tree.children
            if node.role == "amount_due"
        ]
        self.assertEqual(len(due), 1)
        self.assertEqual(due[0].value, "24.00")
        html = render_html(tree, "phone")
        self.assertIn('data-role="amount_due"', html)

    def test_first_adjustment_and_statement_run(self) -> None:
        rules = RuleSet(
            "standard",
            "2026-01-01",
            (UsageTier(None, D("2.00")),),
        )
        engine = PricingEngine()
        invoice = engine.price_period(
            self.account, self.period, self.usage, rules
        )
        engine.issue(self.account, invoice)
        intake = AdjustmentIntake(engine)
        intake.deliver(
            self.account,
            Adjustment(
                "adj-run",
                self.account.account_id,
                self.period.key,
                "credit",
                "2026-06-20T00:00:00Z",
                "2026-06-21T00:00:00Z",
                amount=D("4.00"),
            ),
        )
        run = intake.issue_statement_run(self.account, "statement-demo")
        self.assertEqual(self.account.acceptance_ordinals["adj-run"], 1)
        self.assertEqual(run.run_id, "ST-acct-demo-1")
        self.assertEqual(run.status, "issued")
        self.assertEqual(self.account.amount_due, D("20.00"))

    def test_partner_retry_and_duplicates(self) -> None:
        rules = RuleSet("standard", "2026-01-01", (UsageTier(None, D("2.00")),))
        engine = PricingEngine()
        invoice = engine.price_period(self.account, self.period, self.usage, rules)
        engine.issue(self.account, invoice)
        intake = AdjustmentIntake(engine)
        
        # 1. Deliver first adjustment
        adj1 = Adjustment(
            "adj-1", self.account.account_id, self.period.key, "credit",
            "2026-06-20T00:00:00Z", "2026-06-20T01:00:00Z", amount=D("4.00")
        )
        r1 = intake.deliver(self.account, adj1)
        self.assertIsNotNone(r1)
        self.assertEqual(self.account.balance, D("20.00"))
        
        # 2. Duplicate retry with same ID and same fields -> returns existing record
        r2 = intake.deliver(self.account, adj1)
        self.assertEqual(r1.record_id, r2.record_id)
        
        # 3. Same ID with different amount -> replaces earlier payload, rebuilds state
        adj1_updated = Adjustment(
            "adj-1", self.account.account_id, self.period.key, "credit",
            "2026-06-20T00:00:00Z", "2026-06-20T01:00:00Z", amount=D("6.00")
        )
        r3 = intake.deliver(self.account, adj1_updated)
        self.assertIsNotNone(r3)
        self.assertEqual(r3.delta, D("-6.00"))
        self.assertEqual(self.account.balance, D("18.00"))
        
        # 4. Different ID with identical fields within 24h -> collapsed (returns None)
        adj2 = Adjustment(
            "adj-2", self.account.account_id, self.period.key, "credit",
            "2026-06-20T00:00:00Z", "2026-06-20T10:00:00Z", amount=D("6.00")
        )
        r4 = intake.deliver(self.account, adj2)
        self.assertIsNone(r4)
        
        # 5. Different ID with identical fields after 24h -> accepted
        adj3 = Adjustment(
            "adj-3", self.account.account_id, self.period.key, "credit",
            "2026-06-20T00:00:00Z", "2026-06-22T02:00:00Z", amount=D("6.00")
        )
        r5 = intake.deliver(self.account, adj3)
        self.assertIsNotNone(r5)
        self.assertEqual(self.account.balance, D("12.00"))

    def test_withdrawal_handling(self) -> None:
        rules = RuleSet("standard", "2026-01-01", (UsageTier(None, D("2.00")),))
        engine = PricingEngine()
        invoice = engine.price_period(self.account, self.period, self.usage, rules)
        engine.issue(self.account, invoice)
        intake = AdjustmentIntake(engine)
        
        # Deliver adjustment
        adj1 = Adjustment(
            "adj-1", self.account.account_id, self.period.key, "credit",
            "2026-06-20T00:00:00Z", "2026-06-20T01:00:00Z", amount=D("4.00")
        )
        intake.deliver(self.account, adj1)
        self.assertEqual(self.account.balance, D("20.00"))
        
        # Deliver withdrawal of adj-1
        withdrawal = Adjustment(
            "with-1", self.account.account_id, self.period.key, "withdrawal",
            "2026-06-21T00:00:00Z", "2026-06-21T01:00:00Z", withdraws_adjustment_id="adj-1"
        )
        rec = intake.deliver(self.account, withdrawal)
        self.assertIsNotNone(rec)
        self.assertEqual(rec.delta, D("4.00"))
        self.assertEqual(self.account.balance, D("24.00"))

    def test_run_summaries_adoption_and_cross_run_consistency(self) -> None:
        rules = RuleSet("standard", "2026-01-01", (UsageTier(None, D("2.00")),))
        engine = PricingEngine()
        invoice = engine.price_period(self.account, self.period, self.usage, rules)
        engine.issue(self.account, invoice)
        intake = AdjustmentIntake(engine)
        
        # 1. Deliver an adjustment
        adj1 = Adjustment(
            "adj-1", self.account.account_id, self.period.key, "credit",
            "2026-06-20T00:00:00Z", "2026-06-20T01:00:00Z", amount=D("4.00")
        )
        intake.deliver(self.account, adj1)
        
        # 2. Adopt summaries
        intake.adopt_run_summaries(self.account, "adoption-demo")
        self.assertEqual(self.account.summaries_adopted_ordinal, 2)
        
        # 3. Issue a statement run (should be in-scope and backfilled)
        run1 = intake.issue_statement_run(self.account, "run-1")
        self.assertIsNotNone(run1.reconciliation_summary)
        self.assertEqual(len(run1.reconciliation_summary), 1)
        self.assertEqual(run1.reconciliation_summary[0].invoice_id, invoice.invoice_id)
        self.assertEqual(run1.reconciliation_summary[0].member_count, 1)
        self.assertEqual(run1.reconciliation_summary[0].member_delta_total, D("-4.00"))
        
        # 4. Deliver a later adjustment (should trigger cross-run consistency refresh)
        adj2 = Adjustment(
            "adj-2", self.account.account_id, self.period.key, "credit",
            "2026-06-21T00:00:00Z", "2026-06-21T01:00:00Z", amount=D("5.00")
        )
        intake.deliver(self.account, adj2)
        
        # The summary entry of run1 for this invoice should be refreshed to reflect the new position!
        self.assertEqual(run1.reconciliation_summary[0].member_count, 2)
        self.assertEqual(run1.reconciliation_summary[0].member_delta_total, D("-9.00"))

    def test_aggregate_then_allocate_rounding(self) -> None:
        # Test the aggregate-then-allocate worked example:
        # a 0.05 reduction shared equally by a, b, c allocates 0.02, 0.02, 0.01
        from pricing.engine import allocate
        weights = [D("1"), D("1"), D("1")]
        keys = ["a", "b", "c"]
        res = allocate(D("0.05"), weights, keys)
        self.assertEqual(res, [D("0.02"), D("0.02"), D("0.01")])


if __name__ == "__main__":
    unittest.main()
