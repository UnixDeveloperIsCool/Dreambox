from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from jose import jwt, JWTError

import os
import re
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional

from dashboard import BASE_STYLE, ME_ENDPOINT

router = APIRouter()

# games.py lives in /Dashboard, but DB files live in project root
DASHBOARD_DIR = Path(__file__).resolve().parent          # .../Dreambox/Dashboard
BASE_DIR = DASHBOARD_DIR.parent                          # .../Dreambox

USER_DB_PATH = BASE_DIR / "dreambox.db"
GAMES_DB_PATH = BASE_DIR / "games.db"

SECRET_KEY = os.environ.get("SECRET_KEY", "CHANGE_ME_TO_A_LONG_RANDOM_SECRET")
ALGORITHM = "HS256"


def users_db():
    conn = sqlite3.connect(str(USER_DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def games_db():
    conn = sqlite3.connect(str(GAMES_DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def html_page(title: str, body: str) -> HTMLResponse:
    return HTMLResponse(
        f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{title}</title>
  {BASE_STYLE}
  <style>
    input {{
      padding: 11px 14px;
      border-radius: 999px;
      border: 1px solid rgba(255,255,255,0.12);
      background: #0f0f0f;
      color: #fff;
      outline: none;
    }}
    input:focus {{
      border-color: rgba(255,255,255,0.22);
    }}
  </style>
</head>
<body>
  <div class="shell">{body}</div>
</body>
</html>"""
    )


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    ).fetchone()
    return bool(row)


def _column_exists(conn: sqlite3.Connection, table: str, col: str) -> bool:
    # NOTE: PRAGMA table_info returns rows like: (cid, name, type, notnull, dflt_value, pk)
    cur = conn.execute(f"PRAGMA table_info({table})")
    return any(r[1] == col for r in cur.fetchall())


def ensure_games_schema():
    with games_db() as conn:
        # Create base table
        if not _table_exists(conn, "games"):
            conn.execute("""
                CREATE TABLE IF NOT EXISTS games (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    owner_user_id INTEGER NOT NULL,
                    universe_id INTEGER NOT NULL,
                    name TEXT,
                    created_at TEXT,
                    game_url TEXT,
                    is_favorite INTEGER NOT NULL DEFAULT 0,
                    delete_requested INTEGER NOT NULL DEFAULT 0,
                    delete_requested_at TEXT
                );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_games_owner ON games(owner_user_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_games_universe ON games(universe_id);")
            conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_games_owner_universe ON games(owner_user_id, universe_id);")

        # Older installs: add columns if missing (all aligned at same indentation)
        if not _column_exists(conn, "games", "game_url"):
            try:
                conn.execute("ALTER TABLE games ADD COLUMN game_url TEXT;")
            except Exception:
                pass

        if not _column_exists(conn, "games", "is_favorite"):
            try:
                conn.execute("ALTER TABLE games ADD COLUMN is_favorite INTEGER NOT NULL DEFAULT 0;")
            except Exception:
                pass

        if not _column_exists(conn, "games", "delete_requested"):
            try:
                conn.execute("ALTER TABLE games ADD COLUMN delete_requested INTEGER NOT NULL DEFAULT 0;")
            except Exception:
                pass

        if not _column_exists(conn, "games", "delete_requested_at"):
            try:
                conn.execute("ALTER TABLE games ADD COLUMN delete_requested_at TEXT;")
            except Exception:
                pass

        # Optional analytics table
        if not _table_exists(conn, "stats_snapshots"):
            conn.execute("""
                CREATE TABLE IF NOT EXISTS stats_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    universe_id INTEGER NOT NULL,
                    timestamp TEXT NOT NULL,
                    playing INTEGER NOT NULL DEFAULT 0,
                    visits INTEGER NOT NULL DEFAULT 0,
                    favorites INTEGER NOT NULL DEFAULT 0,
                    upvotes INTEGER NOT NULL DEFAULT 0,
                    downvotes INTEGER NOT NULL DEFAULT 0
                );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_snapshots_u_ts ON stats_snapshots(universe_id, timestamp);")

        conn.commit()


# IMPORTANT: schema ensure must run at import time, but it must not crash
ensure_games_schema()


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

    with users_db() as conn:
        row = conn.execute(
            "SELECT id, email, account_type FROM users WHERE id=?",
            (user_id,),
        ).fetchone()

    if not row:
        raise HTTPException(status_code=401, detail="User not found")
    return row


def _is_partner(acct: str) -> bool:
    return (acct or "").strip().lower() == "partneraccount"


def _is_admin(acct: str) -> bool:
    return "administrator" in (acct or "").lower()


def _extract_place_id_from_url(url: str) -> int:
    m = re.search(r"/games/(\d+)", url or "")
    if not m:
        raise HTTPException(status_code=400, detail="Invalid Roblox game URL (must include /games/<placeId>)")
    return int(m.group(1))


def _try_resolve_universe_id(place_id: int) -> int:
    try:
        import requests  # type: ignore
    except Exception:
        return place_id

    try:
        r = requests.get(
            f"https://apis.roblox.com/universes/v1/places/{place_id}/universe",
            timeout=10
        )
        if r.ok:
            j = r.json()
            uid = j.get("universeId")
            if isinstance(uid, int) and uid > 0:
                return uid
    except Exception:
        pass

    return place_id


def _try_resolve_game_name(universe_id: int) -> Optional[str]:
    try:
        import requests  # type: ignore
    except Exception:
        return None

    try:
        r = requests.get(
            "https://games.roblox.com/v1/games",
            params={"universeIds": str(universe_id)},
            timeout=10
        )
        if not r.ok:
            return None
        j = r.json() or {}
        data = j.get("data") or []
        if data and isinstance(data, list) and isinstance(data[0], dict):
            nm = data[0].get("name")
            if isinstance(nm, str) and nm.strip():
                return nm.strip()
    except Exception:
        return None

    return None


JS_BOOT = f"""
<script>
  (function(){{
    const params = new URLSearchParams(window.location.search);
    const t = params.get("token");
    if(t && t.length > 20){{
      localStorage.setItem("dreambox_token", t);
      params.delete("token");
      const newUrl = window.location.pathname + (params.toString() ? ("?" + params.toString()) : "");
      window.history.replaceState({{}}, "", newUrl);
    }}
  }})();

  const token = localStorage.getItem("dreambox_token");
  if(!token) window.location.href = "/portal";

  async function me(){{
    const r = await fetch("{ME_ENDPOINT}", {{
      headers: {{ "Authorization": "Bearer " + token }}
    }});
    if(!r.ok){{
      localStorage.removeItem("dreambox_token");
      window.location.href = "/portal";
      return null;
    }}
    return await r.json();
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


@router.get("/games", response_class=HTMLResponse)
def games_page():
    body = """
    <div class="topbar">
      <div>
        <div class="kicker">Client portal • Games</div>
        <h1>Games</h1>
        <p class="sub" id="subtext">Connect your Roblox game URLs for tracking.</p>
        <div class="badge"><span class="dot" id="dot"></span><span id="badgeText">Signed in</span></div>
      </div>
      <div class="actions">
        <a class="ghost" href="/portal-home">Dashboard</a>
        <button class="ghost" onclick="logout()">Log out</button>
      </div>
    </div>

    <div class="panel">
      <div class="card">
        <h3>Add a game</h3>
        <p class="sub">Paste a Roblox game URL (we auto-detect the name).</p>
        <div style="display:flex; gap:10px; flex-wrap:wrap;">
          <input id="url" placeholder="https://www.roblox.com/games/123456789/Game-Name" style="flex:1; min-width:260px;">
          <button class="btn" onclick="add()">Add</button>
        </div>
        <p class="tiny" id="hintLine" style="margin-top:10px;"></p>
        <p class="tiny" id="errLine" style="color:#a0a0a0;"></p>
      </div>

      <div class="card" style="margin-top:12px;">
        <h3>Your games</h3>
        <div id="list" style="margin-top:10px; max-height:420px; overflow:auto; padding-right:6px;"></div>
      </div>
    </div>
    """ + JS_BOOT + """
    <script>
      function setStatus(acctType){
        const dot = document.getElementById("dot");
        const badgeText = document.getElementById("badgeText");
        const lower = (acctType||"").toLowerCase();
        if(lower.includes("administrator")){
          dot.style.background = "#60a5fa";
          dot.style.boxShadow = "0 0 0 4px rgba(96,165,250,0.10)";
          badgeText.textContent = "Admin";
        } else if(lower === "partneraccount") {
          dot.style.background = "#4ade80";
          dot.style.boxShadow = "0 0 0 4px rgba(74,222,128,0.10)";
          badgeText.textContent = "Partner";
        } else {
          dot.style.background = "#fbbf24";
          dot.style.boxShadow = "0 0 0 4px rgba(251,191,36,0.10)";
          badgeText.textContent = "No access";
        }
      }

      function item(g, acctType){
        const url = g.game_url || ("https://www.roblox.com/games/" + (g.universe_id || ""));
        const nm = g.name || "—";
        const requested = g.delete_requested ? "Requested" : "—";
        const fav = g.is_favorite ? "★" : "☆";
        const canHardDelete = (acctType||"").toLowerCase().includes("administrator");

        const actions = canHardDelete
          ? `<button class="btn" onclick="hardDelete(${g.id})">Delete</button>`
          : `<button class="ghost" onclick="requestDelete(${g.id})">Request delete</button>`;

        return `
          <div class="card" style="margin-top:12px;">
            <div style="display:flex; align-items:center; justify-content:space-between; gap:10px;">
              <h3 style="margin:0;">${nm}</h3>
              <button class="ghost" style="padding:8px 12px;" onclick="toggleFav(${g.id})" title="Favorite">${fav}</button>
            </div>
            <p class="sub">Universe: <strong>${g.universe_id}</strong> • Delete: ${requested}</p>
            <p class="tiny">
              <a class="ghost" style="padding:6px 10px;" href="${url}" target="_blank" rel="noreferrer">Open Roblox</a>
            </p>
            <div style="display:flex; gap:10px; flex-wrap:wrap; margin-top:10px;">
              ${actions}
            </div>
          </div>
        `;
      }

      let acctType = "";

      async function load(){
        const err = document.getElementById("errLine");
        err.textContent = "";

        const u = await me();
        if(!u) return;

        acctType = u.account_type || "";
        setStatus(acctType);

        const lower = acctType.toLowerCase();
        const allowed = (lower === "partneraccount") || lower.includes("administrator");
        if(!allowed){
          document.getElementById("subtext").textContent = "You do not have access to Games.";
          document.getElementById("list").innerHTML = "<p class='sub'>Access denied.</p>";
          return;
        }

        const data = await api("/games/api/list");
        const list = document.getElementById("list");
        if(!data.games || !data.games.length){
          list.innerHTML = "<p class='sub'>No games yet. Add your first URL above.</p>";
          return;
        }
        list.innerHTML = data.games.map(g => item(g, acctType)).join("");
      }

      async function add(){
        const err = document.getElementById("errLine");
        const hint = document.getElementById("hintLine");
        err.textContent = "";
        hint.textContent = "";

        const url = (document.getElementById("url").value || "").trim();
        if(!url) return;

        try {
          const data = await api("/games/api/add", {
            method:"POST",
            body: JSON.stringify({ game_url: url })
          });
          hint.textContent = "Added: " + (data.name || "Game connected");
          document.getElementById("url").value = "";
          load();
        } catch(e) {
          err.textContent = String(e.message || e);
        }
      }

      async function toggleFav(id){
        const err = document.getElementById("errLine");
        err.textContent = "";
        try {
          await api("/games/api/favorite", {
            method:"POST",
            body: JSON.stringify({ game_id: id })
          });
          load();
        } catch(e) {
          err.textContent = String(e.message || e);
        }
      }

      async function requestDelete(id){
        const err = document.getElementById("errLine");
        err.textContent = "";
        try {
          await api("/games/api/request-delete", {
            method:"POST",
            body: JSON.stringify({ game_id: id })
          });
          load();
        } catch(e) {
          err.textContent = String(e.message || e);
        }
      }

      async function hardDelete(id){
        if(!confirm("Delete this game now? This cannot be undone.")) return;
        const err = document.getElementById("errLine");
        err.textContent = "";
        try {
          await api("/games/api/admin-delete", {
            method:"POST",
            body: JSON.stringify({ game_id: id })
          });
          load();
        } catch(e) {
          err.textContent = String(e.message || e);
        }
      }

      load();
    </script>
    """
    return html_page("Games", body)


@router.get("/games/api/list")
def api_list(request: Request):
    u = _get_current_user_row(request)
    acct = (u["account_type"] or "")

    if not (_is_partner(acct) or _is_admin(acct)):
        raise HTTPException(status_code=403, detail="Not allowed")

    with games_db() as conn:
        rows = conn.execute(
            "SELECT id, owner_user_id, universe_id, name, game_url, is_favorite, delete_requested, delete_requested_at "
            "FROM games WHERE owner_user_id=? ORDER BY is_favorite DESC, id DESC",
            (u["id"],),
        ).fetchall()

    return {"games": [dict(r) for r in rows]}


@router.post("/games/api/add")
async def api_add(request: Request):
    u = _get_current_user_row(request)
    acct = (u["account_type"] or "")

    if not (_is_partner(acct) or _is_admin(acct)):
        raise HTTPException(status_code=403, detail="Not allowed")

    payload = await request.json()
    game_url = str(payload.get("game_url", "")).strip()
    if not game_url:
        raise HTTPException(status_code=400, detail="Missing game_url")

    place_id = _extract_place_id_from_url(game_url)
    universe_id = _try_resolve_universe_id(place_id)
    name = _try_resolve_game_name(universe_id)

    with games_db() as conn:
        existing = conn.execute(
            "SELECT id FROM games WHERE owner_user_id=? AND universe_id=?",
            (u["id"], universe_id),
        ).fetchone()
        if existing:
            raise HTTPException(status_code=400, detail="Game already added")

        conn.execute(
            "INSERT INTO games (owner_user_id, universe_id, name, created_at, game_url, is_favorite, delete_requested, delete_requested_at) "
            "VALUES (?, ?, ?, ?, ?, 0, 0, NULL)",
            (u["id"], universe_id, name, datetime.utcnow().isoformat(), game_url),
        )
        conn.commit()

    return {"ok": True, "universe_id": universe_id, "name": name}


@router.post("/games/api/favorite")
async def api_favorite(request: Request):
    u = _get_current_user_row(request)
    acct = (u["account_type"] or "")

    if not (_is_partner(acct) or _is_admin(acct)):
        raise HTTPException(status_code=403, detail="Not allowed")

    payload = await request.json()
    game_id = int(payload.get("game_id", 0))
    if game_id <= 0:
        raise HTTPException(status_code=400, detail="Invalid game_id")

    with games_db() as conn:
        row = conn.execute(
            "SELECT id, is_favorite FROM games WHERE id=? AND owner_user_id=?",
            (game_id, u["id"]),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Game not found")

        new_val = 0 if int(row["is_favorite"] or 0) == 1 else 1
        conn.execute(
            "UPDATE games SET is_favorite=? WHERE id=?",
            (new_val, game_id),
        )
        conn.commit()

    return {"ok": True, "is_favorite": new_val}


@router.post("/games/api/request-delete")
async def api_request_delete(request: Request):
    u = _get_current_user_row(request)
    acct = (u["account_type"] or "")

    if not (_is_partner(acct) or _is_admin(acct)):
        raise HTTPException(status_code=403, detail="Not allowed")

    payload = await request.json()
    game_id = int(payload.get("game_id", 0))
    if game_id <= 0:
        raise HTTPException(status_code=400, detail="Invalid game_id")

    with games_db() as conn:
        row = conn.execute(
            "SELECT id FROM games WHERE id=? AND owner_user_id=?",
            (game_id, u["id"]),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Game not found")

        conn.execute(
            "UPDATE games SET delete_requested=1, delete_requested_at=? WHERE id=?",
            (datetime.utcnow().isoformat(), game_id),
        )
        conn.commit()

    return {"ok": True}


@router.post("/games/api/admin-delete")
async def api_admin_delete(request: Request):
    u = _get_current_user_row(request)
    acct = (u["account_type"] or "")
    if not _is_admin(acct):
        raise HTTPException(status_code=403, detail="Admin only")

    payload = await request.json()
    game_id = int(payload.get("game_id", 0))
    if game_id <= 0:
        raise HTTPException(status_code=400, detail="Invalid game_id")

    with games_db() as conn:
        row = conn.execute("SELECT id FROM games WHERE id=?", (game_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Game not found")

        conn.execute("DELETE FROM games WHERE id=?", (game_id,))
        conn.commit()

    return {"ok": True}
