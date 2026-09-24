"""Step 1 of the eval: run every golden-set ticket through each model.

Resumable: results are appended to evals/results_raw.csv one row at a time,
and tickets already answered successfully are skipped on re-run.

Usage: .venv/bin/python -u evals/run_eval.py ["Model name" ...]
"""
import csv
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "app"))
from copilot import MODELS, run  # noqa: E402

GOLD = ROOT / "data" / "golden_set.csv"
OUT = ROOT / "evals" / "results_raw.csv"
FIELDS = ["ticket_id", "model", "category", "priority_reason", "priority", "sentiment", "confidence",
          "kb_article", "reply", "needs_human", "latency_s", "input_tokens", "output_tokens",
          "thinking_tokens", "schema_errors", "error"]
EVAL_MODELS = sys.argv[1:] or ["Gemini 3.5 Flash-Lite", "Ministral 14B"]
PAUSE = {"mistral": 1.5, "gemini": 0.5}  # seconds between calls, to stay under per-minute limits

gold = pd.read_csv(GOLD, keep_default_na=False)
done = set()
if OUT.exists():
    prev = pd.read_csv(OUT, keep_default_na=False)
    done = set(zip(prev.ticket_id, prev.model)) - set(zip(prev[prev.error != ""].ticket_id, prev[prev.error != ""].model))
    # drop failed rows so they get retried cleanly
    prev[prev.error == ""].to_csv(OUT, index=False)

new_file = not OUT.exists()
with OUT.open("a", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
    if new_file:
        writer.writeheader()
    for model in EVAL_MODELS:
        vendor = MODELS[model][0]
        consecutive_errors = 0
        for t in gold.itertuples():
            if (t.ticket_id, model) in done:
                continue
            r = run(t.message, model)
            r["ticket_id"] = t.ticket_id
            r.setdefault("error", "")
            writer.writerow(r)
            f.flush()
            status = r["error"][:80] if r["error"] else f"{r['category']}/{r['priority']} {r['latency_s']}s"
            print(f"{model:24s} {t.ticket_id}  {status}", flush=True)
            consecutive_errors = consecutive_errors + 1 if r["error"] else 0
            if consecutive_errors >= 3:
                print(f"!! {model}: 3 errors in a row (likely quota). Skipping the rest; re-run later to resume.")
                break
            time.sleep(PAUSE[vendor])
print("done")
