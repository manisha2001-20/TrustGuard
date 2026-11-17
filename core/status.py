"""User-facing decision status: never call a result VERIFIED when no legal claim was verified.

The release policy (middleware/policy.py) deliberately allows a *clean abstention* to be released
(e.g. "The provided legal sources do not address this question."), and the pipeline finalises it under the
category "VERIFIED". That decision is correct - the abstention asserts no law - but the label is not: zero claims
were verified. This module corrects the label wherever a report leaves the system (API responses, the stored
audit record, the UI, exports).

It is applied at the serialisation / read boundary on purpose: middleware/pipeline.py and middleware/policy.py
are part of the frozen evaluation artifact set (evaluation/freeze.py), and the evaluation harness reads the
in-memory report directly, so held-out results and the frozen-artifact hash are unaffected.
"""
from __future__ import annotations

VERIFIED = "VERIFIED"
NOT_VERIFIED = "NOT_VERIFIED"
NOT_VERIFIED_EXPLANATION = (
    "Not verified - insufficient evidence. No legal claim was verified: the indexed legal sources do not "
    "contain evidence that answers this question, so no legal answer is given. "
    "0 material claim(s) verified against traceable evidence."
)


def verified_claim_count(report: dict) -> int:
    """Material claims marked SUPPORTED in the final attempt of a serialised report."""
    attempts = report.get("attempts") or []
    if not attempts:
        return 0
    claims = attempts[-1].get("claims") or []
    return sum(1 for cv in claims
               if cv.get("status") == "SUPPORTED" and (cv.get("claim") or {}).get("material", True))


def normalize_status(report: dict) -> dict:
    """Relabel a VERIFIED report that verified zero claims as NOT_VERIFIED (in place; also returned).

    Only the category and explanation change. The decision value and released text are left as they are, so
    API consumers and stored records keep their meaning (a released abstention).
    """
    if report.get("decision_category") == VERIFIED and verified_claim_count(report) == 0:
        report["decision_category"] = NOT_VERIFIED
        report["explanation"] = NOT_VERIFIED_EXPLANATION
    return report
