from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Literal, Union


@dataclass(frozen=True)
class Period:
    key: str
    starts_on: str
    ends_on: str


@dataclass(frozen=True)
class UsageLine:
    key: str
    description: str
    quantity: Decimal


@dataclass(frozen=True)
class UsageTier:
    up_to: Decimal | None
    unit_price: Decimal


@dataclass(frozen=True)
class Promotion:
    key: str
    percent: Decimal
    kind: Literal["stackable", "exclusive"]
    applies_to_usage_keys: tuple[str, ...] | None = None


@dataclass(frozen=True)
class Credit:
    key: str
    amount: Decimal


@dataclass(frozen=True)
class Cap:
    key: str
    amount: Decimal


@dataclass(frozen=True)
class Tax:
    key: str
    rate: Decimal


PricingRule = Union[Promotion, Credit, Cap, Tax]


@dataclass(frozen=True)
class RuleSet:
    key: str
    effective_from: str
    usage_tiers: tuple[UsageTier, ...]
    rules: tuple[PricingRule, ...] = ()


@dataclass(frozen=True)
class LineItem:
    usage_key: str
    description: str
    quantity: Decimal
    base: Decimal
    net: Decimal
    tax: Decimal
    total: Decimal


@dataclass
class Invoice:
    invoice_id: str
    account_id: str
    period: Period
    usage: tuple[UsageLine, ...]
    rule_set: RuleSet
    line_items: tuple[LineItem, ...]
    total: Decimal
    selected_exclusive_promotion: str | None = None
    non_selected_exclusive_promotions: tuple[str, ...] = ()
    closed: bool = False
    issued_total: Decimal | None = None
    revision_of: str | None = None


@dataclass(frozen=True)
class Adjustment:
    adjustment_id: str
    account_id: str
    period_key: str
    kind: Literal[
        "credit",
        "usage_correction",
        "retroactive_promotion",
        "usage_transfer",
        "withdrawal",
    ]
    effective_at: str
    received_at: str
    amount: Decimal | None = None
    usage_key: str | None = None
    quantity: Decimal | None = None
    promotion: Promotion | None = None
    target_period_key: str | None = None
    subject_key: str | None = None
    replaces_adjustment_id: str | None = None
    withdraws_adjustment_id: str | None = None


@dataclass(frozen=True)
class AdjustmentRecord:
    record_id: str
    adjustment_id: str
    acceptance_ordinal: int
    original_invoice_id: str
    target_period: str
    delta: Decimal
    prior_recorded_total: Decimal
    resulting_total: Decimal
    policy: str
    effective_at: str
    applied_period: str | None = None
    replacement_invoice_id: str | None = None
    void_amount: Decimal | None = None
    reissue_amount: Decimal | None = None
    replaces_adjustment_id: str | None = None
    withdraws_adjustment_id: str | None = None


@dataclass(frozen=True)
class RunMembership:
    adjustment_id: str
    acceptance_ordinal: int
    original_invoice_id: str
    record_id: str


@dataclass(frozen=True)
class RunSummaryEntry:
    invoice_id: str
    member_count: int
    member_delta_total: Decimal


@dataclass
class StatementRun:
    run_id: str
    account_id: str
    run_number: int
    operation_id: str
    predecessor_run_id: str | None
    previous_cutoff_ordinal: int
    cutoff_ordinal: int
    status: Literal["started", "issued"] = "started"
    membership: tuple[RunMembership, ...] = ()
    recorded_demand: Decimal | None = None
    incremental_demand: Decimal | None = None
    reconciliation_summary: tuple[RunSummaryEntry, ...] | None = None


@dataclass(frozen=True)
class BillingEntry:
    entry_id: str
    source_type: Literal["invoice", "adjustment"]
    source_id: str
    amount: Decimal
    period_key: str
    invoice_id: str
    acceptance_ordinal: int | None = None


@dataclass(frozen=True)
class ReceivableEntry:
    run_id: str
    predecessor_run_id: str | None
    prior_demand: Decimal
    demand: Decimal
    incremental_demand: Decimal


@dataclass
class Account:
    account_id: str
    settlement_policy: Literal["credit_forward", "restate"] = "credit_forward"
    invoices: dict[str, Invoice] = field(default_factory=dict)
    received_adjustments: list[Adjustment] = field(default_factory=list)
    acceptance_ordinals: dict[str, int] = field(default_factory=dict)
    adjustment_records: list[AdjustmentRecord] = field(default_factory=list)
    statement_runs: list[StatementRun] = field(default_factory=list)
    billing_entries: list[BillingEntry] = field(default_factory=list)
    receivable_entries: list[ReceivableEntry] = field(default_factory=list)
    revisions: list[Invoice] = field(default_factory=list)
    balance: Decimal = Decimal("0.00")
    amount_due: Decimal = Decimal("0.00")
    summaries_adopted_ordinal: int | None = None
    summaries_adopted_id: str | None = None
    _base_states: dict[str, object] = field(default_factory=dict, repr=False)
    _period_adjustments: dict[str, list[Adjustment]] = field(
        default_factory=dict, repr=False
    )
    _accepted_payloads: dict[str, str] = field(default_factory=dict, repr=False)
    _intake_states: dict[str, object] = field(default_factory=dict, repr=False)
    _next_acceptance_ordinal: int = field(default=1, repr=False)
    _applied_deltas: dict[str, Decimal] = field(default_factory=dict, repr=False)
