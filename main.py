"""TurboTrack - 100-level racing game (Kivy).

Developer: Ankus Singh <ankush15hjp@gmail.com>
"""
import math

from kivy.app import App
from kivy.clock import Clock, mainthread
from kivy.core.window import Window
from kivy.graphics import Color, Ellipse, Line, PopMatrix, PushMatrix, Rectangle, Rotate
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.screenmanager import Screen, ScreenManager
from kivy.uix.widget import Widget

import config
import net
from engine import COUNTDOWN, Race
from levels import TIERS, TOTAL_LEVELS, level_config, stars_for, tier_for
from storage import Storage

Window.clearcolor = (0.07, 0.09, 0.12, 1)

TIER_COLORS = {
    "Easy": (0.2, 0.7, 0.35, 1),
    "Medium": (0.2, 0.55, 0.9, 1),
    "Hard": (0.95, 0.65, 0.15, 1),
    "Expert": (0.9, 0.3, 0.3, 1),
    "Insane": (0.65, 0.25, 0.85, 1),
}


def big_button(text, on_press, **kw):
    b = Button(text=text, size_hint_y=None, height=56, font_size=20,
               background_normal="", background_color=(0.15, 0.45, 0.85, 1), **kw)
    b.bind(on_release=lambda *_: on_press())
    return b


# --------------------------------------------------------------------- menu
class MenuScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        root = BoxLayout(orientation="vertical", padding=32, spacing=14)
        root.add_widget(Label(text=config.APP_NAME, font_size=48, bold=True,
                              size_hint_y=0.3))
        self.sub = Label(text="", font_size=16, size_hint_y=0.1)
        root.add_widget(self.sub)
        root.add_widget(big_button("PLAY", lambda: self.manager.go("levels")))
        root.add_widget(big_button("HOW TO PLAY", self.show_help))
        root.add_widget(big_button("ABOUT", self.show_about))
        root.add_widget(Label(
            text="Developer: %s\n%s" % (config.DEV_NAME, config.DEV_EMAIL),
            font_size=13, size_hint_y=0.2, halign="center"))
        self.add_widget(root)

    def on_pre_enter(self, *a):
        app = App.get_running_app()
        self.sub.text = "Level %d unlocked   |   %d stars" % (
            app.store.unlocked_level(), app.store.total_stars())

    def show_help(self):
        text = ("Touch LEFT half of the screen to steer left,\n"
                "RIGHT half to steer right.\n"
                "Touch the BRAKE strip at the bottom to slow down.\n\n"
                "Stay on the track, dodge cones, finish all laps\n"
                "before time runs out and in the top 3 to pass.\n"
                "3 stars = 1st place with a fast time.")
        Popup(title="How to play", content=Label(text=text, halign="center"),
              size_hint=(0.9, 0.5)).open()

    def show_about(self):
        text = ("%s v%s\n\n100 levels, 5 difficulty tiers:\n%s\n\n"
                "Developer: %s\n%s" % (
                    config.APP_NAME, config.VERSION,
                    ", ".join("%s (%d-%d)" % t for t in TIERS),
                    config.DEV_NAME, config.DEV_EMAIL))
        Popup(title="About", content=Label(text=text, halign="center"),
              size_hint=(0.9, 0.55)).open()


# ------------------------------------------------------------ level select
class LevelScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.root_box = BoxLayout(orientation="vertical", padding=10, spacing=8)
        self.add_widget(self.root_box)

    def on_pre_enter(self, *a):
        app = App.get_running_app()
        self.root_box.clear_widgets()
        top = BoxLayout(size_hint_y=None, height=48, spacing=8)
        back = Button(text="< Back", size_hint_x=0.3)
        back.bind(on_release=lambda *_: self.manager.go("menu"))
        top.add_widget(back)
        top.add_widget(Label(text="Select level", font_size=22))
        self.root_box.add_widget(top)

        unlocked = app.store.unlocked_level()
        scroll = ScrollView()
        col = BoxLayout(orientation="vertical", size_hint_y=None, spacing=6)
        col.bind(minimum_height=col.setter("height"))
        for name, lo, hi in TIERS:
            col.add_widget(Label(text="%s  (levels %d-%d)" % (name, lo, hi),
                                 size_hint_y=None, height=34, font_size=18,
                                 color=TIER_COLORS[name]))
            grid = GridLayout(cols=5, spacing=6, size_hint_y=None)
            grid.bind(minimum_height=grid.setter("height"))
            for lv in range(lo, hi + 1):
                stars, _ = app.store.get(lv)
                locked = lv > unlocked
                txt = str(lv) if locked else "%d\n%s" % (lv, "*" * stars + "-" * (3 - stars))
                b = Button(text=txt, size_hint_y=None, height=62, font_size=15,
                           disabled=locked, background_normal="",
                           background_color=TIER_COLORS[name] if not locked
                           else (0.25, 0.25, 0.28, 1))
                b.bind(on_release=lambda _b, n=lv: self.play(n))
                grid.add_widget(b)
            col.add_widget(grid)
        scroll.add_widget(col)
        self.root_box.add_widget(scroll)

    def play(self, level):
        self.manager.get_screen("game").level = level
        self.manager.go("game")


# -------------------------------------------------------------- game view
class TrackView(Widget):
    """Renders a Race. All game rules live in engine.py."""

    def __init__(self, **kw):
        super().__init__(**kw)
        self.race = None
        self.touches = {}
        self.steer = 0.0
        self.brake = False

    def set_race(self, race):
        self.race = race
        self.canvas.before.clear()
        with self.canvas.before:
            # grass
            Color(0.1, 0.35, 0.15, 1)
            Rectangle(pos=(0, 0), size=(race.w, race.h))
            pts = [c for p in race.pts for c in p]
            # kerb, asphalt, centre line
            Color(0.85, 0.85, 0.85, 1)
            Line(points=pts, width=race.track_width / 2 + 3, close=True, joint="round")
            Color(0.22, 0.22, 0.25, 1)
            Line(points=pts, width=race.track_width / 2, close=True, joint="round")
            Color(0.9, 0.9, 0.9, 0.35)
            Line(points=pts, width=1, close=True, dash_length=8, dash_offset=8)
            # start/finish line
            (x0, y0), (x1, y1) = race.pts[0], race.pts[1]
            a = math.atan2(y1 - y0, x1 - x0)
            hw = race.track_width / 4
            Color(1, 1, 1, 1)
            Line(points=[x0 - math.sin(a) * hw, y0 + math.cos(a) * hw,
                         x0 + math.sin(a) * hw, y0 - math.cos(a) * hw], width=3)

    def draw(self):
        race = self.race
        if not race:
            return
        self.canvas.clear()
        with self.canvas:
            Color(1, 0.5, 0.1, 1)
            r = race.car_wid * 0.5
            for ox, oy, alive in race.obstacles:
                if alive:
                    Ellipse(pos=(ox - r, oy - r), size=(2 * r, 2 * r))
            for car in reversed(race.cars):
                PushMatrix()
                Rotate(angle=math.degrees(car.angle), origin=(car.x, car.y))
                Color(*car.color)
                Rectangle(pos=(car.x - race.car_len / 2, car.y - race.car_wid / 2),
                          size=(race.car_len, race.car_wid))
                Color(0, 0, 0, 0.6)
                Rectangle(pos=(car.x + race.car_len * 0.05, car.y - race.car_wid * 0.35),
                          size=(race.car_len * 0.25, race.car_wid * 0.7))
                if car.is_player:
                    Color(1, 1, 1, 1)
                    Line(rectangle=(car.x - race.car_len / 2, car.y - race.car_wid / 2,
                                    race.car_len, race.car_wid), width=1.5)
                PopMatrix()
            # brake strip
            Color(0.8, 0.1, 0.1, 0.35 if not self.brake else 0.7)
            Rectangle(pos=(0, 0), size=(race.w, race.h * 0.1))

    # touch input ------------------------------------------------------
    def _recalc(self):
        steer, brake = 0.0, False
        for t in self.touches.values():
            if t[1] < self.height * 0.1:
                brake = True
            elif t[0] < self.width / 2:
                steer += 1.0
            else:
                steer -= 1.0
        self.steer, self.brake = max(-1.0, min(1.0, steer)), brake

    def on_touch_down(self, touch):
        self.touches[touch.uid] = touch.pos
        self._recalc()
        return True

    def on_touch_move(self, touch):
        if touch.uid in self.touches:
            self.touches[touch.uid] = touch.pos
            self._recalc()
        return True

    def on_touch_up(self, touch):
        self.touches.pop(touch.uid, None)
        self._recalc()
        return True


class GameScreen(Screen):
    level = 1

    def __init__(self, **kw):
        super().__init__(**kw)
        self.event = None
        self.race = None
        self.popup = None
        fl = FloatLayout()
        self.view = TrackView(size_hint=(1, 1))
        fl.add_widget(self.view)
        self.hud = Label(text="", size_hint=(1, None), height=60, font_size=18,
                         pos_hint={"top": 1}, halign="center")
        fl.add_widget(self.hud)
        self.banner = Label(text="", font_size=80, bold=True,
                            pos_hint={"center_x": 0.5, "center_y": 0.55})
        fl.add_widget(self.banner)
        quit_btn = Button(text="II", size_hint=(None, None), size=(48, 48),
                          pos_hint={"right": 1, "top": 1})
        quit_btn.bind(on_release=lambda *_: self.pause())
        fl.add_widget(quit_btn)
        self.add_widget(fl)

    def on_enter(self, *a):
        Clock.schedule_once(lambda dt: self.start_level(self.level), 0.05)

    def start_level(self, level):
        self.level = level
        self.race = Race(level, self.width, self.height)
        self.view.touches.clear()
        self.view.set_race(self.race)
        self.finished_handled = False
        if self.event:
            self.event.cancel()
        self.event = Clock.schedule_interval(self.tick, 1 / 60.0)

    def on_leave(self, *a):
        if self.event:
            self.event.cancel()
            self.event = None

    def tick(self, dt):
        r = self.race
        r.step(dt, self.view.steer, self.view.brake)
        self.view.draw()
        cfg = r.cfg
        left = max(0, cfg["time_limit"] - max(0.0, r.time))
        p = r.player
        self.hud.text = "Level %d - %s   Lap %d/%d   Pos %d/%d   Time left %ds" % (
            r.level, cfg["tier"], min(p.lap + 1, r.laps), r.laps,
            r.position_of(p), len(r.cars), left)
        if r.time < 0:
            self.banner.text = str(int(math.ceil(-r.time)))
        elif r.time < 0.6:
            self.banner.text = "GO!"
        else:
            self.banner.text = ""
        if r.over and not self.finished_handled:
            self.finished_handled = True
            self.finish()

    def finish(self):
        r, app = self.race, App.get_running_app()
        pos = r.player_finished_pos or r.position_of(r.player)
        won = r.player.finished and pos <= min(3, len(r.cars))
        stars = 0
        t = r.player.finish_time
        if won:
            stars = stars_for(r.level, t, pos)
            app.store.record(r.level, stars, t)
            net.submit_score(app.server_url(), app.player_name(), r.level, t, stars)
        msg = ("LEVEL COMPLETE!\nPlace %d   Time %.1fs\nStars: %d/3" % (pos, t, stars)
               if won else
               ("OUT OF TIME" if not r.player.finished else
                "FINISHED %d - need top 3" % pos))
        box = BoxLayout(orientation="vertical", spacing=8, padding=10)
        box.add_widget(Label(text=msg, font_size=22, halign="center"))
        if won and r.level < TOTAL_LEVELS:
            box.add_widget(big_button("Next level", lambda: self.next_level()))
        box.add_widget(big_button("Retry", lambda: self.retry()))
        box.add_widget(big_button("Level select", lambda: self.leave("levels")))
        self.popup = Popup(title="Result", content=box, size_hint=(0.85, 0.6),
                           auto_dismiss=False)
        self.popup.open()

    def _close_popup(self):
        if self.popup:
            self.popup.dismiss()
            self.popup = None

    def retry(self):
        self._close_popup()
        self.start_level(self.level)

    def next_level(self):
        self._close_popup()
        self.start_level(self.level + 1)

    def leave(self, screen):
        self._close_popup()
        self.manager.go(screen)

    def pause(self):
        if self.event:
            self.event.cancel()
            self.event = None
        box = BoxLayout(orientation="vertical", spacing=8, padding=10)
        pop = Popup(title="Paused", content=box, size_hint=(0.8, 0.5), auto_dismiss=False)

        def resume():
            pop.dismiss()
            self.event = Clock.schedule_interval(self.tick, 1 / 60.0)

        def quit_():
            pop.dismiss()
            self.manager.go("levels")

        box.add_widget(big_button("Resume", resume))
        box.add_widget(big_button("Restart", lambda: (pop.dismiss(), self.start_level(self.level))))
        box.add_widget(big_button("Quit", quit_))
        pop.open()


# ---------------------------------------------------------------------- app
class Screens(ScreenManager):
    def go(self, name):
        self.current = name


class TurboTrackApp(App):
    title = config.APP_NAME

    def build(self):
        self.store = Storage(self.user_data_dir)
        sm = Screens()
        sm.add_widget(MenuScreen(name="menu"))
        sm.add_widget(LevelScreen(name="levels"))
        sm.add_widget(GameScreen(name="game"))
        Window.bind(on_keyboard=self.on_back)
        return sm

    def on_back(self, window, key, *args):
        if key == 27:  # Android back button / Esc
            sm = self.root
            if sm.current == "game":
                sm.get_screen("game").pause()
                return True
            if sm.current == "levels":
                sm.go("menu")
                return True
        return False

    def server_url(self):
        return self.store.get_setting("server_url", config.SERVER_URL)

    def player_name(self):
        return self.store.get_setting("player_name", "Player")


if __name__ == "__main__":
    TurboTrackApp().run()
