# 🎫 AI Support Ticket Copilot

An AI layer for B2B SaaS support teams. It classifies each incoming ticket, sets its priority using the team's own written policy, drafts a reply grounded only in the help centre, and flags urgent or angry tickets for a senior agent. A human always sends the reply.

**▶ Live demo:** _link added after deployment_ · **📄 [PRD](docs/prd.md)** · **🧭 [Decision log](docs/decision-log.md)** · **📊 [Scorecard](evals/scorecard.md)**

> Portfolio project by Nikhar Jajoo (AI Product Manager). "Nimbus CRM" is a fictional company. Model quality, latency and cost are **measured**; time and cost savings are **projections** from stated assumptions (see PRD §7).

---

## The problem

Support teams triage every ticket by hand: read it, tag it, set a priority, route it, look up the policy, write the reply. At ~2,000 tickets a day:

- **Urgent tickets get buried.** A failing payment or a "what's the exit fee?" churn signal waits behind newsletter requests.
- **Priority depends on who reads the ticket.** When I hand-labelled 50 tickets against my own written policy, my first pass was only **74% consistent**.
- **Agent time goes to routine work:** reading, tagging, searching the help centre, retyping standard answers.

## The solution

```
New ticket ─▶ AI: category · priority (team's rubric) · sentiment · confidence
           ─▶ auto-routed and sorted by urgency
           ─▶ draft reply using ONLY help-centre facts, citing the article
           ─▶ agent reviews, edits, sends
           ─▶ High priority / angry / low confidence ─▶ flagged for a senior agent (coded rule, not the model)
```

**Build vs. integrate:** customers already run a helpdesk (Zendesk, Freshdesk, Intercom). Replacing it would kill adoption, so the product is designed as an add-on: a webhook sends new tickets in, and the helpdesk API writes tags, priority and the draft back as an internal note. This repo contains the AI engine, the evaluation, and a demo UI standing in for the agent view. Live helpdesk integration is designed but not built.

## Results

50 hand-labelled tickets · targets fixed in the PRD **before** any model was run · final rubric v4

| Metric | Target | **Gemini 3.5 Flash-Lite** (default) | Ministral 14B (fallback) |
|---|---|---|---|
| ⭐ Urgent tickets caught (High recall) | ≥ 90% | **100%** ✅ | 100% ✅ |
| Priority accuracy | ≥ 75% | **100%** ✅ | 94% ✅ |
| Category accuracy | ≥ 90% | 98% ✅ | 100% ✅ |
| Median / p90 response time | ≤ 3s | 1.8s / 2.1s ✅ | 2.0s / 2.6s ✅ |
| No invented facts in replies | ≥ 95% | *grading in progress* | *grading in progress* |
| Cost per 1,000 tickets (paid list price) | — | $1.19 | $0.61 |

With 50 tickets, the margin of error is roughly ±7–10 points, so this separates good from bad models, not 94% from 100%.

### How the policy, not the model, drove accuracy

| Rubric version | What changed | Priority accuracy (Flash-Lite / Ministral) |
|---|---|---|
| v2 | Written policy + explicit rules after my 74%-consistent first labelling pass | 84% / 84% |
| v3 | 3 clarifications where **both** models made the same mistake | 94% / 94%, but 3 regressions, incl. a frustrated customer asking for a person |
| v4 | Reworded the 2 rules that caused the regressions | **100% / 94%** |

Every rubric change was followed by a full re-run of all 50 tickets, because fixing one case can break another.

## Key product decisions

Full reasoning, with evidence, in the [decision log](docs/decision-log.md).

1. **Targets before results.** Pass/fail thresholds were written into the PRD before the first eval run.
2. **Urgent-ticket recall is the headline metric.** Missing an urgent ticket costs far more than over-flagging one, so errors are not treated as equal.
3. **Priority is a policy, not a fact.** The same rubric text is used by human labellers and given verbatim to the models.
4. **Deterministic rules stay in code.** "Needs a human" is a coded rule (High / angry / low confidence), not a model decision.
5. **Model choice on quality, stability, latency, availability and cost.** Gemini 3.5 Flash was disqualified (20 requests/day on the free tier, 25–65s per ticket). Flash-Lite beat Ministral on consistency; the ~$35/month cost gap at 2,000 tickets/day is smaller than one agent-hour.
6. **Cross-vendor fallback.** If the default model is unavailable, the other vendor's model takes over automatically.
7. **No vector database (yet).** 8 help articles fit in the prompt; retrieval is only worth adding at hundreds of articles.

## How quality is measured

- **Golden set:** 50 tickets sampled from the public [Bitext customer-support dataset](https://huggingface.co/datasets/bitext/Bitext-customer-support-llm-chatbot-training-dataset) across 8 SaaS categories (reproducible: `data/build_golden_set.py`), with priority hand-labelled against the [rubric](docs/priority-rubric.md).
- **Classification metrics:** category accuracy, priority accuracy, High recall/precision, under- vs over-prioritisation.
- **Reply grounding:** a separate LLM grader checks every drafted reply against the help centre and lists each unsupported claim. It is **blind** (model names hidden, replies shuffled), **batched** to fit free-tier quotas, and falls back across vendors. The models being tested never grade themselves.

## Tech stack

| Layer | Prototype | Production (designed) |
|---|---|---|
| Models | Gemini 3.5 Flash-Lite, Ministral 14B (structured JSON output) | Same, on a paid tier with a data-processing agreement |
| Knowledge | 8 help-centre articles in the prompt | Vector search over the full help centre |
| App | Streamlit | Inside the existing helpdesk via webhook + API |
| Eval | pandas, LLM-as-grader, golden set | Same, run before every prompt/model change, plus daily production sampling |
| Backend / storage | none / CSV | FastAPI + queue / Postgres log of AI decisions and agent edits |

## Repo structure

```
app/copilot.py           triage + reply engine (prompt, schema, retries, fallback)
app/streamlit_app.py     demo UI: triage a ticket · scorecard · how it works
data/golden_set.csv      50 tickets with hand-labelled priority (+ first-pass labels)
data/kb/                 8 help-centre articles (fictional Nimbus CRM)
evals/run_eval.py        runs every ticket through each model (resumable)
evals/judge.py           blind, batched grader for reply grounding
evals/scorecard.py       metrics vs PRD targets → scorecard.md / .json
evals/archive/           results from earlier rubric versions (v2, v3)
docs/                    PRD, priority rubric, decision log
```

## Run it locally

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env        # add GEMINI_API_KEY and MISTRAL_API_KEY (free tiers work)
.venv/bin/streamlit run app/streamlit_app.py
```

Re-run the evaluation: `evals/run_eval.py` → `evals/judge.py` → `evals/scorecard.py`.

## Limitations

- Test tickets are short and single-issue; real B2B tickets are longer and messier, so these results are an upper bound.
- 50 tickets can't distinguish models a few points apart; a repeat-run test would measure run-to-run variance directly.
- Free-tier APIs were used for the prototype. Google may use free-tier data to improve its products, so only public data is used here; production needs a paid tier.
- Impact figures (≈125 agent-hours/day at 2,000 tickets/day) are assumptions to validate with real support teams.
