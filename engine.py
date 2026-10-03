"""Pure-Python race engine (no Kivy) so it can be tested headless."""
import math
import random

from levels import level_config

REF = 500.0          # reference screen size the level data is designed for
COUNTDOWN = 3.0


def dist_point_seg(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    l2 = dx * dx + dy * dy
    if l2 == 0:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / l2))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def wrap_angle(a):
    while a > math.pi:
        a -= math.tau
    while a < -math.pi:
        a += math.tau
    return a


class Car:
    def __init__(self, x, y, angle, color, max_speed, is_player=False):
        self.x, self.y, self.angle = x, y, angle
        self.color = color
        self.max_speed = max_speed
        self.speed = 0.0
        self.is_player = is_player
        self.checkpoint = 1       # index of next waypoint to reach
        self.passed = 0           # total waypoints reached
        self.lap = 0
        self.finished = False
        self.finish_time = None
        self.off_track = False
        self.hit_cooldown = 0.0
        self.progress = 0.0
        self.lateral = 0.0        # AI lane offset (px)


class Race:
    def __init__(self, level, width, height, seed=None):
        self.cfg = level_config(level)
        self.level = level
        self.w, self.h = float(width), float(height)
        self.scale = min(self.w, self.h) / REF
        cfg = self.cfg
        self.pts = [(x * self.w, y * self.h) for x, y in cfg["waypoints"]]
        self.n = len(self.pts)
        self.track_width = cfg["track_width"] * self.scale
        self.car_len = 22 * self.scale
        self.car_wid = 12 * self.scale
        self.laps = cfg["laps"]
        self.time = -COUNTDOWN     # negative while counting down
        self.over = False
        self.player_finished_pos = None
        self.rng = random.Random(seed if seed is not None else cfg["seed"])

        self.player_max = 120 * self.scale
        self.accel = 90 * self.scale
        self.brake_decel = 220 * self.scale

        self.cars = []
        self._spawn_cars()
        self.obstacles = self._make_obstacles()

    # ---- setup -------------------------------------------------------
    def _spawn_cars(self):
        (x0, y0), (x1, y1) = self.pts[0], self.pts[1]
        ang = math.atan2(y1 - y0, x1 - x0)
        bx, by = -math.cos(ang), -math.sin(ang)       # backwards
        px, py = -math.sin(ang), math.cos(ang)        # sideways
        colors = [(0.95, 0.2, 0.2), (0.2, 0.6, 1), (0.2, 0.85, 0.4),
                  (1, 0.8, 0.1), (0.8, 0.4, 1), (1, 0.5, 0.1), (0.3, 0.9, 0.9)]
        total = self.cfg["ai_count"] + 1
        for i in range(total):
            row, col = divmod(i, 2)
            side = (-1 if col == 0 else 1) * self.track_width * 0.22
            back = (row + 1) * self.car_len * 1.8
            x = x0 + bx * back + px * side
            y = y0 + by * back + py * side
            if i == 0:
                car = Car(x, y, ang, colors[0], self.player_max, True)
            else:
                f = self.rng.uniform(0.93, 1.03)
                car = Car(x, y, ang, colors[i % len(colors)],
                          self.player_max * self.cfg["ai_speed"] * f)
                car.lateral = self.rng.uniform(-0.25, 0.25) * self.track_width
            self.cars.append(car)

    def _make_obstacles(self):
        obs = []
        for _ in range(self.cfg["obstacle_count"]):
            i = self.rng.randrange(1, self.n)       # keep start straight clear
            (ax, ay), (bx, by) = self.pts[i], self.pts[(i + 1) % self.n]
            t = self.rng.uniform(0.2, 0.8)
            x, y = ax + (bx - ax) * t, ay + (by - ay) * t
            ang = math.atan2(by - ay, bx - ax)
            off = self.rng.uniform(-0.35, 0.35) * self.track_width
            obs.append([x - math.sin(ang) * off, y + math.cos(ang) * off, True])
        return obs

    # ---- queries -----------------------------------------------------
    def distance_to_track(self, x, y):
        best = 1e9
        for i in range(self.n):
            ax, ay = self.pts[i]
            bx, by = self.pts[(i + 1) % self.n]
            d = dist_point_seg(x, y, ax, ay, bx, by)
            if d < best:
                best = d
        return best

    @property
    def player(self):
        return self.cars[0]

    def position_of(self, car):
        ordered = sorted(self.cars, key=self._rank_key)
        return ordered.index(car) + 1

    def _rank_key(self, c):
        if c.finished:
            return (0, c.finish_time)
        return (1, -c.progress)

    # ---- simulation --------------------------------------------------
    def step(self, dt, steer=0.0, brake=False):
        if self.over:
            return
        dt = min(dt, 0.05)
        self.time += dt
        racing = self.time >= 0
        for car in self.cars:
            if car.finished:
                car.speed = max(0.0, car.speed - self.brake_decel * dt * 0.5)
                self._move(car, dt)
                continue
            if car.is_player:
                self._drive_player(car, dt, steer, brake, racing)
            else:
                self._drive_ai(car, dt, racing)
            self._move(car, dt)
            if racing:
                self._update_progress(car)
                self._hit_obstacles(car, dt)
        if self.player.finished or self.time > self.cfg["time_limit"]:
            self.over = True
            if self.player_finished_pos is None:
                self.player_finished_pos = self.position_of(self.player)

    def _drive_player(self, car, dt, steer, brake, racing):
        cap = car.max_speed * (0.45 if car.off_track else 1.0)
        if racing:
            if brake:
                car.speed = max(0.0, car.speed - self.brake_decel * dt)
            elif car.speed < cap:
                car.speed = min(cap, car.speed + self.accel * dt)
            else:
                car.speed = max(cap, car.speed - self.brake_decel * 0.5 * dt)
        grip = min(1.0, car.speed / (0.35 * self.player_max)) if car.speed > 0 else 0
        car.angle += steer * 2.7 * grip * dt

    def _drive_ai(self, car, dt, racing):
        tx, ty = self.pts[car.checkpoint]
        # lane offset perpendicular to the next segment
        nx, ny = self.pts[(car.checkpoint + 1) % self.n]
        sa = math.atan2(ny - ty, nx - tx)
        tx += -math.sin(sa) * car.lateral
        ty += math.cos(sa) * car.lateral
        want = math.atan2(ty - car.y, tx - car.x)
        diff = wrap_angle(want - car.angle)
        turn = max(-2.7 * dt, min(2.7 * dt, diff * 4 * dt))
        car.angle += turn
        corner = 1.0 - min(0.35, abs(diff) * 0.35)
        cap = car.max_speed * corner * (0.45 if car.off_track else 1.0)
        if racing:
            car.speed += (cap - car.speed) * min(1.0, 2.0 * dt)

    def _move(self, car, dt):
        car.x += math.cos(car.angle) * car.speed * dt
        car.y += math.sin(car.angle) * car.speed * dt
        car.x = max(0, min(self.w, car.x))
        car.y = max(0, min(self.h, car.y))
        car.off_track = self.distance_to_track(car.x, car.y) > self.track_width / 2
        car.hit_cooldown = max(0.0, car.hit_cooldown - dt)

    def _update_progress(self, car):
        tx, ty = self.pts[car.checkpoint]
        d = math.hypot(tx - car.x, ty - car.y)
        if d < self.track_width * 0.8:
            if car.checkpoint == 0:
                car.lap += 1
                if car.lap >= self.laps:
                    car.finished = True
                    car.finish_time = self.time
                    return
            car.passed += 1
            car.checkpoint = (car.checkpoint + 1) % self.n
            tx, ty = self.pts[car.checkpoint]
            d = math.hypot(tx - car.x, ty - car.y)
        px, py = self.pts[(car.checkpoint - 1) % self.n]
        seg = max(1.0, math.hypot(tx - px, ty - py))
        car.progress = car.passed + max(0.0, 1.0 - d / seg)

    def _hit_obstacles(self, car, dt):
        r = self.car_len * 0.7
        for o in self.obstacles:
            if o[2] and math.hypot(o[0] - car.x, o[1] - car.y) < r:
                if car.hit_cooldown <= 0:
                    car.speed *= 0.35
                    car.hit_cooldown = 0.6
                if car.is_player:
                    o[2] = False   # cone knocked over
