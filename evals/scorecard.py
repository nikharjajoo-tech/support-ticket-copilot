"""Step 3 of the eval: turn raw results + grader verdicts into the PRD scorecard.

Writes evals/scorecard.md and evals/scorecard.json (the JSON feeds the demo app).
Usage: .venv/bin/python evals/scorecard.py
"""
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
EVALS = ROOT / "evals"

# Targets fixed in docs/prd.md BEFORE the eval was run.
TARGETS = {
    "high_recall": (0.90, ">="),
    "category_accuracy": (0.90, ">="),
    "priority_accuracy": (0.75, ">="),
    "groundedness": (0.95, ">="),
    "median_latency_s": (3.0, "<="),
}

# USD per 1M tokens (paid tier list prices). See evals/prices.json for sources; None = unknown.
PRICES = json.loads((EVALS / "prices.json").read_text()) if (EVALS / "prices.json").exists() else {}


def pct(x):
    return f"{x * 100:.0f}%"


def main():
    gold = pd.read_csv(ROOT / "data" / "golden_set.csv", keep_default_na=False)
    raw = pd.read_csv(EVALS / "results_raw.csv", keep_default_na=False)
    judged = (pd.read_csv(EVALS / "judgements.csv", keep_default_na=False)
              if (EVALS / "judgements.csv").exists()
              else pd.DataFrame(columns=["ticket_id", "model", "grounded", "answers_question", "unsupported_claims"]))

    df = raw.merge(gold[["ticket_id", "message", "true_category", "priority"]].rename(columns={"priority": "true_priority"}),
                   on="ticket_id")
    df = df.merge(judged.drop(columns=["key"], errors="ignore"), on=["ticket_id", "model"], how="left")

    scores, details = {}, {}
    for model, d in df.groupby("model", sort=False):
        ok = d[d.error == ""]
        n_total = len(gold)
        true_h = ok[ok.true_priority == "H"]
        pred_h = ok[ok.priority == "H"]
        rank = {"L": 0, "M": 1, "H": 2}
        diff = ok.priority.map(rank) - ok.true_priority.map(rank)
        g = ok[ok.grounded.astype(str).isin(["True", "False"])]
        s = {
            "tickets_answered": f"{len(ok)}/{n_total}",
            "valid_output": ((ok.schema_errors == "").mean()),
            "category_accuracy": (ok.category == ok.true_category).mean(),
            "priority_accuracy": (ok.priority == ok.true_priority).mean(),
            "high_recall": (true_h.priority == "H").mean() if len(true_h) else float("nan"),
            "high_precision": (pred_h.true_priority == "H").mean() if len(pred_h) else float("nan"),
            "under_prioritised": (diff < 0).mean(),
            "over_prioritised": (diff > 0).mean(),
            "groundedness": (g.grounded.astype(str) == "True").mean() if len(g) else float("nan"),
            "fully_answers": (g.answers_question.astype(int) == 3).mean() if len(g) else float("nan"),
            "replies_graded": len(g),
            "routed_to_human": (ok.needs_human.astype(str) == "True").mean(),
            "median_latency_s": ok.latency_s.astype(float).median(),
            "p90_latency_s": ok.latency_s.astype(float).quantile(0.9),
            "avg_input_tokens": ok.input_tokens.astype(float).mean(),
            "avg_output_tokens": (ok.output_tokens.astype(float) + ok.thinking_tokens.astype(float)).mean(),
        }
        p = PRICES.get(model)
        if p and p.get("input") is not None:
            s["cost_per_1k_tickets_usd"] = 1000 * (s["avg_input_tokens"] * p["input"] + s["avg_output_tokens"] * p["output"]) / 1e6
        scores[model] = s

        misses = ok[(ok.category != ok.true_category) | (ok.priority != ok.true_priority)]
        details[model] = {
            "per_category_accuracy": (ok.category == ok.true_category).groupby(ok.true_category).mean().round(2).to_dict(),
            "priority_confusion": pd.crosstab(ok.true_priority, ok.priority).reindex(
                index=["H", "M", "L"], columns=["H", "M", "L"], fill_value=0).to_dict(),
            "misses": misses[["ticket_id", "message", "true_category", "category", "true_priority", "priority",
                              "priority_reason"]].to_dict("records"),
            "ungrounded": g[g.grounded.astype(str) == "False"][["ticket_id", "message", "reply",
                                                               "unsupported_claims"]].to_dict("records"),
        }

    # Markdown report
    models = list(scores)
    lines = ["# Evaluation Scorecard", "",
             f"Golden set: {len(gold)} tickets · targets fixed in `docs/prd.md` before the run · grader: blind, batched LLM review", "",
             "| Metric | Target | " + " | ".join(models) + " |",
             "|---|---|" + "---|" * len(models)]

    def row(label, key, fmt, target=None):
        cells = []
        for m in models:
            v = scores[m].get(key)
            if v is None or (isinstance(v, float) and pd.isna(v)):
                cells.append("n/a")
                continue
            cell = fmt(v)
            if target:
                t, op = target
                passed = v >= t if op == ">=" else v <= t
                cell += " ✅" if passed else " ❌"
            cells.append(cell)
        tgt = "" if not target else f"{'≥' if target[1] == '>=' else '≤'} {fmt(target[0])}"
        lines.append(f"| {label} | {tgt} | " + " | ".join(cells) + " |")

    row("⭐ High-priority recall", "high_recall", pct, TARGETS["high_recall"])
    row("Category accuracy", "category_accuracy", pct, TARGETS["category_accuracy"])
    row("Priority accuracy", "priority_accuracy", pct, TARGETS["priority_accuracy"])
    row("Groundedness (no invented facts)", "groundedness", pct, TARGETS["groundedness"])
    row("Median latency", "median_latency_s", lambda v: f"{v:.1f}s", TARGETS["median_latency_s"])
    row("Tickets answered", "tickets_answered", str)
    row("Valid structured output", "valid_output", pct)
    row("High-priority precision", "high_precision", pct)
    row("Under-prioritised (costly error)", "under_prioritised", pct)
    row("Over-prioritised (cheaper error)", "over_prioritised", pct)
    row("Reply fully answers question", "fully_answers", pct)
    row("Routed to a human", "routed_to_human", pct)
    row("p90 latency", "p90_latency_s", lambda v: f"{v:.1f}s")
    row("Avg tokens in / out", "avg_input_tokens",
        lambda v: f"{v:.0f}")
    row("Cost per 1,000 tickets (paid list price)", "cost_per_1k_tickets_usd", lambda v: f"${v:.2f}")

    for m in models:
        det = details[m]
        lines += ["", f"## {m}: misses ({len(det['misses'])})", "",
                  "| Ticket | Message | Category (true → model) | Priority (true → model) | Model's reason |",
                  "|---|---|---|---|---|"]
        for x in det["misses"]:
            cat = x["true_category"] if x["true_category"] == x["category"] else f"**{x['true_category']} → {x['category']}**"
            pri = x["true_priority"] if x["true_priority"] == x["priority"] else f"**{x['true_priority']} → {x['priority']}**"
            lines.append(f"| {x['ticket_id']} | {x['message']} | {cat} | {pri} | {x['priority_reason']} |")
        if det["ungrounded"]:
            lines += ["", f"**Ungrounded replies ({len(det['ungrounded'])})**", ""]
            for x in det["ungrounded"]:
                lines.append(f"- {x['ticket_id']} \"{x['message']}\": {x['unsupported_claims']}")

    (EVALS / "scorecard.md").write_text("\n".join(lines) + "\n")
    (EVALS / "scorecard.json").write_text(json.dumps({"scores": scores, "details": details, "targets": TARGETS},
                                                     indent=1, default=str))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
