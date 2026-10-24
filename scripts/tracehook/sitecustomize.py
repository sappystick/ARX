"""File-access tracer for scripts/pipeline.py. Loaded only when ARX_TRACE is set (the pipeline puts this folder on PYTHONPATH, so every python child process,
including the system python3 that drives KiCad, writes to the same trace file). It records, as one line per event, what a step really reads and writes:
  R <path>   opened for reading (source files, data, results of earlier steps)
  W <path>   opened for writing / created / renamed over / removed
  L <dir>    directory listed (os.listdir / scandir / glob)
  P <path>   a path handed to a child program (kicad-cli etc.): the pipeline decides read or write from the file's mtime after the step
Only paths under ARX_ROOT are kept. Standard library only (runs under python 3.12 and 3.13)."""
import os, sys, shlex

_t = os.environ.get("ARX_TRACE")
if _t:
    _root = os.path.realpath(os.environ.get("ARX_ROOT", os.getcwd()))
    _skip = (os.sep + ".git" + os.sep, os.sep + "__pycache__" + os.sep, os.sep + ".pipeline" + os.sep)
    _f = open(_t, "a", buffering=1)
    _seen = set()
    _WR = os.O_WRONLY | os.O_RDWR | os.O_APPEND | os.O_CREAT | os.O_TRUNC

    def _norm(p):
        if isinstance(p, int) or p is None:
            return None
        try:
            p = os.fsdecode(p)
        except Exception:
            return None
        p = os.path.abspath(p)
        if not (p == _root or p.startswith(_root + os.sep)) or any(s in p + os.sep for s in _skip):
            return None
        return p

    def _put(kind, p):
        p = _norm(p)
        if p is not None and (kind, p) not in _seen:
            _seen.add((kind, p))
            _f.write(kind + " " + p + "\n")

    def _hook(ev, a):
        try:
            if ev == "open":
                fl = a[2]
                _put("W" if isinstance(fl, int) and fl & _WR else "R", a[0])
            elif ev in ("os.rename", "os.replace"):
                _put("W", a[0]); _put("W", a[1])
            elif ev in ("os.remove", "os.unlink", "os.rmdir", "os.mkdir"):
                _put("W", a[0])
            elif ev == "shutil.copyfile":
                _put("R", a[0]); _put("W", a[1])
            elif ev in ("os.listdir", "os.scandir"):
                _put("L", a[0] if a[0] is not None else ".")
            elif ev == "subprocess.Popen":
                args = a[1]
                toks = []
                for x in (args if isinstance(args, (list, tuple)) else [args]):
                    x = os.fsdecode(x)
                    toks.extend(shlex.split(x) if (" " in x and os.sep in x) else [x])
                for x in toks[1:]:
                    for part in x.split("="):
                        if os.sep in part or part.endswith((".json", ".kicad_pcb", ".csv", ".stl")):
                            _put("P", part)
            elif ev == "os.system":
                for x in shlex.split(os.fsdecode(a[0])):
                    if os.sep in x:
                        _put("P", x)
        except Exception:
            pass

    sys.addaudithook(_hook)
