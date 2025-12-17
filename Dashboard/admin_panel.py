from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from jose import jwt, JWTError

import sqlite3
import json
import os
from pathlib import Path

from roles import AccountType, ROLE_PERMISSIONS
from dashboard import BASE_STYLE, ME_ENDPOINT  # reuse your existing style + /auth/me path

router = APIRouter()

BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = BASE_DIR / "dreambox.db"
ROLES_JSON_PATH = BASE_DIR / "config" / "roles.json"
ADMINS_JSON_PATH = BASE_DIR / "config" / "admins.json"

# JWT (must match app.py)
SECRET_KEY = os.environ.get("SECRET_KEY", "CHANGE_ME_TO_A_LONG_RANDOM_SECRET")
ALGORITHM = "HS256"


def html_page(title: str, body: str) -> HTMLResponse:
    return HTMLResponse(
        f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{title}</title>
  {BASE_STYLE}
</head>
<body>
  <div class="shell">{body}</div>
</body>
</html>"""
    )


def db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def _load_admin_emails() -> set[str]:
    try:
        data = json.loads(ADMINS_JSON_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return set()
    except Exception:
        return set()

    if isinstance(data, dict):
        admins = data.get("admins", [])
    elif isinstance(data, list):
        admins = data
    else:
        admins = []

    return {str(e).strip().lower() for e in admins if str(e).strip()}


ADMIN_EMAILS = _load_admin_emails()


def _decode_token_get_user_id(token: str) -> int:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        sub = payload.get("sub")
        return int(sub)
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid or expired token")


def _get_bearer_token(request: Request) -> str:
    auth = request.headers.get("Authorization", "")
    if not auth.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    return auth.split(" ", 1)[1].strip()


def _get_current_user_row(request: Request) -> sqlite3.Row:
    token = _get_bearer_token(request)
    user_id = _decode_token_get_user_id(token)

    with db() as conn:
        row = conn.execute(
            "SELECT id, email, account_type, is_email_verified FROM users WHERE id=?",
            (user_id,),
        ).fetchone()

    if not row:
        raise HTTPException(status_code=401, detail="User not found")
    return row


def _require_admin(request: Request) -> sqlite3.Row:
    row = _get_current_user_row(request)
    email = (row["email"] or "").strip().lower()
    acct = (row["account_type"] or "")

    # allowlist always wins (admins.json)
    if email in ADMIN_EMAILS:
        return row

    # otherwise must be admin account type
    if "administrator" not in acct.lower():
        raise HTTPException(status_code=403, detail="Admin only")
    return row


def _is_admin_account_type(account_type: str) -> bool:
    return "administrator" in (account_type or "").lower()


def _safe_assignable_account_types() -> list[str]:
    """
    Roles you can assign via UI/API.
    Administrator is intentionally excluded.
    """
    return [
        AccountType.ACCOUNT_PENDING.value,
        AccountType.PARTNER.value,
        AccountType.BUSINESS.value,
        AccountType.BRAND_SPECIALIST.value,
        AccountType.BRAND_PARTNER.value,
        AccountType.BRAND.value,
    ]


def _cleanup_user_data(conn: sqlite3.Connection, user_id: int) -> None:
    """
    Best-effort cleanup of rows tied to a user.
    Only delete tables that definitely exist in your app.py init_db().
    """
    cur = conn.cursor()

    # If you add more user-linked tables later, add them here.
    cur.execute("DELETE FROM games WHERE owner_user_id=?", (user_id,))
    cur.execute("DELETE FROM brands WHERE owner_user_id=?", (user_id,))
    cur.execute("DELETE FROM survey_submissions WHERE user_id=?", (user_id,))
    cur.execute("DELETE FROM zoom_meetings WHERE user_id=?", (user_id,))

    # campaigns are tied to brands, so deleting brands first should orphan them if FK not cascading.
    # clean orphan campaigns too:
    cur.execute("DELETE FROM campaigns WHERE brand_id NOT IN (SELECT id FROM brands)")

    conn.commit()


# ----------------------------
# JS boot (token + /auth/me) - injected into every page
# ----------------------------
JS_BOOT = """
<script>
  const token = localStorage.getItem("dreambox_token");
  if(!token) window.location.href = "/portal";

  async function me(){
    const r = await fetch("__ME_ENDPOINT__", {
      headers: { "Authorization": "Bearer " + token }
    });
    if(!r.ok) {
      localStorage.removeItem("dreambox_token");
      window.location.href = "/portal";
      return null;
    }
    return await r.json();
  }

  async function requireAdmin(){
    const user = await me();
    if(!user) return;
    const acct = (user.account_type || "").toLowerCase();
    if(!acct.includes("administrator")){
      window.location.href = "/portal-home";
      return;
    }
    const el = document.getElementById("adminEmailLine");
    if(el) el.textContent = "Signed in as: " + (user.email || "—");
  }

  async function api(path, opts={}){
    opts.headers = Object.assign({}, opts.headers || {}, {
      "Authorization": "Bearer " + token,
      "Content-Type": "application/json"
    });
    const r = await fetch(path, opts);
    const text = await r.text();
    let data = null;
    try { data = JSON.parse(text); } catch(e){}
    if(!r.ok) throw new Error((data && data.detail) || text || ("HTTP " + r.status));
    return data;
  }

  function logout(){
    localStorage.removeItem("dreambox_token");
    window.location.href = "/portal";
  }
</script>
""".replace("__ME_ENDPOINT__", ME_ENDPOINT)


# ============================================================
# ADMIN PAGES
# ============================================================

@router.get("/admin/approvals", response_class=HTMLResponse)
def admin_approvals_page():
    body = """
    <div class="topbar">
      <div>
        <div class="kicker">Administrator • Pending Approvals</div>
        <h1>Pending approvals</h1>
        <p class="sub">Approve accounts by changing their account type.</p>
        <div class="badge"><span class="dot" style="background:#60a5fa;box-shadow:0 0 0 4px rgba(96,165,250,0.10);"></span> Admin access</div>
      </div>
      <div class="actions">
        <a class="ghost" href="/admin">Back</a>
        <button class="ghost" onclick="logout()">Log out</button>
      </div>
    </div>

    <div class="panel">
      <div class="card">
        <h3>Accounts pending</h3>
        <p class="sub" id="adminEmailLine">Signed in as: —</p>
        <div id="list"></div>
      </div>
    </div>
    """ + JS_BOOT + """
    <script>
      function row(u){
        const types = [
          "PartnerAccount","BusinessAccount","BrandSpecialistAccount","BrandPartnerAccount","BrandAccount"
        ];
        const opts = types.map(v => `<option value="${v}">${v}</option>`).join("");

        return `
          <div class="card" style="margin-top:12px;">
            <h3>${u.email}</h3>
            <p class="sub">Current: ${u.account_type}</p>
            <div style="display:flex; gap:10px; flex-wrap:wrap; align-items:center;">
              <select id="sel_${u.id}" style="padding:10px;border-radius:12px;background:#1A1A1A;color:#fff;border:1px solid rgba(255,255,255,.18);">
                ${opts}
              </select>
              <button class="btn" onclick="approve(${u.id})">Approve</button>
            </div>
            ${u.is_protected ? "<p class='tiny' style='margin-top:10px;color:#8a8a8a;'>Protected admin account — cannot be changed.</p>" : ""}
          </div>
        `;
      }

      async function load(){
        await requireAdmin();
        const data = await api("/admin/api/pending");
        document.getElementById("list").innerHTML =
          (data.users.length ? data.users.map(row).join("") : "<p class='sub'>No pending accounts.</p>");
      }

      async function approve(id){
        const v = document.getElementById("sel_" + id).value;
        await api("/admin/api/set-account-type", {
          method:"POST",
          body: JSON.stringify({ user_id:id, account_type:v })
        });
        load();
      }

      load();
    </script>
    """
    return html_page("Admin • Approvals", body)


@router.get("/admin/users", response_class=HTMLResponse)
def admin_users_page():
    body = """
    <div class="topbar">
      <div>
        <div class="kicker">Administrator • User Management</div>
        <h1>User management</h1>
        <p class="sub">Search by email and manage roles. Admin accounts are protected.</p>
        <div class="badge"><span class="dot" style="background:#60a5fa;box-shadow:0 0 0 4px rgba(96,165,250,0.10);"></span> Admin access</div>
      </div>
      <div class="actions">
        <a class="ghost" href="/admin">Back</a>
        <button class="ghost" onclick="logout()">Log out</button>
      </div>
    </div>

    <div class="panel">
      <div class="card">
        <h3>Search</h3>
        <p class="sub" id="adminEmailLine">Signed in as: —</p>

        <div style="display:flex; gap:10px; flex-wrap:wrap;">
          <input id="q" placeholder="email contains..." style="flex:1; min-width:240px;">
          <button class="btn" onclick="search()">Search</button>
          <button class="ghost" onclick="loadAll()">All accounts</button>
        </div>

        <div id="results"
             style="margin-top:12px; max-height:420px; overflow:auto; padding-right:6px;">
        </div>
      </div>
    </div>

    <style>
      #results::-webkit-scrollbar { width: 10px; }
      #results::-webkit-scrollbar-track { background: rgba(255,255,255,0.04); border-radius: 999px; }
      #results::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.12); border-radius: 999px; }
      #results::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.18); }
    </style>
    """ + JS_BOOT + """
    <script>
      function userCard(u){
        const types = [
          "AccountPending","PartnerAccount","BusinessAccount","BrandSpecialistAccount",
          "BrandPartnerAccount","BrandAccount"
        ];

        const opts = types.map(v => {
          const sel = (u.account_type === v) ? "selected" : "";
          return `<option value="${v}" ${sel}>${v}</option>`;
        }).join("");

        const locked = u.is_protected ? "disabled" : "";
        const saveBtn = u.is_protected
          ? `<span class="pill">Protected</span>`
          : `<button class="btn" onclick="save(${u.id})">Save</button>`;

        const deleteBtn = u.is_protected
          ? ""
          : `<button class="ghost" onclick="delUser(${u.id}, '${(u.email||'').replace(/'/g, "\\'")}')">Delete user</button>`;

        return `
          <div class="card" style="margin-top:12px;">
            <h3>${u.email}</h3>
            <p class="sub">ID: ${u.id} • Current: ${u.account_type}</p>
            <div style="display:flex; gap:10px; flex-wrap:wrap; align-items:center;">
              <select ${locked} id="sel_${u.id}" style="padding:10px;border-radius:12px;background:#1A1A1A;color:#fff;border:1px solid rgba(255,255,255,.18);">
                ${opts}
              </select>
              ${saveBtn}
              ${deleteBtn}
            </div>
            ${u.is_protected ? "<p class='tiny' style='margin-top:10px;color:#8a8a8a;'>Protected admin account — cannot be changed or deleted.</p>" : ""}
          </div>
        `;
      }

      async function loadAll(){
        await requireAdmin();
        const data = await api("/admin/api/search?query=");
        document.getElementById("results").innerHTML =
          (data.users.length ? data.users.map(userCard).join("") : "<p class='sub'>No results.</p>");
      }

      async function search(){
        await requireAdmin();
        const q = document.getElementById("q").value || "";
        const data = await api("/admin/api/search?query=" + encodeURIComponent(q));
        document.getElementById("results").innerHTML =
          (data.users.length ? data.users.map(userCard).join("") : "<p class='sub'>No results.</p>");
      }

      async function save(id){
        const v = document.getElementById("sel_" + id).value;
        await api("/admin/api/set-account-type", {
          method:"POST",
          body: JSON.stringify({ user_id:id, account_type:v })
        });
        const q = document.getElementById("q").value || "";
        if(q.trim().length) search();
        else loadAll();
      }

      async function delUser(id, email){
        if(!confirm("Delete user: " + email + " ?\\n\\nThis removes their account and linked data.")) return;
        await api("/admin/api/delete-user", {
          method:"POST",
          body: JSON.stringify({ user_id:id })
        });
        const q = document.getElementById("q").value || "";
        if(q.trim().length) search();
        else loadAll();
      }

      (async () => {
        await requireAdmin();
        loadAll();
      })();
    </script>
    """
    return html_page("Admin • Users", body)


@router.get("/admin/roles", response_class=HTMLResponse)
def admin_roles_page():
    body = """
    <div class="topbar">
      <div>
        <div class="kicker">Administrator • Roles Config</div>
        <h1>Roles config</h1>
        <p class="sub">Viewing merged permissions (defaults + config/roles.json overrides).</p>
      </div>
      <div class="actions">
        <a class="ghost" href="/admin">Back</a>
        <button class="ghost" onclick="logout()">Log out</button>
      </div>
    </div>

    <div class="panel">
      <div class="card">
        <h3>Roles</h3>
        <p class="sub" id="adminEmailLine">Signed in as: —</p>
        <pre id="json" style="white-space:pre-wrap; font-size:12px; color:#d6d6d6;"></pre>
      </div>
    </div>
    """ + JS_BOOT + """
    <script>
      async function load(){
        await requireAdmin();
        const data = await api("/admin/api/roles");
        document.getElementById("json").textContent = JSON.stringify(data, null, 2);
      }
      load();
    </script>
    """
    return html_page("Admin • Roles", body)


@router.get("/admin/logs", response_class=HTMLResponse)
def admin_logs_page():
    body = """
    <div class="topbar">
      <div>
        <div class="kicker">Administrator • Audit Logs</div>
        <h1>Audit logs</h1>
        <p class="sub">Placeholder page for now.</p>
      </div>
      <div class="actions">
        <a class="ghost" href="/admin">Back</a>
        <button class="ghost" onclick="logout()">Log out</button>
      </div>
    </div>

    <div class="panel">
      <div class="card">
        <h3>Status</h3>
        <p class="sub" id="adminEmailLine">Signed in as: —</p>
        <p class="tiny">Coming next: record admin actions like approvals and account changes.</p>
      </div>
    </div>
    """ + JS_BOOT + """
    <script>requireAdmin();</script>
    """
    return html_page("Admin • Logs", body)


@router.get("/admin/support", response_class=HTMLResponse)
def admin_support_page():
    body = """
    <div class="topbar">
      <div>
        <div class="kicker">Administrator • Support Inbox</div>
        <h1>Support inbox</h1>
        <p class="sub">Placeholder page for now.</p>
      </div>
      <div class="actions">
        <a class="ghost" href="/admin">Back</a>
        <button class="ghost" onclick="logout()">Log out</button>
      </div>
    </div>

    <div class="panel">
      <div class="card">
        <h3>Status</h3>
        <p class="sub" id="adminEmailLine">Signed in as: —</p>
        <p class="tiny">You can wire this to chat threads later.</p>
      </div>
    </div>
    """ + JS_BOOT + """
    <script>requireAdmin();</script>
    """
    return html_page("Admin • Support", body)


@router.get("/admin/system", response_class=HTMLResponse)
def admin_system_page():
    body = """
    <div class="topbar">
      <div>
        <div class="kicker">Administrator • System</div>
        <h1>System</h1>
        <p class="sub">Quick health overview.</p>
      </div>
      <div class="actions">
        <a class="ghost" href="/admin">Back</a>
        <button class="ghost" onclick="logout()">Log out</button>
      </div>
    </div>

    <div class="panel">
      <div class="card">
        <h3>Health</h3>
        <p class="sub" id="adminEmailLine">Signed in as: —</p>
        <pre id="health" style="white-space:pre-wrap; font-size:12px; color:#d6d6d6;"></pre>
      </div>
    </div>
    """ + JS_BOOT + """
    <script>
      async function load(){
        await requireAdmin();
        const data = await api("/admin/api/health");
        document.getElementById("health").textContent = JSON.stringify(data, null, 2);
      }
      load();
    </script>
    """
    return html_page("Admin • System", body)


# ============================================================
# ADMIN API
# ============================================================

@router.get("/admin/api/pending")
def api_pending(request: Request):
    _require_admin(request)

    with db() as conn:
        rows = conn.execute(
            "SELECT id, email, account_type FROM users WHERE account_type = ? ORDER BY id DESC",
            (AccountType.ACCOUNT_PENDING.value,),
        ).fetchall()

    users = []
    for r in rows:
        d = dict(r)
        d["is_protected"] = str(d.get("email", "")).lower() in ADMIN_EMAILS
        users.append(d)

    return {"users": users}


@router.get("/admin/api/search")
def api_search(request: Request, query: str = ""):
    _require_admin(request)

    q = (query or "").strip().lower()
    like = f"%{q}%"

    with db() as conn:
        rows = conn.execute(
            "SELECT id, email, account_type FROM users WHERE lower(email) LIKE ? ORDER BY id DESC LIMIT 200",
            (like,),
        ).fetchall()

    users = []
    for r in rows:
        d = dict(r)
        d["is_protected"] = str(d.get("email", "")).lower() in ADMIN_EMAILS
        users.append(d)

    return {"users": users}


@router.post("/admin/api/set-account-type")
async def api_set_account_type(request: Request):
    admin_row = _require_admin(request)

    payload = await request.json()
    user_id = int(payload.get("user_id"))
    account_type = str(payload.get("account_type") or "").strip()

    # hard block assigning any administrator role
    if _is_admin_account_type(account_type):
        raise HTTPException(status_code=403, detail="Administrator role cannot be assigned here.")

    allowed = set(_safe_assignable_account_types())
    if account_type not in allowed:
        raise HTTPException(status_code=400, detail="Invalid account_type")

    with db() as conn:
        target = conn.execute(
            "SELECT id, email, account_type FROM users WHERE id=?",
            (user_id,),
        ).fetchone()

        if not target:
            raise HTTPException(status_code=404, detail="User not found")

        # protect admin emails from being changed
        target_email = str(target["email"] or "").lower()
        if target_email in ADMIN_EMAILS:
            raise HTTPException(status_code=403, detail="This account is protected.")

        # also protect administrator-type accounts
        if _is_admin_account_type(str(target["account_type"] or "")):
            raise HTTPException(status_code=403, detail="This account is protected.")

        # prevent admin editing self via this endpoint (optional but safe)
        if int(target["id"]) == int(admin_row["id"]):
            raise HTTPException(status_code=403, detail="Cannot change your own account type here.")

        conn.execute(
            "UPDATE users SET account_type = ? WHERE id = ?",
            (account_type, user_id),
        )
        conn.commit()

    return {"ok": True}


@router.post("/admin/api/delete-user")
async def api_delete_user(request: Request):
    admin_row = _require_admin(request)

    payload = await request.json()
    user_id = int(payload.get("user_id"))

    # cannot delete self
    if int(user_id) == int(admin_row["id"]):
        raise HTTPException(status_code=403, detail="You cannot delete your own account.")

    with db() as conn:
        target = conn.execute(
            "SELECT id, email, account_type FROM users WHERE id=?",
            (user_id,),
        ).fetchone()

        if not target:
            raise HTTPException(status_code=404, detail="User not found")

        target_email = str(target["email"] or "").lower()
        target_type = str(target["account_type"] or "")

        # protect admin allowlist
        if target_email in ADMIN_EMAILS:
            raise HTTPException(status_code=403, detail="This account is protected and cannot be deleted.")

        # protect any administrator-type account
        if _is_admin_account_type(target_type):
            raise HTTPException(status_code=403, detail="Administrator accounts cannot be deleted here.")

        # cleanup related data first (best-effort)
        cur = conn.cursor()
        cur.execute("DELETE FROM games WHERE owner_user_id=?", (user_id,))
        cur.execute("DELETE FROM brands WHERE owner_user_id=?", (user_id,))
        cur.execute("DELETE FROM survey_submissions WHERE user_id=?", (user_id,))
        cur.execute("DELETE FROM zoom_meetings WHERE user_id=?", (user_id,))
        cur.execute("DELETE FROM campaigns WHERE brand_id NOT IN (SELECT id FROM brands)")

        # finally delete user
        cur.execute("DELETE FROM users WHERE id=?", (user_id,))
        conn.commit()

    return {"ok": True}


@router.get("/admin/api/roles")
def api_roles(request: Request):
    _require_admin(request)

    merged = {k.value: v for k, v in ROLE_PERMISSIONS.items()}

    overrides = {}
    if ROLES_JSON_PATH.exists():
        overrides = json.loads(ROLES_JSON_PATH.read_text(encoding="utf-8"))

    return {"merged": merged, "overrides_config_roles_json": overrides}


@router.get("/admin/api/health")
def api_health(request: Request):
    _require_admin(request)

    with db() as conn:
        user_count = conn.execute("SELECT COUNT(*) AS n FROM users").fetchone()["n"]
        pending = conn.execute(
            "SELECT COUNT(*) AS n FROM users WHERE account_type=?",
            (AccountType.ACCOUNT_PENDING.value,),
        ).fetchone()["n"]

    return {
        "db_path": str(DB_PATH),
        "users_total": user_count,
        "users_pending": pending,
        "roles_json_exists": ROLES_JSON_PATH.exists(),
        "admins_json_exists": ADMINS_JSON_PATH.exists(),
        "admins_loaded": len(ADMIN_EMAILS),
    }
