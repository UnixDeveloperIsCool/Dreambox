# app.py
import os
import json
import sqlite3
import random
import string
import smtplib
from email.message import EmailMessage
from email.utils import formataddr
from datetime import datetime, timedelta
from typing import Optional, Set

from fastapi import FastAPI, HTTPException, Depends, Query, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from jose import jwt, JWTError
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr

from roles import AccountType, ROLE_PERMISSIONS

# ============================================================
# DOMAIN + EMAIL CONFIG (change later via environment variables)
# ============================================================

API_BASE_URL = os.environ.get("API_BASE_URL", "https://api.dreamboxed.com")
FRONTEND_BASE_URL = os.environ.get("FRONTEND_BASE_URL", "https://dreamboxinteractive.com")
EMAIL_FROM = os.environ.get("EMAIL_FROM", "no-reply@dreamboxinteractive.com")

# ============================================================
# APP CONFIG
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "dreambox.db")

# JWT
SECRET_KEY = os.environ.get("SECRET_KEY", "CHANGE_ME_TO_A_LONG_RANDOM_SECRET")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

# 2FA
TWOFA_CODE_EXPIRE_MINUTES = 10

# password reset
PASSWORD_RESET_EXPIRE_MINUTES = 60

# SMTP
SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.ionos.co.uk")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")

pwd_context = CryptContext(
    schemes=["pbkdf2_sha256"],
    deprecated="auto"
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

app = FastAPI(title="Dreambox Interactive Backend")

# ============================================================
# UI STYLE (DARK BG + WHITE GLOW HALO)
# ============================================================

AUTH_STYLE = """
<style>
  :root{
    --page:#1a1a1a;
    --card:#0b0d10;
    --card2:#0a0c0f;
    --text:#f4f6f8;
    --muted:rgba(244,246,248,.65);
    --field:rgba(255,255,255,.06);
    --fieldLine:rgba(255,255,255,.12);
    --radius:26px;
  }

  *{box-sizing:border-box}
  html, body{height:100%;}

  body{
    margin:0;
    font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial;
    background: var(--page);
    color: var(--text);

    /* ✅ IMPORTANT: prevents "vh + padding" overflow */
    height: 100vh;

    display:flex;
    justify-content:center;

    /* ✅ top aligned like your screenshot */
    align-items:flex-start;

    /* ✅ only top padding (no bottom padding that causes overflow) */
    padding:40px 20px 0;

    /* ✅ stop scrollbars from glow/shadows */
    overflow:hidden;
  }

  .glow-wrap{
    position:relative;
    width: min(980px, 100%);
    margin: 0 auto;

    /* ✅ contains the glow so it can’t create overflow */
    overflow:hidden;
    border-radius: var(--radius);
  }

  .glow-wrap::before{
    content:"";
    position:absolute;
    inset:-70px; /* ✅ slightly reduced to avoid overflow edges */
    background: radial-gradient(680px 280px at 50% 45%, rgba(255,255,255,.18), transparent 70%);
    filter: blur(42px);
    z-index:0;
    pointer-events:none;
  }

  .card{
    position:relative;
    z-index:1;
    width:100%;
    background: linear-gradient(180deg, var(--card), var(--card2));
    border-radius: var(--radius);
    border: 1px solid rgba(255,255,255,.08);
    padding: 26px;
    box-shadow:
      0 30px 80px rgba(0,0,0,.75),
      inset 0 1px 0 rgba(255,255,255,.04);
  }

  .grid{
    display:grid;
    grid-template-columns: 1.2fr 0.8fr;
    gap: 22px;

    /* ✅ top-align so it doesn’t “float” */
    align-items:start;
    align-content:start;
  }

  @media (max-width: 860px){
    .grid{ grid-template-columns: 1fr; }
    body{ overflow:auto; } /* ✅ allow scroll on small screens */
  }

  .step{
    font-size:11px;
    letter-spacing:.18em;
    text-transform:uppercase;
    color:rgba(244,246,248,.55);
    margin-bottom:8px;
  }

  h1,h2{
    margin:0 0 8px 0;
    font-size:34px;
    letter-spacing:-0.02em;
  }

  .sub{
    margin:0 0 18px 0;
    color:var(--muted);
    font-size:14px;
    line-height:1.4;
  }

  .pill{
    display:inline-flex;
    align-items:center;
    gap:8px;
    padding:8px 12px;
    border-radius: 999px;
    border:1px solid rgba(255,255,255,.10);
    background: rgba(255,255,255,.04);
    color: rgba(244,246,248,.75);
    font-size: 12px;
  }

  .dot{
    width:10px; height:10px; border-radius:999px;
    background: #22c55e;
    box-shadow: 0 0 0 3px rgba(34,197,94,.10);
  }

  .hint{
    margin-top:14px;
    padding:12px 14px;
    border-radius: 14px;
    border:1px solid rgba(255,255,255,.10);
    background: rgba(255,255,255,.03);
    color: rgba(244,246,248,.72);
    font-size: 13px;
  }

  .panel{
    border-radius: 18px;
    border:1px solid rgba(255,255,255,.10);
    background: rgba(0,0,0,.18);
    padding: 16px;

    /* ✅ prevents panel stretching */
    height: fit-content;
    align-self: start;
  }

  label{
    display:block;
    margin: 14px 0 6px 0;
    font-size: 12px;
    letter-spacing:.08em;
    text-transform:uppercase;
    color: rgba(244,246,248,.72);
  }

  input{
    width:100%;
    padding: 12px 14px;
    border-radius: 12px;
    border: 1px solid var(--fieldLine);
    background: var(--field);
    color: var(--text);
    outline:none;
  }

  input::placeholder{ color: rgba(244,246,248,.45) }

  input:focus{
    border-color: rgba(255,255,255,.22);
    box-shadow: 0 0 0 4px rgba(255,255,255,.06);
  }

  .btn{
    width:100%;
    margin-top: 16px;
    padding: 12px 16px;
    border-radius: 999px;
    border: 0;
    background:#ffffff;
    color:#0b0d10;
    font-weight: 800;
    cursor:pointer;
  }

  .btn-ghost{
    width:100%;
    margin-top: 10px;
    padding: 12px 16px;
    border-radius: 999px;
    border: 1px solid rgba(255,255,255,.14);
    background: rgba(255,255,255,.04);
    color: rgba(244,246,248,.90);
    font-weight: 700;
    cursor:pointer;
  }

  .linkrow{
    margin-top: 10px;
    display:flex;
    justify-content:flex-end;
  }

  a{
    color: rgba(244,246,248,.75);
    text-decoration: underline;
    text-underline-offset: 3px;
    font-size: 12px;
  }

  .code{
    letter-spacing: .28em;
    text-align:center;
    font-size:18px;
  }
</style>
"""


def render_auth_shell(title: str, left_html: str, right_html: str) -> str:
    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>{title}</title>
  {AUTH_STYLE}
</head>
<body>
  <div class="glow-wrap">
    <div class="card">
      <div class="grid">
        <div>{left_html}</div>
        <div class="panel">{right_html}</div>
      </div>
    </div>
  </div>
</body>
</html>
"""

# ============================================================
# CONFIG LOADING (admins.json can be in /config or root)
# ============================================================

def _load_json_if_exists(path: str) -> Optional[dict]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except Exception as e:
        print(f"[CONFIG] Failed reading {path}: {e}")
        return None

def load_admin_emails() -> Set[str]:
    """
    Supports both:
      - ./config/admins.json  (preferred)
      - ./admins.json         (fallback)
    Format supported:
      { "admins": ["a@b.com", ...] }  OR  ["a@b.com", ...]
    """
    config_dir = os.path.join(BASE_DIR, "config")
    candidates = [
        os.path.join(config_dir, "admins.json"),
        os.path.join(BASE_DIR, "admins.json"),
    ]

    data = None
    used = None
    for p in candidates:
        data = _load_json_if_exists(p)
        if data is not None:
            used = p
            break

    if data is None:
        print("[CONFIG] No admins.json found. Admin list empty.")
        return set()

    if isinstance(data, dict):
        admins_list = data.get("admins", [])
    elif isinstance(data, list):
        admins_list = data
    else:
        admins_list = []

    emails = {str(e).lower() for e in admins_list if str(e).strip()}
    print(f"[CONFIG] Loaded {len(emails)} admin emails from {used}")
    return emails

ADMIN_EMAILS = load_admin_emails()

# ============================================================
# DB INIT + LIGHT MIGRATIONS
# ============================================================

def _column_exists(cur: sqlite3.Cursor, table: str, col: str) -> bool:
    cur.execute(f"PRAGMA table_info({table})")
    cols = [r[1] for r in cur.fetchall()]
    return col in cols

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute(
        "CREATE TABLE IF NOT EXISTS users ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "email TEXT UNIQUE NOT NULL,"
        "password_hash TEXT NOT NULL,"
        "account_type TEXT NOT NULL DEFAULT 'AccountPending',"
        "is_email_verified INTEGER NOT NULL DEFAULT 0,"
        "twofa_code TEXT,"
        "twofa_expires_at TEXT"
        ");"
    )

    if not _column_exists(cur, "users", "password_reset_token"):
        cur.execute("ALTER TABLE users ADD COLUMN password_reset_token TEXT;")
    if not _column_exists(cur, "users", "password_reset_expires_at"):
        cur.execute("ALTER TABLE users ADD COLUMN password_reset_expires_at TEXT;")

    cur.execute(
        "CREATE TABLE IF NOT EXISTS games ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "owner_user_id INTEGER NOT NULL,"
        "universe_id INTEGER NOT NULL,"
        "name TEXT,"
        "created_at TEXT NOT NULL,"
        "FOREIGN KEY(owner_user_id) REFERENCES users(id)"
        ");"
    )

    cur.execute(
        "CREATE TABLE IF NOT EXISTS brands ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "name TEXT NOT NULL,"
        "owner_user_id INTEGER NOT NULL,"
        "created_at TEXT NOT NULL,"
        "FOREIGN KEY(owner_user_id) REFERENCES users(id)"
        ");"
    )

    cur.execute(
        "CREATE TABLE IF NOT EXISTS campaigns ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "brand_id INTEGER NOT NULL,"
        "name TEXT NOT NULL,"
        "status TEXT NOT NULL DEFAULT 'draft',"
        "created_at TEXT NOT NULL,"
        "FOREIGN KEY(brand_id) REFERENCES brands(id)"
        ");"
    )

    cur.execute(
        "CREATE TABLE IF NOT EXISTS stats_snapshots ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "universe_id INTEGER NOT NULL,"
        "timestamp TEXT NOT NULL,"
        "playing INTEGER,"
        "visits INTEGER"
        ");"
    )

    cur.execute(
        "CREATE TABLE IF NOT EXISTS survey_submissions ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "user_id INTEGER NOT NULL,"
        "name TEXT,"
        "company TEXT,"
        "role TEXT,"
        "goals TEXT,"
        "budget_range TEXT,"
        "timeline TEXT,"
        "extra_notes TEXT,"
        "preferred_time TEXT,"
        "created_at TEXT NOT NULL,"
        "FOREIGN KEY(user_id) REFERENCES users(id)"
        ");"
    )

    cur.execute(
        "CREATE TABLE IF NOT EXISTS zoom_meetings ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "user_id INTEGER NOT NULL,"
        "email TEXT NOT NULL,"
        "preferred_time TEXT NOT NULL,"
        "status TEXT NOT NULL DEFAULT 'requested',"
        "zoom_join_url TEXT,"
        "created_at TEXT NOT NULL,"
        "FOREIGN KEY(user_id) REFERENCES users(id)"
        ");"
    )

    conn.commit()
    conn.close()

init_db()

# ============================================================
# MODELS
# ============================================================

class SignUpRequest(BaseModel):
    email: EmailStr
    password: str

class TwoFAVerifyRequest(BaseModel):
    email: EmailStr
    code: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserInfo(BaseModel):
    id: int
    email: EmailStr
    account_type: AccountType
    is_email_verified: bool

class SurveySubmission(BaseModel):
    email: EmailStr
    name: str
    company: Optional[str] = None
    role: Optional[str] = None
    goals: Optional[str] = None
    budget_range: Optional[str] = None
    timeline: Optional[str] = None
    extra_notes: Optional[str] = None
    preferred_time: str

class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordResetJSON(BaseModel):
    token: str
    new_password: str

# ============================================================
# DB HELPERS
# ============================================================

def get_user_by_email(email: str) -> Optional[sqlite3.Row]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE email = ?", (email.lower(),))
    row = cur.fetchone()
    conn.close()
    return row

def get_user_by_id(user_id: int) -> Optional[sqlite3.Row]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return row

# ============================================================
# SECURITY UTILS
# ============================================================

def hash_password(password: str) -> str:
    if len(password.encode("utf-8")) > 4096:
        raise HTTPException(status_code=400, detail="Password too long.")
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    if hashed.startswith("$2a$") or hashed.startswith("$2b$") or hashed.startswith("$2y$"):
        try:
            import bcrypt
            return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
        except Exception:
            return False
    return pwd_context.verify(plain, hashed)

def create_access_token(user_id: int) -> str:
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def decode_access_token(token: str) -> int:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return int(payload.get("sub"))
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid or expired token")

def create_twofa_code() -> str:
    return "".join(random.choices(string.digits, k=6))

def set_twofa_code(user_id: int, code: str, expires_at: datetime):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "UPDATE users SET twofa_code = ?, twofa_expires_at = ? WHERE id = ?;",
        (code, expires_at.isoformat(), user_id),
    )
    conn.commit()
    conn.close()

def clear_twofa_code(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "UPDATE users SET twofa_code = NULL, twofa_expires_at = NULL WHERE id = ?;",
        (user_id,),
    )
    conn.commit()
    conn.close()

# ============================================================
# EMAIL HELPERS
# ============================================================

SENDER_NAME = "Dreambox Interactive"
SENDER_EMAIL = "no-reply@dreamboxinteractive.com"

def send_email(to_email: str, subject: str, body: str) -> bool:
    if not SMTP_USER or not SMTP_PASSWORD:
        print("\n--- EMAIL (SMTP NOT CONFIGURED) ---")
        print("From:", formataddr((SENDER_NAME, SENDER_EMAIL)))
        print("To:", to_email)
        print("Subject:", subject)
        print(body)
        print("--- END EMAIL ---\n")
        return False  # IMPORTANT

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = formataddr((SENDER_NAME, SENDER_EMAIL))
    msg["To"] = to_email
    msg.set_content(body)

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        print("[EMAIL ERROR]", repr(e))
        return False


def send_twofa_code_via_email(email: str, code: str):
    subject = "Your Dreambox 2FA Code"
    body = f"Your login code is: {code}\n\nIt expires in {TWOFA_CODE_EXPIRE_MINUTES} minutes."
    send_email(email, subject, body)

def send_password_reset_email(email: str, token: str) -> bool:
    reset_link = f"{API_BASE_URL}/reset-password?token={token}"
    subject = "Set / Reset your Dreambox password"
    body = (
        "Click the link below to set your password:\n\n"
        f"{reset_link}\n\n"
        f"This link expires in {PASSWORD_RESET_EXPIRE_MINUTES} minutes."
    )
    return send_email(email, subject, body)

# ============================================================
# PASSWORD RESET CORE
# ============================================================

def create_password_reset_for_user(user_id: int, email: str):
    token = "".join(random.choices(string.ascii_letters + string.digits, k=48))
    expires_at = (datetime.utcnow() + timedelta(minutes=PASSWORD_RESET_EXPIRE_MINUTES)).isoformat()

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "UPDATE users SET password_reset_token=?, password_reset_expires_at=? WHERE id=?;",
        (token, expires_at, user_id),
    )
    conn.commit()
    conn.close()

    ok = send_password_reset_email(email, token)
    if not ok:
        raise HTTPException(
            status_code=500,
            detail="Email is not configured or failed to send. Contact support."
        )

def consume_password_reset_token(token: str) -> sqlite3.Row:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE password_reset_token=?;", (token,))
    user = cur.fetchone()
    conn.close()

    if not user:
        raise HTTPException(status_code=400, detail="Invalid reset token")

    exp = user["password_reset_expires_at"]
    if not exp:
        raise HTTPException(status_code=400, detail="Invalid reset token")

    try:
        exp_dt = datetime.fromisoformat(exp)
    except ValueError:
        raise HTTPException(status_code=500, detail="Invalid reset expiry stored")

    if datetime.utcnow() > exp_dt:
        raise HTTPException(status_code=400, detail="Reset token expired")

    return user

def clear_password_reset(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "UPDATE users SET password_reset_token=NULL, password_reset_expires_at=NULL WHERE id=?;",
        (user_id,),
    )
    conn.commit()
    conn.close()

# ============================================================
# AUTH DEPENDENCY
# ============================================================

def get_current_user(token: str = Depends(oauth2_scheme)) -> UserInfo:
    user_id = decode_access_token(token)
    row = get_user_by_id(user_id)
    if not row:
        raise HTTPException(status_code=401, detail="User not found")
    return UserInfo(
        id=row["id"],
        email=row["email"],
        account_type=AccountType(row["account_type"]),
        is_email_verified=bool(row["is_email_verified"]),
    )

# ============================================================
# AUTH ENDPOINTS
# ============================================================

@app.post("/auth/signup", response_model=UserInfo)
def signup(req: SignUpRequest):
    existing = get_user_by_email(req.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    account_type = AccountType.ADMIN if req.email.lower() in ADMIN_EMAILS else AccountType.PARTNER

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO users (email, password_hash, account_type, is_email_verified) "
        "VALUES (?, ?, ?, 0);",
        (req.email.lower(), hash_password(req.password), account_type.value),
    )
    conn.commit()
    user_id = cur.lastrowid
    conn.close()

    return UserInfo(
        id=user_id,
        email=req.email,
        account_type=account_type,
        is_email_verified=False,
    )

@app.post("/auth/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    email = form_data.username
    password = form_data.password
    row = get_user_by_email(email)
    if not row or not verify_password(password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    code = create_twofa_code()
    expires_at = datetime.utcnow() + timedelta(minutes=TWOFA_CODE_EXPIRE_MINUTES)
    set_twofa_code(row["id"], code, expires_at)
    send_twofa_code_via_email(email, code)

    # NOTE: still JSON, but now you also have an HTML place to paste:
    # GET /twofa?email=you@company.com
    return {"detail": "2FA code sent to your email.", "twofa_url": f"{API_BASE_URL}/twofa?email={email}"}

@app.post("/auth/verify-2fa", response_model=TokenResponse)
def verify_twofa(req: TwoFAVerifyRequest):
    row = get_user_by_email(req.email)
    if not row:
        raise HTTPException(status_code=401, detail="Invalid email or code")

    stored_code = row["twofa_code"]
    expires_at_str = row["twofa_expires_at"]
    if not stored_code or not expires_at_str:
        raise HTTPException(status_code=401, detail="2FA not initialized, please login again")

    try:
        expires_at = datetime.fromisoformat(expires_at_str)
    except ValueError:
        raise HTTPException(status_code=500, detail="Invalid 2FA expiry")

    if datetime.utcnow() > expires_at:
        clear_twofa_code(row["id"])
        raise HTTPException(status_code=401, detail="2FA code expired, please login again")

    if req.code != stored_code:
        raise HTTPException(status_code=401, detail="Invalid 2FA code")

    clear_twofa_code(row["id"])
    token = create_access_token(row["id"])
    return TokenResponse(access_token=token)

#@app.get("/auth/me", response_model=UserInfo)
#def read_me(current_user: UserInfo = Depends(get_current_user)):
  #  return current_user

@app.get("/auth/me")
def read_me(current_user: UserInfo = Depends(get_current_user)):
    perms = ROLE_PERMISSIONS[current_user.account_type]
    return {
        "id": current_user.id,
        "email": current_user.email,
        "account_type": current_user.account_type.value,
        "is_email_verified": current_user.is_email_verified,
        "permissions": perms,
    }



# ============================================================
# 2FA HTML PAGE (PLACE TO PASTE THE CODE) - STYLED
# ============================================================

@app.get("/twofa", response_class=HTMLResponse)
def twofa_page(email: str = ""):
    left = f"""
      <div class="step">STEP 2 · SECURE LOGIN</div>
      <h1>Verify 2FA</h1>
      <p class="sub">Enter the 6-digit code we emailed to finish signing in.</p>
      <div class="pill"><span class="dot"></span> 2FA required for every login</div>
      <div class="hint">If your code expired, go back and sign in again to receive a new one.</div>
    """
    right = f"""
      <form method="POST" action="/twofa">
        <label>Email</label>
        <input name="email" type="email" required placeholder="you@company.com" value="{email}">
        <label>2FA Code</label>
        <input class="code" name="code" inputmode="numeric" pattern="\\d{{6}}" maxlength="6" minlength="6" required placeholder="••••••">
        <button class="btn" type="submit">Continue</button>
        <div class="linkrow">
          <a href="/forgot-password">Forgot your password?</a>
        </div>
      </form>
    """
    return HTMLResponse(render_auth_shell("Verify 2FA", left, right))

@app.post("/twofa")
def twofa_submit(email: str = Form(...), code: str = Form(...)):
    token = verify_twofa(TwoFAVerifyRequest(email=email, code=code)).access_token
    # Simple redirect back to frontend; you can grab token from URL there.
    return RedirectResponse(url=f"{FRONTEND_BASE_URL}/login?token={token}", status_code=302)

# ============================================================
# FORGOT PASSWORD (JSON)
# ============================================================

@app.post("/auth/request-password-reset")
def request_password_reset(req: PasswordResetRequest):
    row = get_user_by_email(req.email)
    if row:
        create_password_reset_for_user(row["id"], row["email"])
    return {"detail": "If that email exists, a reset link has been sent."}

@app.post("/auth/reset-password")
def reset_password_json(req: PasswordResetJSON):
    user = consume_password_reset_token(req.token)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "UPDATE users SET password_hash=? WHERE id=?;",
        (hash_password(req.new_password), user["id"]),
    )
    conn.commit()
    conn.close()

    clear_password_reset(user["id"])
    return {"detail": "Password updated successfully."}

# ============================================================
# RESET PASSWORD (HTML PAGE ON API DOMAIN) - STYLED
# ============================================================

@app.get("/reset-password", response_class=HTMLResponse)
def reset_password_page(token: str):
    left = """
      <div class="step">STEP 1 · SECURE LOGIN</div>
      <h1>Set password</h1>
      <p class="sub">Create a new password to access your Dreambox account.</p>
      <div class="pill"><span class="dot"></span> 2FA required for every login</div>
      <div class="hint">After setting your password, you’ll be redirected back to the main site.</div>
    """
    right = f"""
      <form method="POST" action="/reset-password">
        <input type="hidden" name="token" value="{token}">
        <label>New password</label>
        <input type="password" name="new_password" required minlength="8" placeholder="At least 8 characters">
        <button class="btn" type="submit">Continue</button>
      </form>
    """
    return HTMLResponse(render_auth_shell("Set Password", left, right))

@app.post("/reset-password")
def reset_password_form(token: str = Form(...), new_password: str = Form(...)):
    user = consume_password_reset_token(token)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "UPDATE users SET password_hash=? WHERE id=?;",
        (hash_password(new_password), user["id"]),
    )
    conn.commit()
    conn.close()

    clear_password_reset(user["id"])
    return RedirectResponse(url=f"{FRONTEND_BASE_URL}/login", status_code=302)

# ============================================================
# SURVEY FLOW (EMAIL ONLY + AccountPending + sends reset)
# ============================================================

def create_or_get_pending_user(email: str) -> int:
    row = get_user_by_email(email)
    if row:
        return row["id"]

    temp_password = "Temp-" + "".join(random.choices(string.digits, k=12))

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO users (email, password_hash, account_type, is_email_verified) "
        "VALUES (?, ?, ?, 0);",
        (email.lower(), hash_password(temp_password), AccountType.ACCOUNT_PENDING.value),
    )
    conn.commit()
    user_id = cur.lastrowid
    conn.close()
    return user_id

def store_survey_submission(user_id: int, req: SurveySubmission):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO survey_submissions (user_id, name, company, role, goals, "
        "budget_range, timeline, extra_notes, preferred_time, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);",
        (
            user_id,
            req.name,
            req.company,
            req.role,
            req.goals,
            req.budget_range,
            req.timeline,
            req.extra_notes,
            req.preferred_time,
            datetime.utcnow().isoformat(),
        ),
    )
    conn.commit()
    conn.close()

def create_zoom_booking(user_id: int, email: str, preferred_time: str) -> None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO zoom_meetings (user_id, email, preferred_time, status, zoom_join_url, created_at) "
        "VALUES (?, ?, ?, ?, NULL, ?);",
        (user_id, email.lower(), preferred_time or "", "requested", datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()

@app.post("/survey/submit")
def submit_survey(req: SurveySubmission):
    user_id = create_or_get_pending_user(req.email)
    store_survey_submission(user_id, req)
    create_zoom_booking(user_id, req.email, req.preferred_time)
    create_password_reset_for_user(user_id, req.email)
    return {"detail": "Survey submitted. Check your email to set your password."}

# ============================================================
# WIDGET (EMBED DASHBOARD) - LEFT AS-IS (OPTIONAL TO RESTYLE)
# ============================================================

@app.get("/widget", response_class=HTMLResponse)
def widget(token: str = Query(None, description="JWT access token")):
    if not token:
        raise HTTPException(status_code=401, detail="Missing token")

    user_id = decode_access_token(token)
    row = get_user_by_id(user_id)
    if not row:
        raise HTTPException(status_code=401, detail="User not found")

    account_type = AccountType(row["account_type"])
    perms = ROLE_PERMISSIONS[account_type]

    sections = []
    sections.append(
        f"<header style='padding:12px 16px;border-bottom:1px solid #2a2a2a;'>"
        f"<h2 style='margin:0;font-family:system-ui;'>Dreambox Dashboard - {account_type.value}</h2>"
        f"<small style='color:#888;'>{row['email']}</small>"
        f"</header>"
    )

    if perms.get("can_view_basic_dashboard"):
        sections.append(
            "<section style='padding:12px 16px;'>"
            "<h3>Overview</h3>"
            "<p>Welcome. Your account is live. If you're AccountPending, you’ll still see Zoom + messaging.</p>"
            "</section>"
        )

    sections.append(
        "<section style='padding:12px 16px;border-top:1px solid #222;'>"
        "<h3>Zoom & Support</h3>"
        "<p><strong>Zoom requests</strong> are logged. An admin will confirm your meeting by email.</p>"
        "<p><strong>Messaging</strong>: support inbox (UI placeholder).</p>"
        "</section>"
    )

    if perms.get("can_view_game_data"):
        sections.append(
            "<section style='padding:12px 16px;border-top:1px solid #222;'>"
            "<h3>Game Analytics</h3>"
            "<p>CCU / visits snapshots will show here.</p>"
            "</section>"
        )

    if perms.get("can_admin"):
        sections.append(
            "<section style='padding:12px 16px;border-top:1px solid #222;background:#151515;'>"
            "<h3>Admin</h3>"
            "<p>Admin tools placeholder.</p>"
            "</section>"
        )

    html = (
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<title>Dreambox Widget</title></head>"
        "<body style='margin:0;font-family:system-ui;background:#101010;color:#e5e5e5;'>"
        "<div style='border:1px solid #262626;border-radius:10px;background:#171717;overflow:hidden;'>"
        + "".join(sections) +
        "</div></body></html>"
    )
    return HTMLResponse(content=html)

# ============================================================
# HTML FORGOT PASSWORD PAGE - STYLED
# ============================================================

@app.get("/forgot-password", response_class=HTMLResponse)
def forgot_password_page():
    left = """
      <div class="step">STEP 1 · SECURE LOGIN</div>
      <h1>Forgot password</h1>
      <p class="sub">Enter your email and we’ll send a reset link.</p>
      <div class="pill"><span class="dot"></span> 2FA required for every login</div>
      <div class="hint">If the email exists, we’ll send a reset link.</div>
    """
    right = f"""
      <form method="POST" action="/forgot-password">
        <label>Email</label>
        <input type="email" name="email" required placeholder="you@company.com">
        <button class="btn" type="submit">Continue</button>
        <button class="btn-ghost" type="button" onclick="window.location.href='/twofa'">Back to 2FA</button>
      </form>
    """
    return HTMLResponse(render_auth_shell("Forgot Password", left, right))

@app.post("/forgot-password")
def forgot_password_submit(email: str = Form(...)):
    email_l = email.lower().strip()
    row = get_user_by_email(email_l)

    if not row and email_l in ADMIN_EMAILS:
        temp_password = "Temp-" + "".join(random.choices(string.digits, k=12))

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO users (email, password_hash, account_type, is_email_verified) "
            "VALUES (?, ?, ?, 0);",
            (email_l, hash_password(temp_password), AccountType.ADMIN.value),
        )
        conn.commit()
        user_id = cur.lastrowid
        conn.close()

        row = {"id": user_id, "email": email_l}

    if row:
        create_password_reset_for_user(row["id"], row["email"])

    # Styled confirmation page (same glow)
    left = """
      <div class="step">DONE</div>
      <h1>Check your email</h1>
      <p class="sub">If the email exists, a reset link has been sent.</p>
      <div class="hint">Open the email and click the reset link to set a new password.</div>
    """
    right = f"""
      <div class="sub" style="margin-bottom:14px;">When you’re ready:</div>
      <button class="btn" type="button" onclick="window.location.href='{FRONTEND_BASE_URL}/login'">Back to login</button>
    """
    return HTMLResponse(render_auth_shell("Reset Link Sent", left, right))

# ===========================
# ROUTER INCLUDES
# ===========================

from landing_pages import router as landing_router
from portal_pages import router as portal_router
from dashboard import router as legacy_dashboard_router  # option A: keep old dashboard.py routes

from Dashboard.games import router as games_router
from Dashboard.admin_game_deletions import router as admin_game_deletions_router

# New modular dashboard pages (folder: Dashboard/)
from Dashboard.dashboard_home import router as dash_home_router
from Dashboard.projects import router as projects_router
from Dashboard.games import router as games_router
from Dashboard.campaigns import router as campaigns_router
from Dashboard.billing import router as billing_router
from Dashboard.admin_panel import router as admin_router


# Include base site routers first
app.include_router(landing_router)
app.include_router(portal_router)

# Keep your existing dashboard routes (option A)
app.include_router(legacy_dashboard_router)

app.include_router(games_router)
app.include_router(admin_game_deletions_router)

# Include new modular dashboard routes
app.include_router(dash_home_router)
app.include_router(projects_router)
app.include_router(games_router)
app.include_router(campaigns_router)
app.include_router(billing_router)
app.include_router(admin_router)

