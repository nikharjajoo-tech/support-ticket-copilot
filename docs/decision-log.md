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
