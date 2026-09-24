# Ticket Priority Rubric

Business policy for how urgently a ticket needs a human response. Used to hand-label the golden set and given to the models word for word, so humans and models are graded against the same rule.

Lens: B2B SaaS. What matters most is (1) a customer who can't use the product, (2) money at risk, (3) churn risk.

| Priority | Definition | Typical examples |
|---|---|---|
| **H: High** | Customer is **blocked**, **money is at risk**, or there is a **churn signal**. | Can't sign up or log in; payment failing; refund not received or disputed; asking about cancellation or exit fees; angry complaint |
| **M: Medium** | Customer needs something done, but isn't blocked and nothing is at risk. | Get or check an invoice; change account details; asks for a human agent; refund *policy* question |
| **L: Low** | Information or courtesy request; no action needed urgently. | Which payment methods exist; newsletter subscribe/unsubscribe; leaving a review or positive feedback |

**Explicit rules** (added after the first labelling pass, v2)
- **Any question about cancellation, exit or early-termination fees = H.** Asking about exit costs is a churn signal even when phrased as "just checking".
- **Downgrade requests (e.g. to a free or lower plan) = H.** Revenue at risk.
- **Formal complaints ("lodge a complaint", "file a reclamation") = H.**
- Refund *status or problem* = H if something is wrong ("anything wrong with my refund"); otherwise M. Refund *policy* questions = M.
- **Asking how to get or request a refund = M.** Only H if an existing refund is late, missing or disputed. (v3)
- **Questions about *when or how* support can be reached (hours, email address, phone number) = L.** (v3, reworded v4)
- **Asking to talk to a person = M. If the customer is also frustrated ("not helpful", swearing, "again"), the frustration bump makes it H.** (v4)

**Tie-breakers**
- Strong frustration (swearing, "you are not helpful", "again", "still") → bump **up one level from the topic's base level**, capped at H. Example: payment-methods question (base L) with swearing = **M**, not H. Profanity alone never makes a ticket H. (v3 clarification)
- If the ticket fits two levels, pick the **higher** one. Under-prioritising costs more than over-prioritising.

**Changelog**
- v1 (2026-09-23): initial draft.
- v2 (2026-09-23): after a hand-labelling pass that was only 74% consistent with v1 (13/50 tickets), added explicit rules for exit fees, downgrades, formal complaints and refund status, and clarified the profanity rule.
- v3 (2026-09-24): both models made the same priority mistakes on support-hours questions, refund requests and profanity, so the wording was the problem. Added rules for refund requests and support-hours questions, and made the profanity bump explicit ("from the topic's base level"). No human labels changed.
- v4 (2026-09-24): v3 fixed 14 errors but caused 3 regressions: "contact channels = L" was read as covering requests for a live agent (T004, T032), and a frustrated customer asking for a person lost the frustration bump (T037, both models). Reworded the support-hours rule and stated explicitly that frustration raises a request for a person to H.
