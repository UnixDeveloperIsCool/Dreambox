from fastapi import APIRouter, Request, HTTPException
from Dashboard.permissions import require, is_admin_email
from Dashboard.db import campaigns_db, init_campaigns_db

router = APIRouter()

@router.on_event("startup")
def _init():
    init_campaigns_db()

# NOTE:
# - One-off invoices: admin issues invoice record here after negotiations
# - Subscriptions: store stripe_customer_id + stripe_subscription_id and handle Stripe webhooks in your main app (recommended)

@router.get("/billing")
def billing_home(request: Request):
    require(request, "can_pay_for_products")
    return {"ok": True, "message": "Billing area (one-off invoices + subscriptions via Stripe)."}

@router.post("/billing/invoices")
def admin_issue_invoice(
    request: Request,
    project_id: int,
    billing_type: str,   # 'one_off' or 'subscription'
    amount: float,
    currency: str = "EUR",
    stripe_customer_id: str = "",
    stripe_invoice_id: str = "",
    stripe_subscription_id: str = "",
):
    user = request.state.user
    if not is_admin_email(user.get("email","")):
        require(request, "can_admin")

    if billing_type not in ("one_off", "subscription"):
        raise HTTPException(400, "billing_type must be one_off or subscription")

    with campaigns_db() as db:
        db.execute(
            """
            INSERT INTO invoices(project_id, billing_type, amount, currency, stripe_customer_id, stripe_invoice_id, stripe_subscription_id)
            VALUES(?,?,?,?,?,?,?)
            """,
            (project_id, billing_type, amount, currency,
             stripe_customer_id or None, stripe_invoice_id or None, stripe_subscription_id or None)
        )
        db.commit()

    return {"ok": True}

@router.get("/billing/invoices")
def list_invoices(request: Request):
    require(request, "can_pay_for_products")
    user = request.state.user
    with campaigns_db() as db:
        if is_admin_email(user.get("email","")):
            rows = db.execute("SELECT * FROM invoices ORDER BY id DESC").fetchall()
        else:
            # Only invoices for projects user can access
            rows = db.execute(
                """
                SELECT i.* FROM invoices i
                JOIN project_access a ON a.project_id = i.project_id
                WHERE a.user_email = ?
                ORDER BY i.id DESC
                """,
                (user["email"],)
            ).fetchall()
    return {"ok": True, "invoices": [dict(r) for r in rows]}
