"""Regression: a released result with zero verified claims must never be presented as VERIFIED.

Also pins that the fix lives at the serialisation boundary only: the in-memory report the evaluation harness
reads is unchanged, and the frozen-artifact sources are not involved.
"""
from core.models import Decision
from core.status import NOT_VERIFIED, normalize_status
from llm.base import ScriptedLLM
from llm.prompts import ABSTAIN_TEXT
from middleware.pipeline import TrustGuardPipeline

Q_OUT = "What is the GST rate on mobile phones?"
Q_IN = "What is the punishment for murder under the BNS?"
CORRECT = ("Under Section 103 of the Bharatiya Nyaya Sanhita, murder is punishable with death or imprisonment "
           "for life, and shall also be liable to fine.")


def run(settings, db, index, answer, q, persist=False):
    return TrustGuardPipeline(settings, db, llm=ScriptedLLM([answer]), index=index).run(q, persist=persist)


def test_abstention_is_not_labelled_verified(settings, db, index):
    r = run(settings, db, index, ABSTAIN_TEXT, Q_OUT)
    d = r.to_dict(include_drafts=False)                      # what the API returns
    assert d["decision_category"] == NOT_VERIFIED
    assert "VERIFIED" not in d["decision_category"].replace(NOT_VERIFIED, "")
    assert "were verified" not in d["explanation"] and "insufficient evidence" in d["explanation"].lower()


def test_in_memory_report_unchanged_for_evaluation(settings, db, index):
    # the evaluation harness reads report.decision / decision_category directly; it must not shift
    r = run(settings, db, index, ABSTAIN_TEXT, Q_OUT)
    assert r.decision == Decision.RELEASED and r.decision_category == "VERIFIED"


def test_real_verified_answer_still_verified(settings, db, index):
    d = run(settings, db, index, CORRECT, Q_IN).to_dict()
    assert d["decision"] == "RELEASED" and d["decision_category"] == "VERIFIED"


def test_stored_and_listed_records_not_verified_and_chain_intact(settings, db, index):
    r = run(settings, db, index, ABSTAIN_TEXT, Q_OUT, persist=True)
    assert db.get_report(r.request_id)["decision_category"] == NOT_VERIFIED
    row = next(x for x in db.search_requests(limit=50) if x["request_id"] == r.request_id)
    assert row["category"] == NOT_VERIFIED and "report_json" not in row
    assert db.verify_audit_integrity()["intact"]


def test_legacy_record_normalised_on_read():
    legacy = {"decision": "RELEASED", "decision_category": "VERIFIED", "explanation": "All material legal claims "
              "were verified ... 0 material claim(s) verified.",
              "attempts": [{"claims": [{"status": "SUPPORTED", "claim": {"material": False}}]}]}
    assert normalize_status(legacy)["decision_category"] == NOT_VERIFIED
    ok = {"decision": "RELEASED", "decision_category": "VERIFIED", "explanation": "x",
          "attempts": [{"claims": [{"status": "SUPPORTED", "claim": {"material": True}}]}]}
    assert normalize_status(ok)["decision_category"] == "VERIFIED"
