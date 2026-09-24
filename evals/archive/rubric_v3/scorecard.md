# Evaluation Scorecard

Golden set: 50 tickets · targets fixed in `docs/prd.md` before the run · grader: blind, batched LLM review

| Metric | Target | Gemini 3.5 Flash-Lite | Ministral 14B |
|---|---|---|---|
| ⭐ High-priority recall | ≥ 90% | 94% ✅ | 94% ✅ |
| Category accuracy | ≥ 90% | 98% ✅ | 100% ✅ |
| Priority accuracy | ≥ 75% | 94% ✅ | 94% ✅ |
| Groundedness (no invented facts) | ≥ 95% | n/a | n/a |
| Median latency | ≤ 3.0s | 1.7s ✅ | 2.1s ✅ |
| Tickets answered |  | 50/50 | 50/50 |
| Valid structured output |  | 100% | 100% |
| High-priority precision |  | 100% | 94% |
| Under-prioritised (costly error) |  | 6% | 4% |
| Over-prioritised (cheaper error) |  | 0% | 2% |
| Reply fully answers question |  | n/a | n/a |
| Routed to a human |  | 34% | 38% |
| p90 latency |  | 1.9s | 2.6s |
| Avg tokens in / out |  | 2819 | 2786 |
| Cost per 1,000 tickets (paid list price) |  | $1.15 | $0.59 |

## Gemini 3.5 Flash-Lite: misses (4)

| Ticket | Message | Category (true → model) | Priority (true → model) | Model's reason |
|---|---|---|---|---|
| T004 | can you help me to talk with an assistant? | CONTACT | **M → L** | Questions about support hours or contact channels are classified as Low priority. |
| T027 | problems with platinum account deletions | **ACCOUNT → CANCEL** | H | Any question about cancellation, exit or early-termination fees is High priority. |
| T032 | I have got to talk with a live agent | CONTACT | **M → L** | Questions about support hours or contact channels are classified as Low priority. |
| T037 | you are not helpful, can I speak with a person? | CONTACT | **H → M** | Customer is asking for a human agent, which is a Medium priority task. |

## Ministral 14B: misses (3)

| Ticket | Message | Category (true → model) | Priority (true → model) | Model's reason |
|---|---|---|---|---|
| T035 | i have got to look for bill #85632 | INVOICE | **M → L** | Customer is requesting a specific invoice, which is a routine information request with no urgency or risk. |
| T037 | you are not helpful, can I speak with a person? | CONTACT | **H → M** | Customer explicitly asked to speak with a human agent now, which qualifies as a medium-priority request under the rubric (v3). |
| T048 | I'm trying to request rebates of my money | REFUND | **M → H** | Asking about refund status or a problem with a refund qualifies as High priority if there is a perceived issue ('rebates of my money' implies a refund is expected but not received or disputed). |
