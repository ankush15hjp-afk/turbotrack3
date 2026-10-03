"""Local save data (SQLite). Works offline on Android and desktop."""
import os
import sqlite3

from levels import TOTAL_LEVELS


class Storage:
    def __init__(self, folder):
        os.makedirs(folder, exist_ok=True)
        self.path = os.path.join(folder, "turbotrack.db")
        self.db = sqlite3.connect(self.path)
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS progress ("
            "level INTEGER PRIMARY KEY, stars INTEGER NOT NULL, best_time REAL NOT NULL)")
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
        self.db.commit()

    def get_setting(self, key, default=""):
        row = self.db.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return row[0] if row else default

    def set_setting(self, key, value):
        self.db.execute("INSERT OR REPLACE INTO settings VALUES (?, ?)", (key, str(value)))
        self.db.commit()

    def record(self, level, stars, finish_time):
        old = self.db.execute(
            "SELECT stars, best_time FROM progress WHERE level=?", (level,)).fetchone()
        if old:
            stars = max(stars, old[0])
            finish_time = min(finish_time, old[1])
        self.db.execute("INSERT OR REPLACE INTO progress VALUES (?, ?, ?)",
                        (level, stars, finish_time))
        self.db.commit()

    def get(self, level):
        row = self.db.execute(
            "SELECT stars, best_time FROM progress WHERE level=?", (level,)).fetchone()
        return row if row else (0, None)

    def unlocked_level(self):
        row = self.db.execute("SELECT MAX(level) FROM progress").fetchone()
        done = row[0] or 0
        return min(TOTAL_LEVELS, done + 1)

    def total_stars(self):
        row = self.db.execute("SELECT COALESCE(SUM(stars), 0) FROM progress").fetchone()
        return row[0]

    def reset(self):
        self.db.execute("DELETE FROM progress")
        self.db.commit()
