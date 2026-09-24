"""Step 2 of the eval: an LLM grader checks every drafted reply against the help centre.

- Blind: the grader never sees which model wrote a reply; replies from all models are shuffled together.
- Batched: 10 replies per call, to fit the grader's free-tier daily quota.
- Resumable: verdicts are appended to evals/judgements.csv; already-graded replies are skipped.

- Fallback: if a grader is unavailable (quota or outage), the next grader in the chain takes over.
  Ministral is never a grader, because it is one of the models being graded.

Usage: .venv/bin/python -u evals/judge.py [grader-model-id ...]
"""
import json
import os
import sys
import time
from pathlib import Path

import pandas as pd
from google import genai
from google.genai import types
from mistralai.client import Mistral

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "app"))
from copilot import KB_TEXT  # noqa: E402

GRADERS = sys.argv[1:] or ["gemini-3.6-flash", "mistral-medium-latest", "mistral-small-latest"]
BATCH = 10
RAW = ROOT / "evals" / "results_raw.csv"
OUT = ROOT / "evals" / "judgements.csv"

JUDGE_PROMPT = f"""You are a strict quality reviewer for customer-support replies at Nimbus CRM.
Each reply was drafted by an AI for the given customer ticket and must use ONLY facts from this help centre:

<help_centre>
{KB_TEXT}
</help_centre>

For EACH item, judge the reply:
- unsupported_claims: list every specific factual claim in the reply (numbers, prices, time frames, menu paths,
  URLs, email addresses, channels, policies, eligibility rules) that is NOT stated in the help centre or contradicts it.
  Quote the claim briefly. Generic courtesy ("happy to help", "sorry for the trouble") and promising that a
  specialist will follow up are NOT factual claims. Empty list if none.
- grounded: true if unsupported_claims is empty, else false.
- answers_question: 3 = fully addresses what the customer asked, using the right information;
  2 = partially addresses it, or is vague where the help centre had a specific answer;
  1 = does not address the question, or answers a different question.
- note: one short sentence explaining the answers_question score.
"""

SCHEMA = {
    "type": "object",
    "properties": {
        "verdicts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "unsupported_claims": {"type": "array", "items": {"type": "string"}},
                    "grounded": {"type": "boolean"},
                    "answers_question": {"type": "integer", "enum": [1, 2, 3]},
                    "note": {"type": "string"},
                },
                "required": ["id", "unsupported_claims", "grounded", "answers_question", "note"],
            },
        }
    },
    "required": ["verdicts"],
}


def grade(grader, prompt, clients):
    if grader.startswith("gemini"):
        resp = clients["gemini"].models.generate_content(
            model=grader, contents=prompt,
            config=types.GenerateContentConfig(system_instruction=JUDGE_PROMPT,
                                               response_mime_type="application/json",
                                               response_json_schema=SCHEMA))
        return json.loads(resp.text)["verdicts"]
    resp = clients["mistral"].chat.complete(
        model=grader,
        messages=[{"role": "system", "content": JUDGE_PROMPT}, {"role": "user", "content": prompt}],
        response_format={"type": "json_schema", "json_schema": {"name": "verdicts", "schema": SCHEMA, "strict": True}})
    return json.loads(resp.choices[0].message.content)["verdicts"]


def main():
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    clients = {"gemini": genai.Client(api_key=os.getenv("GEMINI_API_KEY")),
               "mistral": Mistral(api_key=os.getenv("MISTRAL_API_KEY"))}

    raw = pd.read_csv(RAW, keep_default_na=False)
    raw = raw[(raw.error == "") & (raw.reply != "")]
    gold = pd.read_csv(ROOT / "data" / "golden_set.csv", keep_default_na=False).set_index("ticket_id")
    raw["key"] = raw.ticket_id + "|" + raw.model

    graded = set()
    if OUT.exists():
        graded = set(pd.read_csv(OUT, keep_default_na=False).key)
    todo = raw[~raw.key.isin(graded)].sample(frac=1, random_state=11)  # shuffle: blind + mixed batches
    # Anonymous ids so the grader can't infer the model from the id
    todo = todo.assign(anon_id=[f"R{i:03d}" for i in range(len(todo))])
    print(f"{len(todo)} replies to grade in {-(-len(todo) // BATCH)} calls", flush=True)

    graders = list(GRADERS)
    for start in range(0, len(todo), BATCH):
        chunk = todo.iloc[start:start + BATCH]
        items = [{"id": r.anon_id, "ticket": gold.loc[r.ticket_id, "message"], "reply": r.reply}
                 for r in chunk.itertuples()]
        prompt = "Grade these items:\n" + json.dumps(items, indent=1)
        verdicts = None
        while graders and verdicts is None:
            grader = graders[0]
            for attempt in range(4):
                try:
                    t = time.time()
                    verdicts = {v["id"]: v for v in grade(grader, prompt, clients)}
                    break
                except Exception as e:
                    msg = str(e)
                    print(f"   {grader} retry {attempt + 1}: {msg[:90]}", flush=True)
                    if "PerDay" in msg:
                        break
                    time.sleep(15 * (attempt + 1))
            if verdicts is None:
                print(f"!! {grader} unavailable; switching to next grader", flush=True)
                graders.pop(0)
        if verdicts is None:
            sys.exit("!! All graders unavailable; stopping. Re-run later to resume.")

        rows = []
        for r in chunk.itertuples():
            v = verdicts.get(r.anon_id)
            if v is None:
                print(f"   grader skipped {r.anon_id}; will retry on next run", flush=True)
                continue
            rows.append({"key": r.key, "ticket_id": r.ticket_id, "model": r.model,
                         "grounded": v["grounded"], "answers_question": v["answers_question"],
                         "unsupported_claims": " | ".join(v["unsupported_claims"]), "note": v["note"],
                         "grader": grader})
        pd.DataFrame(rows).to_csv(OUT, mode="a", header=not OUT.exists(), index=False)
        print(f"batch {start // BATCH + 1}: {grader} graded {len(rows)}/{len(chunk)} in {time.time() - t:.0f}s", flush=True)
        time.sleep(5)
    print("done")


if __name__ == "__main__":
    main()
