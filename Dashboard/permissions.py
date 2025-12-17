# Dashboard/permissions.py
import json
from pathlib import Path
from fastapi import Request, HTTPException
from roles import ROLE_PERMISSIONS, AccountType

ADMINS_PATH = Path("config") / "admins.json"

def _load_admin_emails() -> set[str]:
    try:
        data = json.loads(ADMINS_PATH.read_text(encoding="utf-8"))
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

def is_admin_email(email: str) -> bool:
    return (email or "").strip().lower() in ADMIN_EMAILS

def require(request: Request, flag: str):
    """
    Uses request.state.user (your existing middleware system).
    Expects user to have: email + account_type
    Admin emails always pass.
    """
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # supports dict or object
    email = (user.get("email") if isinstance(user, dict) else getattr(user, "email", "")) or ""
    acct  = (user.get("account_type") if isinstance(user, dict) else getattr(user, "account_type", None))

    if is_admin_email(email):
        return

    # normalize to AccountType enum
    if isinstance(acct, AccountType):
        account_type = acct
    else:
        account_type = AccountType(str(acct))

    perms = ROLE_PERMISSIONS.get(account_type, {})
    if not perms.get(flag, False):
        raise HTTPException(status_code=403, detail="Access denied")
