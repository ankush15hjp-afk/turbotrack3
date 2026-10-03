# TurboTrack

100-level racing game for Android, written in Python (Kivy).
Developer: **Ankus Singh** - ankush15hjp@gmail.com

## What's inside
| File | Purpose |
|---|---|
| `main.py` | Frontend: menu, level select (100 levels), game screen, touch controls |
| `engine.py` | Game rules: track, cars, AI rivals, laps, obstacles, ranking (no Kivy, testable) |
| `levels.py` | Generates all 100 levels in 5 tiers: Easy 1-20, Medium 21-45, Hard 46-70, Expert 71-90, Insane 91-100 |
| `storage.py` | Local save (SQLite): stars, best times, unlocked levels |
| `net.py` | Optional client that uploads scores to the backend |
| `server/app.py` | Backend: Flask + SQLite leaderboard API |
| `buildozer.spec` | Android build settings |
| `.github/workflows/build-apk.yml` | Builds the APK online for free on GitHub |

Difficulty rises with the level: narrower and twistier track, more laps, more rival cars
that drive faster, more cones, less time.

## Run on your PC first
```
pip install kivy
python main.py
```
Mouse click = touch. Left half steers left, right half steers right, red strip at the bottom brakes.

## Build the APK
Buildozer only works on Linux (or WSL on Windows).

**Option A - GitHub (easiest, no setup):** push this folder to a GitHub repo, open the
Actions tab, run "Build APK", download `turbotrack-apk` when it finishes.

**Option B - your own Linux/WSL:**
```
pip install buildozer cython==0.29.36
buildozer -v android debug
```
The APK appears in `bin/`. First build takes 20-40 minutes. Copy it to your phone and install
(allow "install unknown apps"). For Play Store use `buildozer android release` and sign it.

## Backend (optional leaderboard)
```
pip install flask
python server/app.py          # http://0.0.0.0:5000
```
Then set `SERVER_URL` in `config.py` (e.g. `http://YOUR_PC_IP:5000`) before building.
Leave it empty to play fully offline. For real users deploy the server on a host
(Render, Railway, a VPS) behind HTTPS and add authentication/rate limiting.

## Tests
```
python run_tests.py
```
Checks that all 100 levels are valid, get harder, and can be finished; and the API and save data.
