"""Fixed architecture measurements for the SQI report (artifacts/quality/README.md).

    python3 artifacts/quality/measure/arch.py   # from the repository root
"""
import ast, json, re, subprocess, sys, time
from pathlib import Path
R = Path.cwd(); SC = R / "skills/deslop/scripts"
mods = {p.stem: p for p in SC.glob("*.py")}
CLIS = {m for m, p in mods.items() if "__main__" in p.read_text()}
edges, private, cli_helper = {}, [], []
for m, p in mods.items():
    t = ast.parse(p.read_text())
    edges[m] = set()
    for n in t.body:
        if isinstance(n, ast.ImportFrom) and n.module in mods:
            edges[m].add(n.module)
            for a in n.names:
                if a.name.startswith("_"): private.append(f"{m}<-{n.module}.{a.name}")
            if n.module in CLIS and m in CLIS: cli_helper.append(f"{m}<-{n.module}:{','.join(a.name for a in n.names)}")
        elif isinstance(n, ast.Import):
            for a in n.names:
                if a.name in mods: edges[m].add(a.name)
def closure(m, seen=None):
    seen = seen if seen is not None else set()
    for d in edges[m]:
        if d not in seen: seen.add(d); closure(d, seen)
    return seen
cycles = [m for m in mods if m in closure(m)]
consts = {}
for m, p in mods.items():
    for n in ast.parse(p.read_text()).body:
        if isinstance(n, ast.Assign):
            for tg in n.targets:
                if isinstance(tg, ast.Name) and tg.id.isupper(): consts.setdefault((tg.id, ast.unparse(n.value) if len(ast.unparse(n.value))<200 else 'long'), []).append(m)
dups = {k[0]: v for k, v in consts.items() if len(v) > 1}
# same name, same set of string values
kinds = {}
for m, p in mods.items():
    for n in ast.parse(p.read_text()).body:
        if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "KINDS" for t in n.targets): kinds[m] = sorted(ast.literal_eval(n.value))
tests = sum(len(re.findall(r"^\s*def test_", f.read_text(), re.M)) for f in (R/"tests").glob("test_*.py"))
site_tests = [f.name for f in (R/"tests").glob("test_*.py") if "site" in f.read_text() and ("data.js" in f.read_text() or "serve" in f.read_text().replace("preserve",""))]
out = {"modules": len(mods), "cli_modules": sorted(CLIS), "edges": {k: sorted(v) for k, v in edges.items()},
 "cycles": cycles, "private_cross_imports": private, "cli_imports_cli_helpers": cli_helper,
 "detect_closure": sorted(closure("detect")), "duplicate_constant_defs": {"KINDS": kinds} ,
 "test_methods": tests, "site_guard_test_files": site_tests}
print(json.dumps(out, indent=1))
