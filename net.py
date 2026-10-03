"""Tiny optional network client (stdlib only, runs in a background thread)."""
import json
import threading
import urllib.request


def _post(url, payload, timeout=6):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def _get(url, timeout=6):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read().decode())


def submit_score(server_url, name, level, finish_time, stars, callback=None):
    """Fire-and-forget. callback(ok: bool) is called from the worker thread."""
    if not server_url:
        return

    def work():
        ok = False
        try:
            _post(server_url.rstrip("/") + "/api/scores", {
                "name": name, "level": level, "time": finish_time, "stars": stars})
            ok = True
        except Exception:
            pass
        if callback:
            callback(ok)

    threading.Thread(target=work, daemon=True).start()


def fetch_leaderboard(server_url, level, callback):
    """callback(rows: list | None) from the worker thread."""
    if not server_url:
        callback(None)
        return

    def work():
        try:
            data = _get(server_url.rstrip("/") + "/api/leaderboard/%d" % level)
            callback(data.get("scores", []))
        except Exception:
            callback(None)

    threading.Thread(target=work, daemon=True).start()
