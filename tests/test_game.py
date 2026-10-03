import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from engine import Race
from levels import TIERS, TOTAL_LEVELS, level_config, tier_for
from engine import wrap_angle
import math


def autopilot(race):
    """Steer player toward next waypoint; returns steer in [-1, 1]."""
    p = race.player
    tx, ty = race.pts[p.checkpoint]
    diff = wrap_angle(math.atan2(ty - p.y, tx - p.x) - p.angle)
    return max(-1.0, min(1.0, diff * 3))


def test_100_levels_valid():
    assert TOTAL_LEVELS == 100
    seen_tiers = {tier_for(i) for i in range(1, 101)}
    assert seen_tiers == {t[0] for t in TIERS}
    prev = None
    for lv in range(1, 101):
        c = level_config(lv)
        assert c["level"] == lv
        assert c["track_width"] > 60
        assert c["time_limit"] > 30
        if prev:
            assert c["ai_count"] >= prev["ai_count"]
            assert c["obstacle_count"] >= prev["obstacle_count"]
            assert c["track_width"] <= prev["track_width"] + 1e-9
        prev = c


def test_every_level_is_completable():
    # a simple autopilot player must be able to finish within the time limit
    for lv in range(1, 101):
        race = Race(lv, 400, 700)
        while not race.over:
            race.step(1 / 60, autopilot(race), False)
        assert race.player.finished, "level %d not completable by autopilot" % lv
        assert race.player.finish_time < race.cfg["time_limit"]


def test_ai_cars_finish_and_rank():
    race = Race(30, 400, 700)
    while not race.over:
        race.step(1 / 60, autopilot(race), False)
    assert 1 <= race.player_finished_pos <= len(race.cars)


def test_storage_roundtrip(tmp_path):
    from storage import Storage
    s = Storage(str(tmp_path))
    assert s.unlocked_level() == 1
    s.record(1, 2, 30.0)
    s.record(1, 1, 25.0)
    assert s.get(1) == (2, 25.0)
    assert s.unlocked_level() == 2
    s.record(100, 3, 50.0)
    assert s.unlocked_level() == 100
    assert s.total_stars() == 5
