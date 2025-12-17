from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from jose import jwt, JWTError

import os
import json
import sqlite3
from pathlib import Path

from dashboard import BASE_STYLE, ME_ENDPOINT  # reuse existing style and /auth/me path

router = APIRouter()

BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = BASE_DIR / "dreambox.db"
ADMINS_JSON_PATH = BASE_DIR / "config" / "admins.json"

# JWT must match app.py
SECRET_KEY = os.environ.get("SECRET_KEY", "CHANGE_ME_TO_A_LONG_RANDOM_SECRET")
ALGORITHM = "HS256"


def html_page(title: str, body: str) -> HTMLResponse:
    return HTMLResponse(f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{title}</title>
  {BASE_STYLE}
</head>
<body>
  <div class="shell">{body}</div>
</body>
</html>""")


def db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def _load_admin_emails() -> set[str]:
    try:
        data = json.loads(ADMINS_JSON_PATH.read_text(encoding="utf-8"))
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


def _get_bearer_token(request: Request) -> str:
    auth = request.headers.get("Authorization", "")
    if not auth.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    return auth.split(" ", 1)[1].strip()


def _decode_token_get_user_id(token: str) -> int:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        sub = payload.get("sub")
        return int(sub)
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid or expired token")


def _get_current_user_row(request: Request) -> sqlite3.Row:
    token = _get_bearer_token(request)
    user_id = _decode_token_get_user_id(token)

    with db() as conn:
        row = conn.execute(
            "SELECT id, email, account_type FROM users WHERE id=?",
            (user_id,),
        ).fetchone()

    if not row:
        raise HTTPException(status_code=401, detail="User not found")
    return row


def _require_admin(request: Request) -> sqlite3.Row:
    row = _get_current_user_row(request)
    email = (row["email"] or "").strip().lower()
    acct = (row["account_type"] or "")

    # allowlist always wins
    if email in ADMIN_EMAILS:
        return row

    if "administrator" not in acct.lower():
        raise HTTPException(status_code=403, detail="Admin only")
    return row


JS_BOOT = """
<script>
  const token = localStorage.getItem("dreambox_token");
  if(!token) window.location.href = "/portal";

  async function me(){{
    const r = await fetch("{ME_ENDPOINT}", {{
      headers: {{ "Authorization": "Bearer " + token }}
    }});
    if(!r.ok) {{
      localStorage.removeItem("dreambox_token");
      window.location.href = "/portal";
      return null;
    }}
    return await r.json();
  }}

  async function requireAdmin(){{
    const user = await me();
    if(!user) return;
    const acct = (user.account_type || "").toLowerCase();
    if(!acct.includes("administrator")){{
      window.location.href = "/portal-home";
      return;
    }}
    const el = document.getElementById("adminEmailLine");
    if(el) el.textContent = "Signed in as: " + (user.email || "—");
  }}

  async function api(path, opts={{}}){{
    opts.headers = Object.assign({{}}, opts.headers || {{}}, {{
      "Authorization": "Bearer " + token,
      "Content-Type": "application/json"
    }});
    const r = await fetch(path, opts);
    const text = await r.text();
    let data = null;
    try {{ data = JSON.parse(text); }} catch(e){{}}
    if(!r.ok) throw new Error((data && data.detail) || text || ("HTTP " + r.status));
    return data;
  }}

  function logout(){{
    localStorage.removeItem("dreambox_token");
    window.location.href = "/portal";
  }}
</script>
"""


@router.get("/admin/game-deletions", response_class=HTMLResponse)
def game_deletions_page():
    body = """
    <div class="topbar">
      <div>
        <div class="kicker">Administrator • Game deletion requests</div>
        <h1>Game deletion requests</h1>
        <p class="sub">Partners request deletion. Approve or reject here.</p>
        <div class="badge">
          <span class="dot" style="background:#60a5fa;box-shadow:0 0 0 4px rgba(96,165,250,0.10);"></span>
          Admin access
        </div>
      </div>
      <div class="actions">
        <a class="ghost" href="/admin">Admin dashboard</a>
        <button class="ghost" onclick="logout()">Log out</button>
      </div>
    </div>

    <div class="panel">
      <div class="card">
        <h3>Requests</h3>
        <p class="sub" id="adminEmailLine">Signed in as: —</p>
        <p class="tiny">Approve = delete the game row. Reject = clear the request flag.</p>
        <div id="wrap" style="margin-top:12px; max-height:420px; overflow:auto; padding-right:6px;"></div>
        <p class="tiny" id="err" style="color:#a0a0a0;"></p>
      </div>
    </div>

    {JS_BOOT}

    <script>
      function card(g){{
        const when = g.delete_requested_at ? g.delete_requested_at : "—";
        const url = g.game_url || ("https://www.roblox.com/games/" + (g.universe_id || ""));
        const name = g.name || "—";

        return `
          <div class="card" style="margin-top:12px;">
            <h3>${name}</h3>
            <p class="sub">Universe/Place: <strong>${g.universe_id}</strong> • Game ID: ${g.id}</p>
            <p class="tiny">Owner: ${g.owner_email || "—"} • Requested: ${when}</p>
            <div style="display:flex; gap:10px; flex-wrap:wrap; margin-top:10px;">
              <a class="ghost" style="padding:10px 14px;" href="${url}" target="_blank" rel="noreferrer">Open Roblox</a>
              <button class="btn" onclick="approve(${g.id})">Approve delete</button>
              <button class="ghost" onclick="reject(${g.id})">Reject</button>
            </div>
          </div>
        `;
      }}

      async function load(){{
        const err = document.getElementById("err");
        err.textContent = "";
        await requireAdmin();
        try{{
          const data = await api("/admin/api/game-delete-requests");
          const wrap = document.getElementById("wrap");
          if(!data.requests || !data.requests.length){{
            wrap.innerHTML = "<p class='sub'>No pending requests.</p>";
            return;
          }}
          wrap.innerHTML = data.requests.map(card).join("");
        }}catch(e){{
          err.textContent = String(e.message || e);
        }}
      }}

      async function approve(id){{
        if(!confirm("Approve deletion? This will permanently delete the game row.")) return;
        await api("/admin/api/game-delete-approve", {{
          method:"POST",
          body: JSON.stringify({{ game_id: id }})
        }});
        load();
      }}

      async function reject(id){{
        await api("/admin/api/game-delete-reject", {{
          method:"POST",
          body: JSON.stringify({{ game_id: id }})
        }});
        load();
      }}

      load();
    </script>
    """
    return html_page("Admin • Game deletion requests", body)


@router.get("/admin/api/game-delete-requests")
def api_list_requests(request: Request):
    _require_admin(request)
    with db() as conn:
        rows = conn.execute(
            """
            SELECT g.id, g.universe_id, g.name, g.game_url, g.delete_requested_at,
                   g.owner_user_id, u.email AS owner_email
            FROM games g
            LEFT JOIN users u ON u.id = g.owner_user_id
            WHERE COALESCE(g.delete_requested, 0) = 1
            ORDER BY g.id DESC
            """
        ).fetchall()
    return {"requests": [dict(r) for r in rows]}


@router.post("/admin/api/game-delete-approve")
async def api_approve(request: Request):
    _require_admin(request)
    payload = await request.json()
    game_id = int(payload.get("game_id", 0))
    if game_id <= 0:
        raise HTTPException(status_code=400, detail="Invalid game_id")

    with db() as conn:
        row = conn.execute(
            "SELECT id FROM games WHERE id=? AND COALESCE(delete_requested,0)=1",
            (game_id,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Request not found")

        # Hard delete the game row (analytics snapshots remain in their own table)
        conn.execute("DELETE FROM games WHERE id=?", (game_id,))
        conn.commit()

    return {"ok": True}


@router.post("/admin/api/game-delete-reject")
async def api_reject(request: Request):
    _require_admin(request)
    payload = await request.json()
    game_id = int(payload.get("game_id", 0))
    if game_id <= 0:
        raise HTTPException(status_code=400, detail="Invalid game_id")

    with db() as conn:
        row = conn.execute(
            "SELECT id FROM games WHERE id=? AND COALESCE(delete_requested,0)=1",
            (game_id,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Request not found")

        conn.execute(
            "UPDATE games SET delete_requested=0, delete_requested_at=NULL WHERE id=?",
            (game_id,),
        )
        conn.commit()

    return {"ok": True}
