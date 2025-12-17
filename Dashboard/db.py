import sqlite3

GAMES_DB = "games.db"
CAMPAIGNS_DB = "campaigns.db"

def _conn(path: str) -> sqlite3.Connection:
    c = sqlite3.connect(path)
    c.row_factory = sqlite3.Row
    return c

def games_db() -> sqlite3.Connection:
    return _conn(GAMES_DB)

def campaigns_db() -> sqlite3.Connection:
    return _conn(CAMPAIGNS_DB)

def init_games_db():
    with games_db() as db:
        db.execute("""
        CREATE TABLE IF NOT EXISTS games (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          partner_email TEXT NOT NULL,
          name TEXT NOT NULL,
          universe_id TEXT,
          created_at TEXT DEFAULT (datetime('now'))
        );
        """)
        db.execute("""
        CREATE TABLE IF NOT EXISTS game_stats_daily (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          game_id INTEGER NOT NULL,
          day TEXT NOT NULL,
          dau INTEGER DEFAULT 0,
          mau INTEGER DEFAULT 0,
          ccu_peak INTEGER DEFAULT 0,
          avg_session_minutes REAL DEFAULT 0,
          impressions INTEGER DEFAULT 0,
          clicks INTEGER DEFAULT 0,
          spend_estimate REAL DEFAULT 0,
          FOREIGN KEY(game_id) REFERENCES games(id)
        );
        """)
        db.execute("CREATE INDEX IF NOT EXISTS idx_stats_game_day ON game_stats_daily(game_id, day);")
        db.commit()

def init_campaigns_db():
    with campaigns_db() as db:
        db.execute("""
        CREATE TABLE IF NOT EXISTS projects (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          brand_email TEXT NOT NULL,
          title TEXT NOT NULL,
          status TEXT DEFAULT 'draft',
          budget REAL DEFAULT 0,
          currency TEXT DEFAULT 'EUR',
          targets_json TEXT DEFAULT '{}',
          algorithm_version TEXT DEFAULT 'v1',
          created_by_email TEXT NOT NULL,
          created_at TEXT DEFAULT (datetime('now'))
        );
        """)
        db.execute("""
        CREATE TABLE IF NOT EXISTS project_access (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          project_id INTEGER NOT NULL,
          user_email TEXT NOT NULL,
          access_role TEXT DEFAULT 'viewer',
          created_at TEXT DEFAULT (datetime('now')),
          UNIQUE(project_id, user_email),
          FOREIGN KEY(project_id) REFERENCES projects(id)
        );
        """)
        db.execute("""
        CREATE TABLE IF NOT EXISTS project_games (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          project_id INTEGER NOT NULL,
          game_id INTEGER NOT NULL,
          UNIQUE(project_id, game_id)
        );
        """)
        db.execute("""
        CREATE TABLE IF NOT EXISTS quotes (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          project_id INTEGER NOT NULL,
          amount REAL NOT NULL,
          currency TEXT DEFAULT 'EUR',
          notes TEXT DEFAULT '',
          status TEXT DEFAULT 'sent',
          created_at TEXT DEFAULT (datetime('now'))
        );
        """)
        db.execute("""
        CREATE TABLE IF NOT EXISTS invoices (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          project_id INTEGER NOT NULL,
          quote_id INTEGER,
          billing_type TEXT NOT NULL, -- 'one_off' or 'subscription'
          amount REAL NOT NULL,
          currency TEXT DEFAULT 'EUR',
          status TEXT DEFAULT 'issued', -- issued/paid/void/uncollectible
          stripe_customer_id TEXT,
          stripe_invoice_id TEXT,
          stripe_subscription_id TEXT,
          issued_at TEXT DEFAULT (datetime('now')),
          paid_at TEXT
        );
        """)
        db.commit()
