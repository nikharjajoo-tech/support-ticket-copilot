# PRD: AI Support Ticket Copilot

| | |
|---|---|
| **Author** | Nikhar Jajoo (Product) |
| **Status** | Prototype + evaluation |
| **Last updated** | 2026-09-23 |
| **Type** | Portfolio project. Target customer is illustrative; "Nimbus CRM" is a fictional company. Impact figures are **projections from stated assumptions**; model quality, latency and cost figures are **measured** on the eval set. |

## 1. Problem

B2B SaaS support teams triage every ticket by hand: read it, tag it, set a priority, route it, find the relevant policy, write a reply. At ~2,000 tickets/day this creates four problems:

1. **Urgent tickets get buried.** Queues are first-come-first-served, so "my payment is failing" or "what's the exit fee?" (a churn signal) waits behind newsletter requests.
2. **Priority is inconsistent.** It depends on who reads the ticket. When I hand-labelled 50 tickets against my *own* written rubric, my first pass was only **74% consistent** (see decision-log D3).
3. **Misrouting.** Wrong tags send tickets to the wrong team and they bounce.
4. **Agent time goes to work that doesn't need judgement:** reading, tagging, searching the help centre and retyping standard answers. Headcount grows with ticket volume.

## 2. Target customer and users

- **Buyer:** Head of Support / Support Ops at a mid-size B2B SaaS company (illustrative profile: 20 agents, ~2,000 tickets/day, already using a helpdesk such as Zendesk, Freshdesk or Intercom).
- **Primary user:** Tier-1 support agent.
- **Secondary user:** Support team lead, who owns the priority policy and wants consistency plus visibility into what's urgent.

## 3. Current workflow → proposed workflow

**Today (manual)**
```
Ticket → shared queue (FIFO) → agent reads → tags category + priority → routes
       → searches help centre → writes reply → sends / escalates
```

**Proposed (AI-assisted, human in the loop)**
```
Ticket → AI (~seconds): category, priority (team's rubric), sentiment, confidence
       → auto-routed to the right queue, sorted by priority
       → AI drafts a reply grounded ONLY in help-centre articles, citing the article used
       → agent reviews / edits / sends
       → low confidence, High priority or angry customer → flagged for a senior agent
```

## 4. Solution scope

**Build vs. integrate:** The customer already has a helpdesk. Replacing it means migrating ticket history, retraining agents and rebuilding reports, a switching cost that would kill adoption. **The product is an AI layer that plugs into the existing helpdesk** via webhook (new ticket → our service) and REST API (write back tags, priority and the draft as an internal note). Agents never leave their current tool.

**In scope (this prototype)**
- Triage engine: category (8 classes), priority (H/M/L per rubric v2), sentiment, needs-human flag, confidence.
- Grounded reply drafting from a small help centre (8 articles).
- Evaluation harness: golden set of 50 tickets, 3 models compared, automated grader for reply quality, scorecard.
- Demo UI (Streamlit) standing in for the agent's view.

**Out of scope (designed, not built)**
- Live helpdesk integration (webhook + API write-back). *Stretch: connect a Freshdesk/Zendesk trial.*
- Auto-sending replies without a human (Phase 2, only for Low-risk categories once proven).
- Vector search over a large help centre (unnecessary at 8 articles; needed at hundreds).
- Multi-language, attachments, multi-issue tickets.

## 5. Requirements

| # | Requirement | Priority |
|---|---|---|
| R1 | Classify each ticket into one of 8 categories | Must |
| R2 | Assign H/M/L priority using the team's written rubric (rubric text passed to the model verbatim) | Must |
| R3 | Output a fixed, machine-readable format (JSON), so results can be written back to a helpdesk | Must |
| R4 | Draft replies use only facts from help-centre articles and name the article used; if no article covers the question, say so and flag for a human | Must |
| R5 | Flag for a human when priority = H, sentiment is angry, or confidence is low | Must |
| R6 | Report latency and token usage per ticket (for cost) | Must |
| R7 | Model choice configurable, so we can switch vendors without code changes | Should |

## 6. Success metrics and launch criteria

Targets set **before** running the evaluation.

| Metric | Definition | Target | Why this target |
|---|---|---|---|
| ⭐ **High-priority recall** | % of truly-High tickets the model marks High | **≥ 90%** | Missing an urgent/churn ticket is the costliest error |
| Category accuracy | % correct category vs. dataset labels | ≥ 90% | Wrong category = misrouting |
| Priority accuracy | % exact match vs. my labels | ≥ 75% | Human first pass was 74%; the model should at least match that |
| Groundedness | % of drafts with no facts missing from the help centre (judged by grader model) | ≥ 95% | An invented refund policy is a legal/trust risk |
| Median latency | Seconds per ticket | ≤ 3s | Must feel instant inside the agent's workflow |
| Cost | $ per 1,000 tickets at paid-tier list prices (from measured tokens) | Report | Business case input |

**Decision rule:** Pick the cheapest/fastest model that meets every "Must" target. If none meets them all, report which ones fail and why.

## 7. Projected impact (assumptions, to be validated)

| Assumption (illustrative) | Manual | With copilot |
|---|---|---|
| Triage time / ticket | 1.5 min | 0.25 min (confirm) |
| Reply time / ticket | 5 min | 2.5 min (edit draft) |

At 2,000 tickets/day: ~3.75 min × 2,000 ≈ **125 agent-hours/day ≈ 15 FTE of capacity** freed to absorb growth, set against measured AI cost per ticket. The bigger benefit is probably not speed: **urgent and churn-risk tickets are handled first, under one consistent policy.**

*Validation plan:* 15-minute interviews with 2–3 support agents or leads to confirm triage/reply times and pain points.

## 8. Architecture

| Layer | Prototype | Production |
|---|---|---|
| Ticket source | Bitext dataset (50-ticket golden set) | Helpdesk webhook |
| Models | Gemini 3.5 Flash-Lite, Gemini 3.5 Flash, Ministral 14B (free tiers) | Winning model on a paid tier with a data-processing agreement |
| Knowledge | 8 articles in the prompt | Vector search over the full help centre (RAG) |
| Backend | None (app calls models directly) | FastAPI service + queue for spikes |
| Storage | CSV | Postgres log of every AI decision + agent edit |
| Eval | Golden set + LLM grader + scorecard | Same, re-run before every prompt/model change + daily spot checks |
| Monitoring | Printed scorecard | LLM observability (e.g. Langfuse) |
| Privacy | Public data only | Remove personal data before the LLM call; secrets manager |
| UI | Streamlit (Community Cloud) | Inside the existing helpdesk |

## 9. Risks

| Risk | Mitigation |
|---|---|
| Model invents a policy in a reply | Grounding instruction + groundedness metric + human sends every reply |
| Urgent ticket marked Low | High-recall target; H/angry/low-confidence tickets always go to a human |
| Test set easier than real tickets | Stated limitation; real B2B tickets are longer and multi-issue. Expand the golden set from production samples |
| Grader model biased toward its own vendor | Noted; spot-check a sample of grades by hand |
| Vendor retires a model (already saw gemini-2.5-flash retired) | Model is a config setting; re-run eval before switching |
| Free tier trains on data | Prototype uses public data only; production requires a paid tier + DPA |

## 10. Open questions
- Does Gemini 3.5 Flash's default "thinking" explain its ~15s latency, and is quality worth it?
- Optional scale check: category accuracy on ~200 tickets (labels free from the dataset) for the cheapest model.
