from fastapi import APIRouter, Request, HTTPException
from Dashboard.permissions import require, is_admin_email
from Dashboard.db import campaigns_db, init_campaigns_db, games_db

router = APIRouter()

@router.on_event("startup")
def _init():
    init_campaigns_db()

def _has_project_access(project_id: int, email: str) -> bool:
    with campaigns_db() as db:
        row = db.execute(
            "SELECT 1 FROM project_access WHERE project_id=? AND user_email=?",
            (project_id, email)
        ).fetchone()
        return row is not None

@router.get("/campaigns")
def campaigns_home(request: Request):
    # Brands + admins can view campaign projects
    require(request, "can_view_brand_campaigns")
    user = request.state.user

    with campaigns_db() as db:
        if is_admin_email(user.get("email","")):
            rows = db.execute("SELECT * FROM projects ORDER BY id DESC").fetchall()
        else:
            rows = db.execute(
                """
                SELECT p.* FROM projects p
                JOIN project_access a ON a.project_id = p.id
                WHERE a.user_email = ?
                ORDER BY p.id DESC
                """,
                (user["email"],)
            ).fetchall()

    return {"ok": True, "projects": [dict(r) for r in rows]}

@router.post("/campaigns/projects")
def admin_create_project(
    request: Request,
    brand_email: str,
    title: str,
    budget: float = 0.0,
    currency: str = "EUR",
    targets_json: str = "{}",
    algorithm_version: str = "v1",
):
    # Admin-only creates projects, sets access
    user = request.state.user
    if not is_admin_email(user.get("email","")):
        require(request, "can_admin")

    with campaigns_db() as db:
        cur = db.execute(
            """
            INSERT INTO projects(brand_email, title, budget, currency, targets_json, algorithm_version, created_by_email)
            VALUES(?,?,?,?,?,?,?)
            """,
            (brand_email, title, budget, currency, targets_json, algorithm_version, user["email"])
        )
        project_id = cur.lastrowid

        # Grant the brand account access by default
        db.execute(
            "INSERT OR IGNORE INTO project_access(project_id, user_email, access_role) VALUES(?,?,?)",
            (project_id, brand_email, "owner")
        )
        db.commit()

    return {"ok": True, "project_id": project_id}

@router.post("/campaigns/projects/{project_id}/access")
def admin_grant_access(request: Request, project_id: int, user_email: str, access_role: str = "viewer"):
    user = request.state.user
    if not is_admin_email(user.get("email","")):
        require(request, "can_admin")

    with campaigns_db() as db:
        db.execute(
            "INSERT OR REPLACE INTO project_access(project_id, user_email, access_role) VALUES(?,?,?)",
            (project_id, user_email, access_role)
        )
        db.commit()
    return {"ok": True}

@router.post("/campaigns/projects/{project_id}/games/{game_id}")
def admin_link_game(request: Request, project_id: int, game_id: int):
    user = request.state.user
    if not is_admin_email(user.get("email","")):
        require(request, "can_admin")

    # Ensure game exists (in games.db)
    with games_db() as gdb:
        g = gdb.execute("SELECT id FROM games WHERE id=?", (game_id,)).fetchone()
        if not g:
            raise HTTPException(404, "Game not found")

    with campaigns_db() as db:
        db.execute("INSERT OR IGNORE INTO project_games(project_id, game_id) VALUES(?,?)", (project_id, game_id))
        db.commit()

    return {"ok": True}
