# Decision Log

Running record of product and technical decisions, with the evidence behind each.

## D1: Model shortlist (2026-09-23)

**Context:** Free-tier API keys only (Google AI Studio, Mistral "Experiment" plan). Listed models ≠ callable models, so each candidate got a one-line smoke test.

| Model | Result | Latency (1-line reply) |
|---|---|---|
| gemini-3.5-flash | ✅ works | ~15s |
| gemini-3.5-flash-lite | ✅ works | ~1.4s |
| gemini-flash-latest | ✅ works (alias) | ~15s |
| gemini-2.5-flash | ❌ 404, retired for new users | — |
| ministral-8b-latest | ✅ works | ~0.8s |
| ministral-14b-latest | ✅ works | ~1.2s |
| mistral-small-latest / -2603 | ❌ 429 rate-limited, even with 3s gaps | — |
| mistral-medium-latest | ❌ 429 rate-limited | — |

**Decision:** Compare 3 models: `gemini-3.5-flash-lite`, `gemini-3.5-flash`, `ministral-14b-latest`.

**Why:**
- Mixes a fast/cheap tier and a stronger tier, from two vendors, for a real trade-off.
- Mistral Small/Medium were not reliably callable on the free tier. A model you can't call consistently is a non-starter, whatever its benchmark scores.
- gemini-2.5-flash is retired: a reminder that model choice needs a migration plan, not a one-time pick.

**Open question:** Is Gemini 3.5 Flash's ~15s latency due to default "thinking"? It matters for a live support tool. Test in the eval step.

## D2: Test set ("golden set") (2026-09-23)

**Source:** Bitext Customer Support dataset (Hugging Face), 26,872 labelled customer messages.

**Decision:** 50 tickets, stratified across 8 SaaS-relevant categories (6–7 each, 18 intents): ACCOUNT, INVOICE, PAYMENT, REFUND, NEWSLETTER, CANCEL, CONTACT, FEEDBACK. Excluded ORDER/SHIPPING/DELIVERY (e-commerce) and messages with unfilled `{{placeholders}}`. Fixed random seed, so the set can be reproduced.

**Data-quality finding:** Bitext's `SUBSCRIPTION` category is entirely *newsletter* sign-ups, not SaaS plan subscriptions. Renamed it to `NEWSLETTER` so the label means what it says and the models aren't nudged toward the wrong meaning.

**Priority labels:** Not in the source data. Hand-labelled by me (the PM) against the rubric in `docs/priority-rubric.md`, so "correct priority" reflects an explicit business policy, not a model's guess.

**Known limitations:** Messages are short, single-issue and often have typos. Real B2B tickets are longer and multi-issue, so results here are an upper bound on real-world accuracy. 50 tickets is enough to separate models with clearly different quality, not ones within a few points of each other.

## D3: Priority labels and rubric v2 (2026-09-23)

**What happened:** I hand-labelled all 50 tickets H/M/L. A consistency check found near-identical tickets with different labels, e.g. six "what's the early exit fee?" tickets labelled L, L, M, H, H, H. **13/50 tickets (26%) disagreed with my own written rubric → first-pass consistency 74%.**

**Why it matters:** The golden set is the answer key. If the answer key is inconsistent, a model gets marked "wrong" for matching a rule I didn't follow myself, and the accuracy numbers stop meaning anything.

**Decision:** Tightened the rubric to v2 (`docs/priority-rubric.md`) with explicit rules for the ambiguous cases: exit-fee questions = H (churn), downgrades = H (revenue), formal complaints = H, and profanity bumps one level rather than always meaning H. Re-labelled the 13 tickets. The first-pass labels are kept in `priority_first_pass` for transparency.

**Final distribution:** 18 High / 18 Medium / 14 Low, balanced enough that a model can't score well by always guessing one level.

**Product takeaway:** Priority is a *policy*, not a fact. Writing it down precisely was a prerequisite for automating it, and the same rubric text is given to the models, so humans and models are graded against the same rule.

## D4: First run of the engine, 4 tickets × 3 models (2026-09-23)

| Ticket (truth) | Flash-Lite | Gemini 3.5 Flash | Ministral 14B |
|---|---|---|---|
| T011 exit fee (CANCEL/H) | ✓ ✓ 2.5s | 503 overloaded | ✓ ✓ 4.1s |
| T037 "not helpful, need a person" (CONTACT/H) | ✓ **M ✗** 1.9s | 503 overloaded | ✓ ✓ 2.5s |
| T002 payment methods (PAYMENT/L) | ✓ ✓ 1.8s | 503 overloaded | ✓ ✓ 2.4s |
| T026 refund status (REFUND/M) | ✓ ✓ 1.6s | ✓ ✓ **64.8s** | ✓ **H ✗** 1.9s |

**Findings**
- All replies spot-checked were grounded: fees, hours, payment methods and menu paths match the help centre.
- **Flash-Lite said one thing and did another** on T037: its stated reason was "frustration bumps the priority up one level", but it output M. An urgent ticket marked Medium is the costliest error type (see High-recall target).
- **Ministral over-prioritised** T026, treating "refund status" as a refund problem. Per the rubric's tie-breaker, over-prioritising is the cheaper error.
- **Gemini 3.5 Flash is not viable as configured:** it failed with 503 "high demand" on 3/4 tickets (even after 5 retries with backoff), and the one success took 65s with ~1,000 hidden "thinking" tokens. **Availability and latency are product requirements, not just quality.**
- Each call uses ~2,650 input tokens, almost all of them the fixed instructions (rubric + help centre). In production, prompt caching would cut most of that cost.

**Next decision:** Re-test Gemini 3.5 Flash with thinking set to minimal before the full eval, to separate "slow because thinking" from "slow because overloaded".

## D5: Full evaluation, 50 tickets × 2 models (2026-09-23)

**Gemini 3.5 Flash disqualified before the full run:** its free tier allows 20 requests/day per model (quota hit mid-test), and even with thinking set to minimal it took 25s per ticket vs. the ≤3s target.

**Results** (targets fixed in the PRD beforehand; full table in `evals/scorecard.md`)

| | Flash-Lite | Ministral 14B |
|---|---|---|
| Urgent tickets caught (≥90%) | 94% ✅ (missed T037) | 100% ✅ |
| Category accuracy (≥90%) | 98% ✅ | 98% ✅ |
| Priority accuracy (≥75%) | 84% ✅ | 84% ✅ |
| Median / p90 latency | 1.8s / 11.4s | 2.1s / 2.8s |
| Sent to a human | 38% | 48% |
| Cost per 1,000 tickets | $1.12 | $0.55 |
| No invented facts (≥95%) | *preliminary* 9/9 | *preliminary* 8/11 |

**Findings**
- Both models beat my own first-pass labelling consistency (74%).
- Most priority misses were shared by both models and trace back to **rubric ambiguity**: support-hours questions, refund *requests* vs. refund *problems*, and how the profanity bump applies. Same lesson as D3: fix the policy wording before blaming the model.
- Ministral's 3 flagged replies were minor rewordings (e.g. "each workspace needs its own admin email" instead of "each user needs their own email"), not invented prices or policies. **A pass/fail groundedness score hides severity.**
- Ministral once returned its schema instead of an answer (T049). Fixed by switching Mistral from plain JSON mode to strict schema mode.

**Grader reliability:** free-tier graders were the bottleneck. gemini-3.7-flash and 3.8-flash were overloaded (503), and gemini-3.6-flash hit its 20/day quota after 20 replies; overload retries appear to count against the quota. The grader now has a fallback chain (Gemini 3.6 Flash → Mistral Medium → Mistral Small). Ministral is excluded as a grader because it is one of the models being graded. Remaining 80 replies to be graded after the quota resets.

**Decision (provisional):** **Ministral 14B as the default model**, with **Gemini 3.5 Flash-Lite as automatic fallback** (different vendor, so a single provider outage doesn't stop triage). Why: catches 100% of urgent tickets, half the cost, consistent latency. Its extra human hand-offs are the cheaper error under the rubric. Revisit when groundedness grading is complete.

## D6: Rubric v3 and v4 re-runs, and final model choice (2026-09-24)

Each rubric change was followed by a **full re-run of all 50 tickets on both models**, not just the previous misses, because the rubric is in every prompt and a fix for one ticket can break another.

| Metric | Flash-Lite v2 → v3 → v4 | Ministral 14B v2 → v3 → v4 |
|---|---|---|
| Priority accuracy | 84% → 94% → **100%** | 84% → 94% → 94% |
| Urgent tickets caught (High recall) | 94% → 94% → **100%** | 100% → 94% → 100% |
| Marked High that were truly High | 89% → 100% → 100% | 75% → 94% → 86% |
| Over-prioritised | 10% → 0% → 0% | 16% → 2% → 6% |
| Category accuracy | 98% → 98% → 98% | 98% → 100% → 100% |
| p90 latency | 11.4s → 1.9s → 2.1s | 2.8s → 2.6s → 2.6s |

**v3** (support hours = L, refund request = M, profanity bump explicit) fixed 14 errors but introduced 3 regressions, including T037, a frustrated customer asking for a person, which both models downgraded to M.
**v4** (reworded the support-hours rule; frustration + request for a person = H) fixed all 3 regressions.

**Run-to-run variance:** Ministral changed its answer on tickets whose rules did not change between v3 and v4 (e.g. T026 "status of my refund": M in v3, H in v4). Some variation between runs is noise, not the rubric. With 50 tickets, 94% vs 100% is a 3-ticket gap, within the ±7–10 point margin, so Flash-Lite's 100% is best read as "at least as good as Ministral, and more consistent", not "perfect".

**Decision: switch the default to Gemini 3.5 Flash-Lite, with Ministral 14B as the cross-vendor fallback** (reverses D5's provisional pick).
- Quality: no under- or over-prioritisation on v4, and no invented facts in the 9 replies graded so far (Ministral: 3 minor ones in 11).
- Stability: its answers held steady across rubric versions, where Ministral's flip-flopped.
- Cost: $1.19 vs $0.61 per 1,000 tickets with the v4 rubric (the longer rubric added ~300 input tokens per ticket; v2 was $1.12 vs $0.55). At 2,000 tickets/day that's about $71 vs $37 per month, a difference smaller than one agent-hour. **Quality and consistency outweigh the cost gap at this scale.**
- Latency: the 11s p90 seen in v2 did not recur (1.9–2.1s), so it was free-tier throttling, not the model.

**Still open:** groundedness grading for the v4 replies (all graders out of quota; resumes when quotas reset). Also, a repeat-run consistency test (same tickets, 3 runs per model) would measure variance directly.
