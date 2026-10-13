# Module 09: Quality Reviewer / Critic Agent

## 1. What It Does in 3 Sentences
The Quality Reviewer (Critic) module serves as an internal adversarial safety auditor that inspects the findings of all upstream agents before any recommendations reach human engineers. It cross-checks mathematical calculations, tolerance bounds, and sample-size validity to ensure no contradictory conclusions exist. Crucially, it scans agent outputs for unproven causal claims (e.g. "definitely caused by"), intercepting unsupported assumptions and forcing reassessment loops if needed.

## 2. Key Functions and File Paths
- `QualityReviewerCriticAgent.review_workflow()` in [`backend/app/agents/reviewer_agent.py`](file:///d:/Projects%20Local/QT/backend/app/agents/reviewer_agent.py)
- `scan_unsupported_causal_claims()` in [`backend/app/agents/reviewer_agent.py`](file:///d:/Projects%20Local/QT/backend/app/agents/reviewer_agent.py)
- Schema definitions in [`backend/app/schemas/schemas.py`](file:///d:/Projects%20Local/QT/backend/app/schemas/schemas.py) (`CriticReview`, `CertaintyLevel`)

## 3. Formula / Algorithm in Plain Words with BATCH-0245 Worked Example
The Critic agent evaluates four safety criteria:
1. **Mathematical Consistency**: Verifies that non-conformance rate equals $(\text{nonconforming\_count} / \text{total}) \times 100\%$ within a 0.01% epsilon.
2. **Tolerance Logic**: Verifies that reported deviations equal measured values minus nominal.
3. **Capability Guardrail**: Verifies that if $n < 30$, a sample-size warning was included.
4. **Causal Interception Regex**:
   Scans text against forbidden assertional patterns:
   $$\text{Pattern} \in \{\text{"definitely caused"}, \text{"proves causation"}, \text{"proven root cause"}, \text{"root cause is"}, \text{"caused by"}\}$$
   If a match is found and the finding is not backed by physical verification, the verdict is set to `REVISE_HYPOTHESIS`.

**Worked Example from BATCH-0245:**
- The Critic reviews BATCH-0245:
  - Math check: $3/5 = 60.0\%$ matches intake and dimensional reports.
  - Limits check: Max deviation $+0.03\,\text{mm}$ matches sample P004 ($50.08 - 50.05$).
  - Guardrail check: $n=5 < 30$ warning confirmed present.
  - Causal scan: Text states `"Tool wear is the primary hypothesis pending engineering verification"` $\implies$ No unproven causal assertions detected.
- **Verdict**: `APPROVED` (Verdict notes: "All mathematical calculations verified. Epistemic boundary respected. Package cleared for Human-in-the-Loop review.").

## 4. Design Decision and Alternative
- **Decision**: An independent Critic agent with authority to loop execution back to the RCA agent via LangGraph conditional edges.
- **Alternative**: Relying on single-pass agent outputs without internal review.
- **Why Chosen**: In mission-critical aerospace and automotive quality, early hallucinated assumptions that confuse correlation with causation lead to wasted teardowns and unaddressed defects.

## 5. One Limitation
The causal regex scanner checks English terminology; if an LLM outputs subtly overstated causal assertions in an unexpected phrasing not caught by the pattern set, it relies on the human Quality Engineer at the approval gate as the final backstop.

## 6. Three Questions an Examiner Might Ask with Factual Answers
1. **Q: How does the system handle an injected unproven causal claim during testing?**
   - *Answer*: In test `test_critic_catches_injected_causal_claim`, when text containing `"Tool wear definitely caused the defect"` is injected, the Critic catches the phrase, sets `unsupported_causal_claims_detected=True`, changes verdict to `REVISE_HYPOTHESIS`, and routes back for revision.
2. **Q: What is the maximum number of reassessment loops allowed before escalating?**
   - *Answer*: The workflow state tracks `reassessment_loops`; if the loop count reaches 2 without resolving concerns, it escalates directly to human engineers with an audit discrepancy warning to avoid infinite recursion.
3. **Q: What epistemic label is assigned to the Critic's review?**
   - *Answer*: `[STATISTICAL FINDING]`, because it is an algorithmic safety audit of calculations and language adherence.
