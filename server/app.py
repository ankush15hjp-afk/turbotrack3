"""Leaderboard backend (Flask + SQLite).

Run:  pip install flask && python server/app.py
API:
  GET  /api/health
  GET  /api/levels                 -> summary of all 100 levels
  POST /api/scores                 -> {"name","level","time","stars"}
  GET  /api/leaderboard/<level>    -> top 20 fastest times for that level
"""
import os
import sqlite3
import sys

from flask import Flask, jsonify, request

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from levels import TOTAL_LEVELS, level_config  # noqa: E402

DB_PATH = os.environ.get("TURBOTRACK_DB", os.path.join(os.path.dirname(__file__), "scores.db"))

app = Flask(__name__)


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS scores ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, level INTEGER NOT NULL, "
        "time REAL NOT NULL, stars INTEGER NOT NULL, created TEXT DEFAULT CURRENT_TIMESTAMP)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_level_time ON scores(level, time)")
    return conn


@app.get("/api/health")
def health():
    return jsonify(ok=True)


@app.get("/api/levels")
def levels():
    out = []
    for lv in range(1, TOTAL_LEVELS + 1):
        c = level_config(lv)
        out.append({k: c[k] for k in ("level", "tier", "laps", "ai_count", "time_limit")})
    return jsonify(levels=out)


@app.post("/api/scores")
def post_score():
    data = request.get_json(silent=True) or {}
    try:
        name = str(data.get("name", "Player")).strip()[:20] or "Player"
        level = int(data["level"])
        t = float(data["time"])
        stars = int(data["stars"])
    except (KeyError, TypeError, ValueError):
        return jsonify(error="bad request"), 400
    if not (1 <= level <= TOTAL_LEVELS) or not (0 < t < 3600) or stars not in (1, 2, 3):
        return jsonify(error="invalid values"), 400
    with db() as conn:
        conn.execute("INSERT INTO scores (name, level, time, stars) VALUES (?,?,?,?)",
                     (name, level, t, stars))
    return jsonify(ok=True), 201


@app.get("/api/leaderboard/<int:level>")
def leaderboard(level):
    if not (1 <= level <= TOTAL_LEVELS):
        return jsonify(error="unknown level"), 404
    with db() as conn:
        rows = conn.execute(
            "SELECT name, MIN(time), MAX(stars) FROM scores WHERE level=? "
            "GROUP BY name ORDER BY MIN(time) LIMIT 20", (level,)).fetchall()
    return jsonify(level=level, scores=[
        {"rank": i + 1, "name": r[0], "time": round(r[1], 2), "stars": r[2]}
        for i, r in enumerate(rows)])


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
