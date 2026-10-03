"""Minimal test runner (use `pytest tests` if you have pytest)."""
import importlib.util, inspect, os, sys, tempfile, pathlib, traceback
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

class MP:
    def setenv(self, k, v): os.environ[k] = v

failed = 0
for fn in ("tests/test_game.py", "tests/test_server.py"):
    spec = importlib.util.spec_from_file_location(os.path.basename(fn)[:-3], fn)
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except Exception:
        print("IMPORT FAIL", fn); traceback.print_exc(); failed += 1; continue
    for name, f in inspect.getmembers(mod, inspect.isfunction):
        if not name.startswith("test_"):
            continue
        args = []
        params = inspect.signature(f).parameters
        if "tmp_path" in params: args.append(pathlib.Path(tempfile.mkdtemp()))
        if "monkeypatch" in params: args.append(MP())
        try:
            f(*args); print("PASS", name)
        except Exception:
            failed += 1; print("FAIL", name); traceback.print_exc()
sys.exit(1 if failed else 0)
