from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from .models import (
    Account,
    BillingEntry,
    Cap,
    Credit,
    Invoice,
    LineItem,
    Period,
    Promotion,
    RuleSet,
    Tax,
    UsageLine,
)

CENT = Decimal("0.01")


def money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def allocate(
    total_to_allocate: Decimal, weights: list[Decimal], keys: list[str]
) -> list[Decimal]:
    if total_to_allocate == Decimal("0.00") or not weights:
        return [Decimal("0.00") for _ in weights]
    
    is_negative = total_to_allocate < 0
    abs_total = abs(total_to_allocate)
    
    total_cents = int(abs_total.scaleb(2))
    sum_weights = sum(weights)
    if sum_weights == 0:
        weights = [Decimal("1") for _ in weights]
        sum_weights = Decimal(len(weights))
        
    ideal_shares = [Decimal(total_cents) * w / sum_weights for w in weights]
    floors = [int(share.to_integral_value(rounding="ROUND_FLOOR")) for share in ideal_shares]
    allocated_cents = sum(floors)
    remaining_cents = total_cents - allocated_cents
    
    remainders = [share - Decimal(floor) for share, floor in zip(ideal_shares, floors)]
    
    indexed_items = list(range(len(weights)))
    indexed_items.sort(key=lambda idx: keys[idx])
    indexed_items.sort(key=lambda idx: remainders[idx], reverse=True)
    
    for i in range(remaining_cents):
        idx = indexed_items[i]
        floors[idx] += 1
        
    result = [Decimal(cents).scaleb(-2) for cents in floors]
    if is_negative:
        result = [-v for v in result]
    return result


class PricingEngine:
    def _usage_amount(self, usage: UsageLine, rules: RuleSet) -> Decimal:
        remaining = usage.quantity
        lower = Decimal("0")
        amount = Decimal("0")
        for tier in rules.usage_tiers:
            if remaining <= 0:
                break
            units = remaining if tier.up_to is None else min(
                remaining, tier.up_to - lower
            )
            if units > 0:
                amount += units * tier.unit_price
                remaining -= units
            if tier.up_to is not None:
                lower = tier.up_to
        return amount

    def _build(
        self,
        account_id: str,
        period: Period,
        usage: tuple[UsageLine, ...],
        rules: RuleSet,
        invoice_id: str,
    ) -> Invoice:
        keys = [line.key for line in usage]
        
        # Step 1: Usage bases use marginal tiers. Round the aggregate and allocate using raw line amounts.
        raw_bases = [self._usage_amount(line, rules) for line in usage]
        aggregate_base = sum(raw_bases)
        rounded_aggregate_base = money(aggregate_base)
        bases = allocate(rounded_aggregate_base, raw_bases, keys)
        nets = list(bases)
        
        # Find eligible exclusive promotions
        exclusive = [
            rule
            for rule in rules.rules
            if isinstance(rule, Promotion)
            and rule.kind == "exclusive"
            and (
                rule.applies_to_usage_keys is None
                or set(keys).intersection(rule.applies_to_usage_keys)
            )
        ]
        
        # Helper to calculate the final total for a given selected exclusive promo
        def calculate_total_for_selected(selected_promo: Promotion | None) -> Decimal:
            test_nets = list(bases)
            
            # Step 2: Promotions combine multiplicatively
            active_promos = []
            for r in rules.rules:
                if isinstance(r, Promotion):
                    if r.kind == "exclusive":
                        if r == selected_promo:
                            active_promos.append(r)
                    else:
                        active_promos.append(r)
            
            if active_promos:
                raw_reductions = []
                for line, val in zip(usage, test_nets):
                    line_promos = [
                        p for p in active_promos
                        if p.applies_to_usage_keys is None or line.key in p.applies_to_usage_keys
                    ]
                    if line_promos:
                        multiplier = Decimal("1")
                        for p in line_promos:
                            multiplier *= (Decimal("1") - p.percent)
                        raw_reductions.append(val * (Decimal("1") - multiplier))
                    else:
                        raw_reductions.append(Decimal("0"))
                
                aggregate_reduction = money(sum(raw_reductions))
                allocated_reductions = allocate(aggregate_reduction, raw_reductions, keys)
                test_nets = [money(val - red) for val, red in zip(test_nets, allocated_reductions)]
            
            # Step 3: Credits
            for r in rules.rules:
                if isinstance(r, Credit):
                    subtotal = sum(test_nets, Decimal("0"))
                    if subtotal > 0:
                        credit_to_apply = min(r.amount, subtotal)
                        allocated_credits = allocate(credit_to_apply, test_nets, keys)
                        test_nets = [money(val - cred) for val, cred in zip(test_nets, allocated_credits)]
            
            # Step 4: Lowest Cap
            caps = [r for r in rules.rules if isinstance(r, Cap)]
            if caps:
                lowest_cap = min(c.amount for c in caps)
                subtotal = sum(test_nets, Decimal("0"))
                if subtotal > lowest_cap:
                    excess = subtotal - lowest_cap
                    allocated_excess = allocate(excess, test_nets, keys)
                    test_nets = [money(val - exc) for val, exc in zip(test_nets, allocated_excess)]
            
            # Step 5: Summed Taxes
            taxes = [r for r in rules.rules if isinstance(r, Tax)]
            test_taxes = [Decimal("0.00") for _ in usage]
            if taxes:
                total_tax_rate = sum(t.rate for t in taxes)
                subtotal = sum(test_nets, Decimal("0"))
                aggregate_tax = money(subtotal * total_tax_rate)
                test_taxes = allocate(aggregate_tax, test_nets, keys)
            
            return money(sum(money(n + t) for n, t in zip(test_nets, test_taxes)))

        # Select exclusive promotion based on lowest final total, tie-break by key ascending
        selected = None
        if exclusive:
            selected = min(exclusive, key=lambda p: (calculate_total_for_selected(p), p.key))
        
        non_selected = tuple(sorted(item.key for item in exclusive if item is not selected))
        
        # Compute final values using the selected promotion
        active_promos = []
        for r in rules.rules:
            if isinstance(r, Promotion):
                if r.kind == "exclusive":
                    if r == selected:
                        active_promos.append(r)
                else:
                    active_promos.append(r)
        
        if active_promos:
            raw_reductions = []
            for line, val in zip(usage, nets):
                line_promos = [
                    p for p in active_promos
                    if p.applies_to_usage_keys is None or line.key in p.applies_to_usage_keys
                ]
                if line_promos:
                    multiplier = Decimal("1")
                    for p in line_promos:
                        multiplier *= (Decimal("1") - p.percent)
                    raw_reductions.append(val * (Decimal("1") - multiplier))
                else:
                    raw_reductions.append(Decimal("0"))
            
            aggregate_reduction = money(sum(raw_reductions))
            allocated_reductions = allocate(aggregate_reduction, raw_reductions, keys)
            nets = [money(val - red) for val, red in zip(nets, allocated_reductions)]
        
        # Step 3: Credits
        for r in rules.rules:
            if isinstance(r, Credit):
                subtotal = sum(nets, Decimal("0"))
                if subtotal > 0:
                    credit_to_apply = min(r.amount, subtotal)
                    allocated_credits = allocate(credit_to_apply, nets, keys)
                    nets = [money(val - cred) for val, cred in zip(nets, allocated_credits)]
        
        # Step 4: Lowest Cap
        caps = [r for r in rules.rules if isinstance(r, Cap)]
        if caps:
            lowest_cap = min(c.amount for c in caps)
            subtotal = sum(nets, Decimal("0"))
            if subtotal > lowest_cap:
                excess = subtotal - lowest_cap
                allocated_excess = allocate(excess, nets, keys)
                nets = [money(val - exc) for val, exc in zip(nets, allocated_excess)]
        
        # Step 5: Summed Taxes
        taxes = [r for r in rules.rules if isinstance(r, Tax)]
        line_taxes = [Decimal("0.00") for _ in usage]
        if taxes:
            total_tax_rate = sum(t.rate for t in taxes)
            subtotal = sum(nets, Decimal("0"))
            aggregate_tax = money(subtotal * total_tax_rate)
            line_taxes = allocate(aggregate_tax, nets, keys)
        
        items = tuple(
            LineItem(
                line.key,
                line.description,
                line.quantity,
                base,
                net,
                tax,
                money(net + tax),
            )
            for line, base, net, tax in zip(usage, bases, nets, line_taxes)
        )
        return Invoice(
            invoice_id,
            account_id,
            period,
            usage,
            rules,
            items,
            money(sum((item.total for item in items), Decimal("0"))),
            selected.key if selected else None,
            non_selected,
        )

    def price_period(
        self,
        account: Account,
        period: Period,
        usage: tuple[UsageLine, ...],
        rule_set: RuleSet,
    ) -> Invoice:
        invoice = self._build(
            account.account_id,
            period,
            usage,
            rule_set,
            f"INV-{account.account_id}-{period.key}",
        )
        account.invoices[period.key] = invoice
        account._base_states[period.key] = (period, usage, rule_set)
        return invoice

    def reprice(
        self,
        invoice: Invoice,
        usage: tuple[UsageLine, ...],
        rule_set: RuleSet,
    ) -> Invoice:
        return self._build(
            invoice.account_id, invoice.period, usage, rule_set, invoice.invoice_id
        )

    def issue(self, account: Account, invoice: Invoice) -> None:
        if invoice.closed:
            return
        invoice.closed = True
        invoice.issued_total = invoice.total
        account.billing_entries.append(
            BillingEntry(
                f"BE-{invoice.invoice_id}",
                "invoice",
                invoice.invoice_id,
                invoice.total,
                invoice.period.key,
                invoice.invoice_id,
            )
        )
        account.balance = money(account.balance + invoice.total)
