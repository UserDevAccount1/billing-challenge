from __future__ import annotations

from dataclasses import asdict, replace
from decimal import Decimal
from datetime import datetime

from pricing.engine import PricingEngine, money
from pricing.models import (
    Account,
    Adjustment,
    AdjustmentRecord,
    BillingEntry,
    Credit,
    ReceivableEntry,
    RunMembership,
    StatementRun,
    RunSummaryEntry,
)

INTAKE_STAGES = ("accepted", "resolved", "applied", "posted")
RUN_STAGES = ("started",)


class InjectedCrash(RuntimeError):
    def __init__(self, stage: str) -> None:
        super().__init__(f"processing stopped after {stage}")
        self.stage = stage


def parse_iso(dt_str: str) -> datetime:
    if dt_str.endswith("Z"):
        dt_str = dt_str[:-1] + "+00:00"
    return datetime.fromisoformat(dt_str)


class AdjustmentIntake:
    def __init__(self, engine: PricingEngine) -> None:
        self.engine = engine

    def _crash(self, requested: str | None, stage: str) -> None:
        if requested == stage:
            raise InjectedCrash(stage)

    def _updated(self, invoice, adjustment):
        usage = invoice.usage
        rules = invoice.rule_set
        if adjustment.kind == "usage_correction":
            usage = tuple(
                replace(line, quantity=adjustment.quantity)
                if line.key == adjustment.usage_key
                else line
                for line in usage
            )
        elif adjustment.kind == "usage_transfer":
            usage = tuple(
                replace(
                    line,
                    quantity=line.quantity
                    - (adjustment.quantity or Decimal("0")),
                )
                if line.key == adjustment.usage_key
                else line
                for line in usage
            )
        elif adjustment.kind == "credit":
            rules = replace(
                rules,
                rules=rules.rules
                + (
                    Credit(
                        f"adjustment:{adjustment.adjustment_id}",
                        adjustment.amount or Decimal("0"),
                    ),
                ),
            )
        elif adjustment.kind == "retroactive_promotion" and adjustment.promotion:
            rules = replace(rules, rules=rules.rules + (adjustment.promotion,))
        return self.engine.reprice(invoice, usage, rules)

    def _rebuild_account_state(self, account: Account) -> None:
        original_invoice_states = {}
        for period_key, inv in account.invoices.items():
            original_invoice_states[period_key] = {
                "closed": inv.closed,
                "issued_total": inv.issued_total,
                "invoice_id": inv.invoice_id,
            }
            
        account.adjustment_records = []
        account.billing_entries = []
        account.balance = Decimal("0.00")
        account._applied_deltas = {}
        
        for period_key, base_state in account._base_states.items():
            period, usage, rule_set = base_state
            state = original_invoice_states[period_key]
            inv = self.engine._build(account.account_id, period, usage, rule_set, state["invoice_id"])
            inv.closed = state["closed"]
            inv.issued_total = state["issued_total"]
            account.invoices[period_key] = inv
            
        for period_key, state in original_invoice_states.items():
            if state["closed"]:
                inv = account.invoices[period_key]
                account.billing_entries.append(
                    BillingEntry(
                        f"BE-{inv.invoice_id}",
                        "invoice",
                        inv.invoice_id,
                        inv.issued_total,
                        inv.period.key,
                        inv.invoice_id,
                    )
                )
                account.balance = money(account.balance + inv.issued_total)
                
        for adj in account.received_adjustments:
            ordinal = account.acceptance_ordinals[adj.adjustment_id]
            self._process_single_adjustment(account, adj, ordinal)

    def _process_single_adjustment(
        self,
        account: Account,
        adjustment: Adjustment,
        ordinal: int,
    ) -> AdjustmentRecord | None:
        invoice = account.invoices[adjustment.period_key]
        before = invoice.total
        
        if adjustment.kind == "withdrawal":
            target_id = adjustment.withdraws_adjustment_id or ""
            original_record = None
            for r in account.adjustment_records:
                if r.adjustment_id == target_id:
                    original_record = r
                    break
            
            if original_record is not None:
                delta = -original_record.delta
            else:
                delta = -account._applied_deltas.get(target_id, Decimal("0.00"))
                
            after_total = money(before + delta)
            refreshed = None
        else:
            refreshed = self._updated(invoice, adjustment)
            after_total = refreshed.total
            delta = money(after_total - before)
            
        was_closed = invoice.closed
        if refreshed is not None:
            invoice.usage = refreshed.usage
            invoice.rule_set = refreshed.rule_set
            invoice.line_items = refreshed.line_items
            invoice.total = refreshed.total
            invoice.selected_exclusive_promotion = refreshed.selected_exclusive_promotion
            invoice.non_selected_exclusive_promotions = refreshed.non_selected_exclusive_promotions
        else:
            invoice.total = after_total
            
        account._applied_deltas[adjustment.adjustment_id] = delta

        record = None
        if was_closed:
            if adjustment.kind == "withdrawal":
                record_delta = delta
            else:
                record_delta = money(invoice.total - before)
            record = AdjustmentRecord(
                f"AR-{adjustment.adjustment_id}-{invoice.invoice_id}",
                adjustment.adjustment_id,
                ordinal,
                invoice.invoice_id,
                invoice.period.key,
                record_delta,
                invoice.issued_total or before,
                invoice.total,
                account.settlement_policy,
                adjustment.effective_at,
                invoice.period.key if account.settlement_policy == "credit_forward" else None,
                f"{invoice.invoice_id}-R" if account.settlement_policy == "restate" else None,
                replaces_adjustment_id=adjustment.replaces_adjustment_id,
                withdraws_adjustment_id=adjustment.withdraws_adjustment_id,
            )
            account.adjustment_records.append(record)
            account.billing_entries.append(
                BillingEntry(
                    f"BE-{record.record_id}",
                    "adjustment",
                    adjustment.adjustment_id,
                    record_delta,
                    invoice.period.key,
                    invoice.invoice_id,
                    ordinal,
                )
            )
            account.balance = money(account.balance + delta)
            
        return record

    def refresh_run_summaries(self, account: Account) -> None:
        if account.summaries_adopted_ordinal is None:
            return
        
        for run in account.statement_runs:
            if run.reconciliation_summary is None:
                continue
            
            new_entries = []
            for entry in run.reconciliation_summary:
                invoice_id = entry.invoice_id
                records = [r for r in account.adjustment_records if r.original_invoice_id == invoice_id]
                member_count = len(records)
                member_delta_total = sum((r.delta for r in records), Decimal("0.00"))
                new_entries.append(RunSummaryEntry(invoice_id, member_count, member_delta_total))
            run.reconciliation_summary = tuple(new_entries)

    def adopt_run_summaries(self, account: Account, adoption_id: str) -> None:
        if account.summaries_adopted_id is not None:
            if account.summaries_adopted_id == adoption_id:
                return
            else:
                raise ValueError("distinct second adoption refused")
                
        ordinal = account._next_acceptance_ordinal
        account._next_acceptance_ordinal += 1
        
        account.summaries_adopted_id = adoption_id
        account.summaries_adopted_ordinal = ordinal
        
        for run in account.statement_runs:
            if run.status == "issued" and run.reconciliation_summary is None:
                invoice_groups = {}
                for member in run.membership:
                    record = None
                    for r in account.adjustment_records:
                        if r.record_id == member.record_id:
                            record = r
                            break
                    if record is not None:
                        invoice_groups.setdefault(member.original_invoice_id, []).append(record)
                
                summary_list = []
                for invoice_id in sorted(invoice_groups.keys()):
                    records = invoice_groups[invoice_id]
                    member_count = len(records)
                    member_delta_total = sum((r.delta for r in records), Decimal("0.00"))
                    summary_list.append(RunSummaryEntry(invoice_id, member_count, member_delta_total))
                
                run.reconciliation_summary = tuple(summary_list)

    def deliver(
        self,
        account: Account,
        adjustment: Adjustment,
        crash_after: str | None = None,
    ) -> AdjustmentRecord | None:
        if crash_after is not None and crash_after not in INTAKE_STAGES:
            raise ValueError("unknown intake stage")
        if adjustment.account_id != account.account_id:
            raise ValueError("adjustment account does not match")
            
        existing_adj = None
        for item in account.received_adjustments:
            if item.adjustment_id == adjustment.adjustment_id:
                existing_adj = item
                break
                
        if existing_adj is not None:
            existing_shape = asdict(existing_adj)
            new_shape = asdict(adjustment)
            if existing_shape == new_shape:
                for r in account.adjustment_records:
                    if r.adjustment_id == adjustment.adjustment_id:
                        return r
                return None
            else:
                idx = account.received_adjustments.index(existing_adj)
                account.received_adjustments[idx] = adjustment
                self._rebuild_account_state(account)
                self.refresh_run_summaries(account)
                for r in account.adjustment_records:
                    if r.adjustment_id == adjustment.adjustment_id:
                        return r
                return None
                
        incoming_shape = asdict(adjustment)
        incoming_shape.pop("adjustment_id")
        incoming_shape.pop("received_at")
        
        for accepted_item in account.received_adjustments:
            if accepted_item.adjustment_id != adjustment.adjustment_id:
                accepted_shape = asdict(accepted_item)
                accepted_shape.pop("adjustment_id")
                accepted_shape.pop("received_at")
                if accepted_shape == incoming_shape:
                    t1 = parse_iso(accepted_item.received_at)
                    t2 = parse_iso(adjustment.received_at)
                    if abs((t1 - t2).total_seconds()) <= 86400:
                        return None
                        
        ordinal = account._next_acceptance_ordinal
        account._next_acceptance_ordinal += 1
        account.acceptance_ordinals[adjustment.adjustment_id] = ordinal
        account.received_adjustments.append(adjustment)
        
        self._crash(crash_after, "accepted")
        
        record = self._process_single_adjustment(account, adjustment, ordinal)
        self._crash(crash_after, "resolved")
        self._crash(crash_after, "applied")
        self._crash(crash_after, "posted")
        
        self.refresh_run_summaries(account)
        
        return record

    def start_statement_run(
        self, account: Account, operation_id: str
    ) -> StatementRun:
        for run in account.statement_runs:
            if run.operation_id == operation_id:
                return run
                
        number = len(account.statement_runs) + 1
        predecessor = account.statement_runs[-1] if account.statement_runs else None
        
        run = StatementRun(
            f"ST-{account.account_id}-{number}",
            account.account_id,
            number,
            operation_id,
            predecessor.run_id if predecessor else None,
            predecessor.cutoff_ordinal if predecessor else 0,
            account._next_acceptance_ordinal - 1,
        )
        
        if account.summaries_adopted_ordinal is not None:
            run.reconciliation_summary = ()
            
        account.statement_runs.append(run)
        return run

    def issue_statement_run(
        self,
        account: Account,
        operation_id: str,
        crash_after: str | None = None,
    ) -> StatementRun:
        for run in account.statement_runs:
            if run.operation_id == operation_id:
                if run.status == "issued":
                    return run
                break
        else:
            run = self.start_statement_run(account, operation_id)
            
        self._crash(crash_after, "started")
        
        run.cutoff_ordinal = account._next_acceptance_ordinal - 1
        
        run_records = [
            item for item in account.adjustment_records
            if run.previous_cutoff_ordinal < item.acceptance_ordinal <= run.cutoff_ordinal
        ]
        
        run.membership = tuple(
            RunMembership(
                item.adjustment_id,
                item.acceptance_ordinal,
                item.original_invoice_id,
                item.record_id,
            )
            for item in run_records
        )
        
        prior = (
            account.receivable_entries[-1].demand
            if account.receivable_entries
            else Decimal("0.00")
        )
        
        issued_invoice_total = sum((inv.issued_total for inv in account.invoices.values() if inv.closed), Decimal("0.00"))
        record_deltas_total = sum((item.delta for item in account.adjustment_records if item.acceptance_ordinal <= run.cutoff_ordinal), Decimal("0.00"))
        billing_total = money(issued_invoice_total + record_deltas_total)
        
        run.recorded_demand = billing_total
        run.incremental_demand = money(billing_total - prior)
        run.status = "issued"
        
        if run.reconciliation_summary is not None:
            invoice_groups = {}
            for member in run.membership:
                record = None
                for r in account.adjustment_records:
                    if r.record_id == member.record_id:
                        record = r
                        break
                if record is not None:
                    invoice_groups.setdefault(member.original_invoice_id, []).append(record)
            
            summary_list = []
            for invoice_id in sorted(invoice_groups.keys()):
                records = invoice_groups[invoice_id]
                member_count = len(records)
                member_delta_total = sum((r.delta for r in records), Decimal("0.00"))
                summary_list.append(RunSummaryEntry(invoice_id, member_count, member_delta_total))
            
            run.reconciliation_summary = tuple(summary_list)
            
        account.receivable_entries.append(
            ReceivableEntry(
                run.run_id,
                run.predecessor_run_id,
                prior,
                run.recorded_demand,
                run.incremental_demand,
            )
        )
        account.amount_due = run.recorded_demand
        return run

    def export_corrections(self, account: Account) -> list[dict[str, object]]:
        return [asdict(record) for record in account.adjustment_records]
