
import time
import sqlite3
from datetime import datetime
import requests
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "games.db")
POLL_INTERVAL_SECONDS = 300  # 5 minutes


def get_tracked_universe_ids():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    try:
        cur.execute("SELECT DISTINCT universe_id FROM games")
    except sqlite3.OperationalError as e:
        print("DB not ready yet (games table missing):", e)
        conn.close()
        return []
    rows = cur.fetchall()
    conn.close()
    return [r["universe_id"] for r in rows]


def insert_snapshot(universe_id: int, playing: int, visits: int, favorites: int):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO stats_snapshots (universe_id, timestamp, playing, visits, favorites)
        VALUES (?, ?, ?, ?, ?)
        """,
        (universe_id, datetime.utcnow().isoformat(), playing, visits, favorites),
    )
    conn.commit()
    conn.close()



def poll_once():
    universe_ids = get_tracked_universe_ids()
    if not universe_ids:
        print("No tracked games yet. Sleeping...")
        return
    ids_param = ",".join(str(u) for u in universe_ids)
    url = "https://games.roblox.com/v1/games"
    try:
        resp = requests.get(url, params={"universeIds": ids_param}, timeout=10)
        resp.raise_for_status()
    except Exception as e:
        print("Error talking to Roblox API:", e)
        return
    data = resp.json().get("data", [])
    for game in data:
        universe_id = game["id"]
        playing = game.get("playing") or 0
        visits = game.get("visits") or 0
        favorites = game.get("favoritedCount") or 0

        insert_snapshot(universe_id, playing, visits, favorites)

        print(
            f"[SNAPSHOT] {universe_id} "
            f"playing={playing} visits={visits} favorites={favorites}"
    )



def main():
    print("Starting CCU collector loop...")
    while True:
        poll_once()
        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
