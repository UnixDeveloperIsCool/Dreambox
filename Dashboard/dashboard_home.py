from fastapi import APIRouter, Request
from Dashboard.style import render
from Dashboard.permissions import require, is_admin_email
#from config.roles import ROLE_PRESETS
from roles import ROLE_PERMISSIONS, AccountType


router = APIRouter()

@router.get("/dashboard")
def dashboard(request: Request):
    require(request, "can_view_basic_dashboard")
    user = request.state.user
    role = ROLE_PRESETS.get(user["account_type"], {})

    tiles = []

    # Partners/admins: add games + view stats
    if role.get("can_manage_games"):
        tiles.append(("Games / Projects", "/projects", "Add games (partners). Admins can also remove."))
    if role.get("can_view_game_data"):
        tiles.append(("Game Data", "/games", "Upload/view stats that power campaign targets."))

    # Brands/finance/admin: campaign + billing
    if role.get("can_view_brand_campaigns"):
        tiles.append(("Campaign Projects", "/campaigns", "Projects/campaigns linked to one or more games."))
    if role.get("can_pay_for_products"):
        tiles.append(("Billing", "/billing", "One-off invoices + Stripe subscriptions."))

    # Admin
    if role.get("can_admin") or is_admin_email(user.get("email","")):
        tiles.append(("Admin", "/admin", "Create projects, quote, invoice, manage access."))

    tile_html = "".join(
        f"""<a class="tile" href="{u}">
              <h3>{t}</h3><p>{d}</p>
            </a>"""
        for t,u,d in tiles
    )

    body = f"""
    <div class="shell">
      <h1>Dashboard</h1>
      <div class="grid">{tile_html}</div>
    </div>
    """
    return render("Dashboard", body)
