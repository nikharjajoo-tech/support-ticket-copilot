# Evaluation Scorecard

Golden set: 50 tickets · targets fixed in `docs/prd.md` before the run · grader: blind, batched LLM review

| Metric | Target | Gemini 3.5 Flash-Lite | Ministral 14B |
|---|---|---|---|
| ⭐ High-priority recall | ≥ 90% | 100% ✅ | 100% ✅ |
| Category accuracy | ≥ 90% | 98% ✅ | 100% ✅ |
| Priority accuracy | ≥ 75% | 100% ✅ | 94% ✅ |
| Groundedness (no invented facts) | ≥ 95% | 100% ⚠️ preliminary (n=6) | 100% ⚠️ preliminary (n=4) |
| Median latency | ≤ 3.0s | 1.8s ✅ | 2.0s ✅ |
| Tickets answered |  | 50/50 | 50/50 |
| Valid structured output |  | 100% | 100% |
| High-priority precision |  | 100% | 86% |
| Under-prioritised (costly error) |  | 0% | 0% |
| Over-prioritised (cheaper error) |  | 0% | 6% |
| Reply fully answers question |  | 100% ⚠️ preliminary (n=6) | 100% ⚠️ preliminary (n=4) |
| Routed to a human |  | 36% | 42% |
| p90 latency |  | 2.1s | 2.6s |
| Avg tokens in / out |  | 2953 | 2921 |
| Cost per 1,000 tickets (paid list price) |  | $1.19 | $0.61 |

⚠️ Grader metrics are preliminary: fewer than 80% of replies graded so far (free-tier grader quotas). Pass/fail is not claimed until grading completes.

## Gemini 3.5 Flash-Lite: misses (1)

| Ticket | Message | Category (true → model) | Priority (true → model) | Model's reason |
|---|---|---|---|---|
| T027 | problems with platinum account deletions | **ACCOUNT → CANCEL** | H | Any question about cancellation, exit or early-termination fees or account deletion blocks under annual contracts is classified as High priority. |

## Ministral 14B: misses (3)

| Ticket | Message | Category (true → model) | Priority (true → model) | Model's reason |
|---|---|---|---|---|
| T026 | need help to see the status of my refund | REFUND | **M → H** | Refund status or problem with a refund is a high-priority issue due to money at risk. |
| T030 | i need assistance opening a platinum account for my daughter | ACCOUNT | **M → H** | Customer is attempting to sign up for a paid plan, which is a critical action for product access. |
| T036 | where could i leave a fucking comment for a service | FEEDBACK | **M → H** | Formal complaint indicated by profanity and explicit request for feedback/complaint channel, bumping priority from base level (L) to H due to frustration. |
