from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from pricing.models import Account

VIEWPORTS = ("phone", "tablet")


@dataclass(frozen=True)
class Node:
    role: str
    label: str = ""
    value: str | None = None
    ref: str | None = None
    collapsed: bool = False
    children: tuple["Node", ...] = ()


def build_statement(
    account: Account, period_key: str, viewport: str = "phone"
) -> Node:
    if viewport not in VIEWPORTS:
        raise ValueError("unknown viewport")
        
    invoice = account.invoices[period_key]
    latest = account.statement_runs[-1] if account.statement_runs else None
    
    # Calculate settled vs pending totals for visible summary
    settled_total = Decimal("0.00")
    pending_total = Decimal("0.00")
    
    settled_corrections = []
    pending_corrections = []
    
    for record in account.adjustment_records:
        if record.original_invoice_id == invoice.invoice_id:
            # Find if settled in a run
            run_id = None
            for run in account.statement_runs:
                if run.status == "issued" and run.previous_cutoff_ordinal < record.acceptance_ordinal <= run.cutoff_ordinal:
                    run_id = run.run_id
                    break
            
            if run_id is not None:
                settled_total += record.delta
                settled_corrections.append(
                    Node(
                        "correction",
                        "Correction detail",
                        str(record.delta),
                        record.adjustment_id,
                        children=(
                            Node("settlement", f"Settled in {run_id}", run_id, ref=run_id),
                        ),
                    )
                )
            else:
                pending_total += record.delta
                pending_corrections.append(
                    Node(
                        "pending",
                        "Pending correction",
                        "pending",
                        record.adjustment_id,
                    )
                )
                
    children = [
        Node("header", f"Billing period {invoice.period.key}"),
        Node(
            "group",
            "Charges",
            children=tuple(
                Node("line", item.description, str(item.total))
                for item in invoice.line_items
            ),
        ),
        Node(
            "issued_amount",
            "Original invoice total",
            str(invoice.issued_total or invoice.total),
        ),
    ]
    
    if settled_total != Decimal("0.00"):
        children.append(Node("line", "Settled corrections", str(settled_total)))
        
    if pending_total != Decimal("0.00"):
        children.append(Node("line", "Pending corrections", str(pending_total)))
        
    if latest:
        children.append(
            Node(
                "run",
                f"As of statement run {latest.run_number}",
                str(account.balance),
                latest.run_id,
            )
        )
    else:
        children.append(
            Node(
                "run",
                "Current statement",
                str(account.balance),
                None,
            )
        )
        
    # Tomas's Calm Bill: detailed correction history is collapsed by default
    if settled_corrections:
        children.append(
            Node(
                "group",
                "Settled corrections detail",
                collapsed=True,
                children=tuple(settled_corrections),
            )
        )
        
    if pending_corrections:
        children.append(
            Node(
                "group",
                "Corrections pending next run",
                collapsed=True,
                children=tuple(pending_corrections),
            )
        )
        
    # Section 6: Inline Statement Run Summaries
    summary_nodes = []
    for run in account.statement_runs:
        if run.reconciliation_summary is not None:
            run_summary_children = []
            for entry in run.reconciliation_summary:
                run_summary_children.append(
                    Node(
                        "line",
                        f"Invoice {entry.invoice_id} ({entry.member_count} items)",
                        str(entry.member_delta_total),
                    )
                )
            if run_summary_children:
                summary_nodes.append(
                    Node(
                        "group",
                        f"Run summary for {run.run_id}",
                        collapsed=False,
                        children=tuple(run_summary_children),
                    )
                )
    if summary_nodes:
        children.append(
            Node(
                "group",
                "Statement Run Summaries",
                collapsed=False,
                children=tuple(summary_nodes),
            )
        )
        
    children.append(Node("amount_due", "Amount due", str(invoice.total)))
    
    return Node(
        "statement", f"Statement {invoice.invoice_id}", children=tuple(children)
    )


def _render(node: Node) -> str:
    attrs = f' data-role="{node.role}"'
    if node.ref is not None:
        attrs += f' data-ref="{node.ref}"'
    if node.collapsed:
        attrs += ' data-collapsed="true"'
    label = f'<span class="label">{node.label}</span>' if node.label else ""
    value = (
        f'<span class="value">{node.value}</span>'
        if node.value is not None
        else ""
    )
    return f"<div{attrs}>{label}{value}{''.join(_render(c) for c in node.children)}</div>"


def render_html(node: Node, viewport: str = "phone") -> str:
    if viewport not in VIEWPORTS:
        raise ValueError("unknown viewport")
    
    html = (
        f'<html><head><style>'
        f'body {{ font-family: monospace; padding: 20px; max-width: 100%; box-sizing: border-box; }}'
        f'.viewport-phone {{ max-width: 320px; margin: 0 auto; }}'
        f'.viewport-tablet {{ max-width: 640px; margin: 0 auto; }}'
        f'[data-role="statement"] {{ border: 1px solid #ccc; padding: 15px; border-radius: 4px; background: #fff; }}'
        f'[data-role="header"] {{ font-size: 1.2em; font-weight: bold; margin-bottom: 15px; border-bottom: 2px solid #333; padding-bottom: 5px; }}'
        f'[data-role="group"] {{ margin: 10px 0; border: 1px dashed #eee; padding: 10px; }}'
        f'[data-role="line"], [data-role="issued_amount"], [data-role="amount_due"], [data-role="run"] {{ display: flex; justify-content: space-between; margin: 5px 0; }}'
        f'[data-role="amount_due"] {{ font-weight: bold; font-size: 1.1em; border-top: 1px solid #333; padding-top: 5px; margin-top: 15px; }}'
        f'.label {{ color: #555; }}'
        f'.value {{ font-weight: bold; }}'
        f'.footer {{ margin-top: 20px; font-size: 0.8em; text-align: center; color: #777; border-top: 1px solid #eee; padding-top: 10px; }}'
        f'</style></head>'
        f'<body class="statement viewport-{viewport}">'
        f"{_render(node)}"
        f'<div class="footer">Billing Dept Fax: 1-800-555-0199 | Page i</div>'
        f'</body></html>'
    )
    return html
