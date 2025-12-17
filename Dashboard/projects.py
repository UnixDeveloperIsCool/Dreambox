from fastapi import APIRouter, Request, HTTPException
from Dashboard.permissions import require, is_admin_email
from Dashboard.db import games_db, init_games_db

router = APIRouter()

@router.on_event("startup")
def _init():
    init_games_db()

@router.get("/projects")
def projects_page(request: Request):
    require(request, "can_manage_games")
    # Keep your existing HTML UI here; this is API-focused skeleton.
    return {"ok": True, "message": "Projects/Games area (partners add games; admins can remove)."}

@router.post("/projects/games")
def add_game(request: Request, name: str, universe_id: str = ""):
    require(request, "can_manage_games")
    user = request.state.user
    with games_db() as db:
        db.execute(
            "INSERT INTO games(partner_email, name, universe_id) VALUES(?,?,?)",
            (user["email"], name, universe_id or None)
        )
        db.commit()
    return {"ok": True}

@router.delete("/projects/games/{game_id}")
def remove_game(request: Request, game_id: int):
    # Admins only can remove
    user = request.state.user
    if not is_admin_email(user.get("email","")):
        require(request, "can_admin")

    with games_db() as db:
        cur = db.execute("DELETE FROM games WHERE id = ?", (game_id,))
        db.commit()
        if cur.rowcount == 0:
            raise HTTPException(404, "Game not found")
    return {"ok": True}
