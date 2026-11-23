"""Run the manager's collision code unchanged, with legacy render calls suppressed."""
from contextlib import redirect_stdout
import io
import os
from pathlib import Path
import sys
from types import ModuleType

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fit_shoes import BANKS, DEST, HERE, MASTER, sha, write_json

SHARED = Path(os.environ.get(
    "HIGHTOP_CHECKER_DIR",
    "/private/tmp/claude-501/-Users-yapweijun--claude-spares-spare-Iu3lC0/"
    "26a84d71-25c7-41e6-b903-49317aeebb05/scratchpad/modular",
))


def results():
    records = []
    fixed, _ = BANKS[0]
    for label, base, extra in (
        ("shared", SHARED, None),
        ("sit_hold", fixed.parent / "act", BANKS[1][0]),
        ("carry", fixed.parent / "act2", BANKS[2][0]),
    ):
        for kind in ("dense", "tri"):
            print("CHECKING", label, kind, flush=True)
            out = HERE / "checkers" / label
            out.mkdir(parents=True, exist_ok=True)
            name = "motion_check_tri.py" if kind == "tri" else "motion_check_dense.py"
            path = base / (name if extra is None else "motion_check.py")
            wrapper = base / name if extra is not None and kind == "tri" else None
            source = path.read_text()
            assert source.count("bpy.ops.render.render(write_still=True)") == 1
            source = source.replace("bpy.ops.render.render(write_still=True)", "None")
            original_argv = sys.argv
            sys.argv = [str(path), "--", str(MASTER), str(fixed), str(DEST), str(out)]
            if extra:
                sys.argv.append(str(extra))
            log = io.StringIO()
            try:
                sys.modules.pop("chibi", None)
                with redirect_stdout(log):
                    if wrapper:
                        module = ModuleType("motion_check")
                        module.__file__ = str(path)
                        sys.modules[module.__name__] = module
                        exec(compile(source, str(path), "exec"), module.__dict__)
                        exec(compile(wrapper.read_text(), str(wrapper), "exec"),
                             {"__file__": str(wrapper), "__name__": "__main__"})
                    else:
                        exec(compile(source, str(path), "exec"),
                             {"__file__": str(path), "__name__": "__main__"})
            finally:
                sys.argv = original_argv
                sys.modules.pop("chibi", None)
                if wrapper:
                    sys.modules.pop("motion_check", None)
            lines = [line for line in log.getvalue().splitlines() if line.startswith("RESULT ")]
            (out / ("motion_check_" + kind + ".txt")).write_text("\n".join(lines) + "\n")
            if extra is None:
                (out / "motion_check.json").replace(out / ("motion_check_" + kind + ".json"))
            required = {"rest", *BANKS[0][1]}
            if extra:
                required.update(next(clips for bank, clips in BANKS if bank == extra))
            fields = [line.split() for line in lines]
            assert {f[1] for f in fields} == required, fields
            passed = all(int(f[-2 if extra else 3]) == 0 and float(f[-1]) >= .0005 for f in fields)
            hashes = {p.name: sha(p) for p in (path, wrapper) if p}
            records.append({"group": label, "check": kind, "source_sha256": hashes, "passed": passed})
            print("\n".join(lines), flush=True)
    write_json("checker_manifest.json", {"export_sha256": sha(DEST), "checks": records})
    assert all(record["passed"] for record in records)


if __name__ == "__main__":
    results()
