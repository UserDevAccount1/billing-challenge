import json
from decimal import Decimal
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from pricing import (
    Account,
    Adjustment,
    Period,
    PricingEngine,
    RuleSet,
    UsageLine,
    UsageTier,
    Promotion,
    Credit,
    Cap,
    Tax,
)
from adjustments import AdjustmentIntake
from statement import build_statement, render_html

# Global state to act as our database for the demo/challenge
ACCOUNTS = {}
ENGINE = PricingEngine()
INTAKE = AdjustmentIntake(ENGINE)

def decimal_serializer(obj):
    if isinstance(obj, Decimal):
        return str(obj)
    raise TypeError(f"Type {type(obj)} not serializable")

def init_demo_account():
    account = Account("acct-demo", "credit_forward")
    period = Period("2026-06", "2026-06-01", "2026-07-01")
    usage = (
        UsageLine("api", "API calls", Decimal("12")),
        UsageLine("storage", "Storage (GB)", Decimal("5")),
    )
    rules = RuleSet(
        "standard",
        "2026-01-01",
        (
            UsageTier(Decimal("10"), Decimal("2.00")),
            UsageTier(None, Decimal("1.50")),
        ),
        (
            Promotion("promo-10", Decimal("0.10"), "stackable"),
            Promotion("promo-exclusive-15", Decimal("0.15"), "exclusive"),
            Promotion("promo-exclusive-20", Decimal("0.20"), "exclusive"),
            Credit("credit-welcome", Decimal("5.00")),
            Cap("cap-max", Decimal("50.00")),
            Tax("tax-vat", Decimal("0.05")),
        )
    )
    ENGINE.price_period(account, period, usage, rules)
    ENGINE.issue(account, account.invoices["2026-06"])
    ACCOUNTS[account.account_id] = account

init_demo_account()

def serialize_invoice(invoice):
    if invoice is None:
        return None
    return {
        "invoice_id": invoice.invoice_id,
        "account_id": invoice.account_id,
        "period": {
            "key": invoice.period.key,
            "starts_on": invoice.period.starts_on,
            "ends_on": invoice.period.ends_on,
        },
        "usage": [{"key": u.key, "description": u.description, "quantity": str(u.quantity)} for u in invoice.usage],
        "rule_set": {
            "key": invoice.rule_set.key,
            "effective_from": invoice.rule_set.effective_from,
        },
        "line_items": [
            {
                "usage_key": item.usage_key,
                "description": item.description,
                "quantity": str(item.quantity),
                "base": str(item.base),
                "net": str(item.net),
                "tax": str(item.tax),
                "total": str(item.total),
            }
            for item in invoice.line_items
        ],
        "total": str(invoice.total),
        "selected_exclusive_promotion": invoice.selected_exclusive_promotion,
        "non_selected_exclusive_promotions": invoice.non_selected_exclusive_promotions,
        "closed": invoice.closed,
        "issued_total": str(invoice.issued_total) if invoice.issued_total else None,
    }

def serialize_run(run):
    return {
        "run_id": run.run_id,
        "account_id": run.account_id,
        "run_number": run.run_number,
        "operation_id": run.operation_id,
        "predecessor_run_id": run.predecessor_run_id,
        "previous_cutoff_ordinal": run.previous_cutoff_ordinal,
        "cutoff_ordinal": run.cutoff_ordinal,
        "status": run.status,
        "membership": [
            {
                "adjustment_id": m.adjustment_id,
                "acceptance_ordinal": m.acceptance_ordinal,
                "original_invoice_id": m.original_invoice_id,
                "record_id": m.record_id,
            }
            for m in run.membership
        ],
        "recorded_demand": str(run.recorded_demand) if run.recorded_demand else None,
        "incremental_demand": str(run.incremental_demand) if run.incremental_demand else None,
        "reconciliation_summary": [
            {
                "invoice_id": s.invoice_id,
                "member_count": s.member_count,
                "member_delta_total": str(s.member_delta_total),
            }
            for s in run.reconciliation_summary
        ] if run.reconciliation_summary is not None else None,
    }

def serialize_account(account):
    return {
        "account_id": account.account_id,
        "settlement_policy": account.settlement_policy,
        "balance": str(account.balance),
        "amount_due": str(account.amount_due),
        "summaries_adopted_id": account.summaries_adopted_id,
        "summaries_adopted_ordinal": account.summaries_adopted_ordinal,
        "invoices": {k: serialize_invoice(v) for k, v in account.invoices.items()},
        "received_adjustments": [
            {
                "adjustment_id": adj.adjustment_id,
                "account_id": adj.account_id,
                "period_key": adj.period_key,
                "kind": adj.kind,
                "effective_at": adj.effective_at,
                "received_at": adj.received_at,
                "amount": str(adj.amount) if adj.amount is not None else None,
                "usage_key": adj.usage_key,
                "quantity": str(adj.quantity) if adj.quantity is not None else None,
                "target_period_key": adj.target_period_key,
                "subject_key": adj.subject_key,
                "replaces_adjustment_id": adj.replaces_adjustment_id,
                "withdraws_adjustment_id": adj.withdraws_adjustment_id,
            }
            for adj in account.received_adjustments
        ],
        "adjustment_records": [
            {
                "record_id": rec.record_id,
                "adjustment_id": rec.adjustment_id,
                "acceptance_ordinal": rec.acceptance_ordinal,
                "original_invoice_id": rec.original_invoice_id,
                "target_period": rec.target_period,
                "delta": str(rec.delta),
                "prior_recorded_total": str(rec.prior_recorded_total),
                "resulting_total": str(rec.resulting_total),
                "policy": rec.policy,
                "effective_at": rec.effective_at,
                "applied_period": rec.applied_period,
                "replacement_invoice_id": rec.replacement_invoice_id,
                "void_amount": str(rec.void_amount) if rec.void_amount else None,
                "reissue_amount": str(rec.reissue_amount) if rec.reissue_amount else None,
            }
            for rec in account.adjustment_records
        ],
        "statement_runs": [serialize_run(run) for run in account.statement_runs],
    }

def serialize_node(node):
    return {
        "role": node.role,
        "label": node.label,
        "value": node.value,
        "ref": node.ref,
        "collapsed": node.collapsed,
        "children": [serialize_node(c) for c in node.children],
    }

@require_http_methods(["GET"])
def get_account(request):
    account_id = request.GET.get("account_id", "acct-demo")
    if account_id not in ACCOUNTS:
        return JsonResponse({"error": "Account not found"}, status=404)
    return JsonResponse(serialize_account(ACCOUNTS[account_id]))

@csrf_exempt
@require_http_methods(["POST"])
def deliver_adjustment(request):
    try:
        data = json.loads(request.body)
        account_id = data.get("account_id", "acct-demo")
        if account_id not in ACCOUNTS:
            return JsonResponse({"error": "Account not found"}, status=404)
        
        account = ACCOUNTS[account_id]
        
        # Build Adjustment object
        promotion = None
        if data.get("promotion"):
            p_data = data["promotion"]
            promotion = Promotion(
                p_data["key"],
                Decimal(str(p_data["percent"])),
                p_data["kind"],
                tuple(p_data["applies_to_usage_keys"]) if p_data.get("applies_to_usage_keys") else None
            )
            
        adjustment = Adjustment(
            adjustment_id=data["adjustment_id"],
            account_id=account_id,
            period_key=data["period_key"],
            kind=data["kind"],
            effective_at=data["effective_at"],
            received_at=data["received_at"],
            amount=Decimal(str(data["amount"])) if data.get("amount") is not None else None,
            usage_key=data.get("usage_key"),
            quantity=Decimal(str(data["quantity"])) if data.get("quantity") is not None else None,
            promotion=promotion,
            target_period_key=data.get("target_period_key"),
            subject_key=data.get("subject_key"),
            replaces_adjustment_id=data.get("replaces_adjustment_id"),
            withdraws_adjustment_id=data.get("withdraws_adjustment_id"),
        )
        
        record = INTAKE.deliver(account, adjustment)
        
        return JsonResponse({
            "success": True,
            "record": {
                "record_id": record.record_id,
                "delta": str(record.delta),
                "resulting_total": str(record.resulting_total),
            } if record else None,
            "account": serialize_account(account)
        })
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)

@csrf_exempt
@require_http_methods(["POST"])
def issue_run(request):
    try:
        data = json.loads(request.body)
        account_id = data.get("account_id", "acct-demo")
        operation_id = data["operation_id"]
        if account_id not in ACCOUNTS:
            return JsonResponse({"error": "Account not found"}, status=404)
        
        account = ACCOUNTS[account_id]
        run = INTAKE.issue_statement_run(account, operation_id)
        
        return JsonResponse({
            "success": True,
            "run": serialize_run(run),
            "account": serialize_account(account)
        })
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)

@csrf_exempt
@require_http_methods(["POST"])
def adopt_summaries(request):
    try:
        data = json.loads(request.body)
        account_id = data.get("account_id", "acct-demo")
        adoption_id = data["adoption_id"]
        if account_id not in ACCOUNTS:
            return JsonResponse({"error": "Account not found"}, status=404)
        
        account = ACCOUNTS[account_id]
        INTAKE.adopt_run_summaries(account, adoption_id)
        
        return JsonResponse({
            "success": True,
            "account": serialize_account(account)
        })
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)

@require_http_methods(["GET"])
def get_statement(request, period_key):
    account_id = request.GET.get("account_id", "acct-demo")
    viewport = request.GET.get("viewport", "phone")
    fmt = request.GET.get("format", "json")
    
    if account_id not in ACCOUNTS:
        return JsonResponse({"error": "Account not found"}, status=404)
        
    account = ACCOUNTS[account_id]
    if period_key not in account.invoices:
        return JsonResponse({"error": "Invoice not found for this period"}, status=404)
        
    try:
        tree = build_statement(account, period_key, viewport)
        if fmt == "html":
            html_content = render_html(tree, viewport)
            return HttpResponse(html_content, content_type="text/html")
        else:
            return JsonResponse(serialize_node(tree))
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)

@csrf_exempt
@require_http_methods(["POST"])
def reset_account(request):
    try:
        init_demo_account()
        return JsonResponse({"success": True, "account": serialize_account(ACCOUNTS["acct-demo"])})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)
