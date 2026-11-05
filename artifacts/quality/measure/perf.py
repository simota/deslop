"""Fixed performance measurements for the SQI report (artifacts/quality/README.md).

    python3 artifacts/quality/measure/perf.py   # from the repository root

Median of 7 runs: a full corpus scan with detect.scan, and a cold `import detect`.
"""
import glob
import json
import statistics
import subprocess
import sys
import time

sys.path.insert(0, "skills/deslop/scripts")
import detect  # noqa: E402
from common import clear_caches, load_rules  # noqa: E402

rules = load_rules()
files = sorted(glob.glob("corpus/**/*.md", recursive=True))
scan = []
for _ in range(7):
    clear_caches()
    t = time.perf_counter()
    detect.scan(files, ".", rules, [], {f: "general" for f in files}, paths=files)
    scan.append(time.perf_counter() - t)
cold = []
for _ in range(7):
    t = time.perf_counter()
    subprocess.run([sys.executable, "-c", "import sys; sys.path.insert(0, 'skills/deslop/scripts'); import detect"], check=True)
    cold.append(time.perf_counter() - t)
loaded = subprocess.run([sys.executable, "-c", "import sys; sys.path.insert(0, 'skills/deslop/scripts'); import detect; "
                         "print(sorted(m for m in sys.modules if m in {'common','comparison','contract_check','cues','detect',"
                         "'findings','markdown_spans','preserve_check','snapshot'}))"], capture_output=True, text=True).stdout.strip()
print(json.dumps({"corpus_files": len(files), "scan_median_s": round(statistics.median(scan), 3),
                  "scan_runs_s": [round(x, 3) for x in scan], "cold_import_detect_median_s": round(statistics.median(cold), 3),
                  "modules_loaded_by_import_detect": loaded}, indent=1))
