"""Streamlit demo: AI Support Ticket Copilot.

Run locally:  .venv/bin/streamlit run app/streamlit_app.py
"""
import json
import os
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent

# On Streamlit Community Cloud, API keys come from the app's Secrets settings instead of .env
try:
    for key in ("GEMINI_API_KEY", "MISTRAL_API_KEY"):
        if key in st.secrets and not os.getenv(key):
            os.environ[key] = st.secrets[key]
except (FileNotFoundError, st.errors.StreamlitSecretNotFoundError):
    pass

from copilot import MODELS, run_with_fallback  # noqa: E402

st.set_page_config(page_title="Support Ticket Copilot", page_icon="🎫", layout="wide")

DEMO_MODELS = ["Gemini 3.5 Flash-Lite", "Ministral 14B"]
MAX_RUNS_PER_SESSION = 15  # protects the free-tier API quota on the public demo
PRICES = json.loads((ROOT / "evals" / "prices.json").read_text())
PRIORITY_LABEL = {"H": "🔴 High", "M": "🟠 Medium", "L": "🟢 Low"}


@st.cache_data
def load_gold():
    return pd.read_csv(ROOT / "data" / "golden_set.csv", keep_default_na=False)


@st.cache_data
def load_scorecard():
    path = ROOT / "evals" / "scorecard.json"
    return json.loads(path.read_text()) if path.exists() else None


def cost_usd(result):
    p = PRICES.get(result["model"])
    if not p:
        return None
    out = result.get("output_tokens", 0) + result.get("thinking_tokens", 0)
    return (result.get("input_tokens", 0) * p["input"] + out * p["output"]) / 1e6


st.title("🎫 AI Support Ticket Copilot")
st.caption("Triages B2B SaaS support tickets and drafts replies grounded in the help centre, "
           "with a human agent always in control. Portfolio project · fictional company \"Nimbus CRM\".")

missing = [k for k in ("GEMINI_API_KEY", "MISTRAL_API_KEY") if not os.getenv(k)]
if missing:
    st.error(f"API keys not configured: {', '.join(missing)}. Add them in the app's Secrets settings "
             "(or in a local .env file) to enable live triage. The scorecard still works.")

tab_try, tab_score, tab_how = st.tabs(["Triage a ticket", "Evaluation scorecard", "How it works"])

# ---------------------------------------------------------------- Tab 1: try it
with tab_try:
    gold = load_gold()
    left, right = st.columns([2, 3], gap="large")

    with left:
        st.subheader("Incoming ticket")
        options = ["✍️ Write my own"] + [f"{r.ticket_id} · {r.message}" for r in gold.itertuples()]
        choice = st.selectbox("Pick a sample from the test set, or write your own", options, index=37)
        sample = None if choice.startswith("✍️") else gold[gold.ticket_id == choice.split(" · ")[0]].iloc[0]
        ticket = st.text_area("Customer message", value="" if sample is None else sample.message, height=110,
                              placeholder="e.g. Our payment failed twice and the whole team is locked out!")
        st.caption("🔒 Demo runs on free-tier AI APIs, which may use inputs to improve their models. "
                   "Please don't enter real personal or company data.")
        model = st.selectbox("Model", DEMO_MODELS,
                             help="Gemini 3.5 Flash-Lite is the recommended default from the evaluation. "
                                  "If the chosen model is unavailable, the other vendor's model takes over.")
        runs = st.session_state.get("runs", 0)
        go = st.button("Triage ticket", type="primary", disabled=not ticket.strip() or runs >= MAX_RUNS_PER_SESSION)
        if runs >= MAX_RUNS_PER_SESSION:
            st.info("Demo limit reached for this session (free-tier API quota). Refresh later to try again.")
        if sample is not None:
            st.caption(f"Human labels for this ticket → category **{sample.true_category}**, "
                       f"priority **{PRIORITY_LABEL[sample.priority]}**")

    with right:
        st.subheader("Copilot output")
        if go:
            st.session_state["runs"] = runs + 1
            with st.spinner(f"Triaging with {model}…"):
                st.session_state["result"] = run_with_fallback(ticket.strip(), model)
                st.session_state["result_for"] = sample.ticket_id if sample is not None else None
        r = st.session_state.get("result")
        if not r:
            st.info("Pick a ticket and click **Triage ticket**.")
        elif "error" in r:
            st.error(f"Both models are unavailable right now (free-tier limits). Please try again shortly.\n\n`{r['error'][:160]}`")
        else:
            if r.get("fallback_from"):
                st.warning(f"{r['fallback_from']} was unavailable, so the backup model **{r['model']}** handled this ticket.")
            c1, c2 = st.columns(2)
            c1.metric("Category", r["category"].title())
            c2.metric("Priority", PRIORITY_LABEL.get(r["priority"], r["priority"]))
            c3, c4 = st.columns(2)
            c3.metric("Sentiment", r["sentiment"].title())
            c4.metric("Route", "👤 Human review" if r["needs_human"] else "✅ Agent queue")
            st.markdown(f"**Why this priority:** {r['priority_reason']}")
            if r["needs_human"]:
                reasons = [x for x, on in [("High priority", r["priority"] == "H"),
                                           ("angry customer", r["sentiment"] == "angry"),
                                           ("low model confidence", r["confidence"] == "low")] if on]
                st.caption("Flagged for a senior agent because: " + ", ".join(reasons))
            st.markdown(f"**Draft reply** · source: `{r['kb_article']}` · confidence: {r['confidence']}")
            st.text_area("Agent edits before sending", value=r["reply"], height=170, label_visibility="collapsed")
            cost = cost_usd(r)
            st.caption(f"{r['model']} · {r['latency_s']:.1f}s · {r['input_tokens']} tokens in / {r['output_tokens']} out"
                       + (f" · ≈ ${cost * 1000:.2f} per 1,000 tickets at paid list price" if cost else ""))

# ---------------------------------------------------------------- Tab 2: scorecard
with tab_score:
    sc = load_scorecard()
    if not sc:
        st.info("Run `evals/scorecard.py` to generate the scorecard.")
    else:
        scores, details, targets = sc["scores"], sc["details"], sc["targets"]
        models = list(scores)
        st.markdown("50 hand-labelled tickets · **targets set in the PRD before the run** · "
                    "replies checked for invented facts by a blind LLM grader")

        def fmt(v, kind):
            if v is None or v != v:  # NaN
                return "n/a"
            return {"pct": f"{v * 100:.0f}%", "s": f"{v:.1f}s", "usd": f"${v:.2f}", "raw": str(v)}[kind]

        rows = [
            ("⭐ Urgent tickets caught (High recall)", "high_recall", "pct"),
            ("Category accuracy", "category_accuracy", "pct"),
            ("Priority accuracy", "priority_accuracy", "pct"),
            ("No invented facts (groundedness)", "groundedness", "pct"),
            ("Median response time", "median_latency_s", "s"),
            ("Slowest 10% response time", "p90_latency_s", "s"),
            ("Marked High that were truly High", "high_precision", "pct"),
            ("Under-prioritised (costly error)", "under_prioritised", "pct"),
            ("Over-prioritised (cheaper error)", "over_prioritised", "pct"),
            ("Sent to a human", "routed_to_human", "pct"),
            ("Valid output format", "valid_output", "pct"),
            ("Cost per 1,000 tickets (paid list price)", "cost_per_1k_tickets_usd", "usd"),
            ("Replies graded", "replies_graded", "raw"),
        ]
        table = []
        for label, key, kind in rows:
            row = {"Metric": label}
            if key in targets:
                t, op = targets[key]
                row["Target"] = ("≥ " if op == ">=" else "≤ ") + fmt(t, kind)
            else:
                row["Target"] = ""
            for m in models:
                v = scores[m].get(key)
                cell = fmt(v, kind)
                if key in targets and v is not None and v == v:
                    t, op = targets[key]
                    cell += " ✅" if (v >= t if op == ">=" else v <= t) else " ❌"
                row[m] = cell
            table.append(row)
        st.dataframe(pd.DataFrame(table), hide_index=True, width="stretch")
        graded = [scores[m].get("replies_graded", 0) for m in models]
        if min(graded) < 50:
            st.caption(f"⚠️ Groundedness is preliminary: {sum(graded)}/100 replies graded so far "
                       "(the free-tier grader quota ran out).")

        st.subheader("Where the models got it wrong")
        pick = st.radio("Model", models, horizontal=True, label_visibility="collapsed")
        misses = pd.DataFrame(details[pick]["misses"])
        if len(misses):
            misses = misses.rename(columns={"ticket_id": "Ticket", "message": "Message", "true_category": "True category",
                                            "category": "Model category", "true_priority": "True priority",
                                            "priority": "Model priority", "priority_reason": "Model's reason"})
            st.dataframe(misses, hide_index=True, width="stretch")
        ung = details[pick]["ungrounded"]
        if ung:
            st.markdown("**Replies flagged for unsupported facts**")
            for x in ung:
                st.markdown(f"- **{x['ticket_id']}** “{x['message']}” → {x['unsupported_claims']}")

        st.subheader("Priority: human label vs. model")
        conf = pd.DataFrame(details[pick]["priority_confusion"]).rename(
            index=lambda i: f"Human: {i}", columns=lambda c: f"Model: {c}")
        st.dataframe(conf, width="content")

# ---------------------------------------------------------------- Tab 3: how it works
with tab_how:
    st.markdown("""
### The problem
B2B SaaS support teams triage every ticket by hand: read, tag, prioritise, route, look up the policy, write a reply.
Urgent tickets (a failing payment, a customer asking about exit fees) wait behind newsletter requests, and priority
depends on who reads the ticket. When I hand-labelled 50 tickets against my own written rubric, my first pass was
only **74% consistent**.

### The workflow
**Today:** ticket → shared queue → agent reads → tags and prioritises → searches the help centre → writes a reply.

**With the copilot:** ticket → AI classifies it and sets priority using the team's rubric → auto-routed and sorted
by urgency → AI drafts a reply using only help-centre facts and cites the article → the agent edits and sends.
High-priority, angry or low-confidence tickets are flagged for a senior agent by a **coded rule**, not by the model.

### Build vs. integrate
The customer already has a helpdesk (Zendesk, Freshdesk, Intercom…). Replacing it would kill adoption, so the product
is an **AI layer that plugs in**: a webhook sends each new ticket to the service, and the helpdesk API writes back
tags, priority and the draft as an internal note. *This demo stands in for that agent view; live helpdesk
integration is designed but not built.*

### How quality was measured
- **Golden set:** 50 tickets from the public Bitext dataset, 8 SaaS categories, priority hand-labelled against a
  written rubric (v2, tightened after the 74% first pass).
- **Targets set before the run:** ≥90% urgent tickets caught, ≥90% category accuracy, ≥75% priority accuracy,
  ≥95% of replies with no invented facts, ≤3s median response time.
- **Grader:** a separate LLM checks each reply against the help centre, blind to which model wrote it.
- **Reliability:** each model has a backup from another vendor.

### Honest limitations
- Test tickets are short and single-issue; real B2B tickets are longer, so these results are an upper bound.
- 50 tickets separate models with big quality differences (±10 points), not small ones.
- Free-tier models were used for the prototype; production needs a paid tier with a data-processing agreement.
""")
