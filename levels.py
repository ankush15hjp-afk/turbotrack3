"""Level generator: 100 levels, 5 difficulty tiers. Deterministic (seeded)."""
import math
import random

TOTAL_LEVELS = 100

TIERS = [
    # name, first level, last level
    ("Easy", 1, 20),
    ("Medium", 21, 45),
    ("Hard", 46, 70),
    ("Expert", 71, 90),
    ("Insane", 91, 100),
]


def tier_for(level):
    for name, lo, hi in TIERS:
        if lo <= level <= hi:
            return name
    return TIERS[-1][0]


def level_config(level):
    """Return a dict describing one level. level is 1..100."""
    level = max(1, min(TOTAL_LEVELS, level))
    t = (level - 1) / (TOTAL_LEVELS - 1)  # 0..1 progress
    rng = random.Random(level * 7919)

    laps = 2 + level // 25                      # 2..6
    track_width = 150 - 70 * t                  # wide -> narrow
    ai_count = 1 + int(5 * t)                   # 1..6 rivals
    ai_speed = 0.70 + 0.30 * t                  # fraction of player max speed
    obstacle_count = 2 + int(22 * t)            # cones/oil on track
    waypoint_count = 8 + int(8 * t)
    wobble = 0.15 + 0.35 * t                    # how twisty the track is

    # Closed track as a wobbly ellipse -> list of (x, y) in 0..1 space
    phase = [rng.uniform(0, math.tau) for _ in range(3)]
    pts = []
    for i in range(waypoint_count):
        a = math.tau * i / waypoint_count
        r = 1 + wobble * (
            0.5 * math.sin(2 * a + phase[0])
            + 0.3 * math.sin(3 * a + phase[1])
            + 0.2 * math.sin(5 * a + phase[2])
        )
        r = max(0.55, r)
        pts.append((0.5 + 0.36 * r * math.cos(a), 0.5 + 0.36 * r * math.sin(a)))

    time_limit = int(40 + laps * (38 - 14 * t))  # seconds to win
    return {
        "level": level,
        "tier": tier_for(level),
        "laps": laps,
        "track_width": track_width,
        "ai_count": ai_count,
        "ai_speed": ai_speed,
        "obstacle_count": obstacle_count,
        "waypoints": pts,
        "time_limit": time_limit,
        "seed": level * 7919,
    }


def stars_for(level, finish_time, position):
    """1-3 stars. position is 1-based finishing place."""
    cfg = level_config(level)
    if position == 1 and finish_time <= cfg["time_limit"] * 0.7:
        return 3
    if position <= 2:
        return 2
    return 1
