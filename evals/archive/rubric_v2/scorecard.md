# Evaluation Scorecard

Golden set: 50 tickets · targets fixed in `docs/prd.md` before the run · grader: blind, batched LLM review

| Metric | Target | Gemini 3.5 Flash-Lite | Ministral 14B |
|---|---|---|---|
| ⭐ High-priority recall | ≥ 90% | 94% ✅ | 100% ✅ |
| Category accuracy | ≥ 90% | 98% ✅ | 98% ✅ |
| Priority accuracy | ≥ 75% | 84% ✅ | 84% ✅ |
| Groundedness (no invented facts) | ≥ 95% | 100% ✅ | 73% ❌ |
| Median latency | ≤ 3.0s | 1.8s ✅ | 2.1s ✅ |
| Tickets answered |  | 50/50 | 50/50 |
| Valid structured output |  | 100% | 98% |
| High-priority precision |  | 89% | 75% |
| Under-prioritised (costly error) |  | 6% | 0% |
| Over-prioritised (cheaper error) |  | 10% | 16% |
| Reply fully answers question |  | 100% | 100% |
| Routed to a human |  | 38% | 48% |
| p90 latency |  | 11.4s | 2.8s |
| Avg tokens in / out |  | 2646 | 2614 |
| Cost per 1,000 tickets (paid list price) |  | $1.12 | $0.55 |

## Gemini 3.5 Flash-Lite: misses (9)

| Ticket | Message | Category (true → model) | Priority (true → model) | Model's reason |
|---|---|---|---|---|
| T001 | I want assistance to check the goddamn payment methods | PAYMENT | **M → L** | Any question about payment methods is low priority as it is an information request with no action needed urgently. |
| T018 | how do I see at what time customer assistance available is? | CONTACT | **L → M** | Customer is asking about support hours, which falls under the Medium priority rule for getting help or reaching a human agent. |
| T025 | help to check what hours customer assistance available is | CONTACT | **L → M** | Customer is asking for human support hours, which is classified as Medium priority. |
| T027 | problems with platinum account deletions | **ACCOUNT → CANCEL** | H | Any question about cancellation is classified as High per the explicit priority rules. |
| T036 | where could i leave a fucking comment for a service | FEEDBACK | **M → L** | Profanity alone does not make a ticket high priority, so it remains low priority for leaving feedback. |
| T037 | you are not helpful, can I speak with a person? | CONTACT | **H → M** | Customer is asking for a human agent with strong frustration, bumped up one level per the tie-breaker rule. |
| T044 | where do I check what hours I can reach customer service? | CONTACT | **L → M** | Customer needs to know support hours, which is a medium priority task since they are not blocked. |
| T045 | I don't know what to do to get a reimbursement | REFUND | **M → H** | Refund status or problems are classified as High priority. |
| T048 | I'm trying to request rebates of my money | REFUND | **M → H** | Refund status or problem is rated High if something is unclear or needs attention. |

## Ministral 14B: misses (9)

| Ticket | Message | Category (true → model) | Priority (true → model) | Model's reason |
|---|---|---|---|---|
| T001 | I want assistance to check the goddamn payment methods | PAYMENT | **M → H** | Strong frustration ('goddamn') bumps priority up one level, capped at H. |
| T025 | help to check what hours customer assistance available is | CONTACT | **L → M** | Customer is seeking information about support availability, which is not urgent but requires clarification. |
| T026 | need help to see the status of my refund | REFUND | **M → H** | Customer is asking about refund status, which is a refund problem (H priority). |
| T030 | i need assistance opening a platinum account for my daughter | ACCOUNT | **M → H** | Customer is blocked from creating a Platinum account for a new user, which may prevent product usage. |
| T036 | where could i leave a fucking comment for a service | FEEDBACK | **M → H** | Strong frustration (profanity) → bump up one level, capped at H. |
| T044 | where do I check what hours I can reach customer service? | CONTACT | **L → M** | Customer needs to know support hours, no urgency or risk involved. |
| T045 | I don't know what to do to get a reimbursement | REFUND | **M → H** | Customer is asking about a refund status or problem, which is a churn signal. |
| T048 | I'm trying to request rebates of my money | REFUND | **M → H** | Customer is asking about refund status or a problem with a refund, which is a churn signal. |
| T049 | update details on platinum account | **ACCOUNT → {'TYPE': 'ACCOUNT'}** | M | {'type': 'string', 'description': 'Customer needs to update account details, but is not blocked or at risk of churn.'} |

**Ungrounded replies (3)**

- T009 "show me bill #00108": ask your workspace admin to share it with you
- T020 "open gold cacount for wife": Each workspace must have its own admin email
- T032 "I have got to talk with a live agent": For urgent matters outside these hours
