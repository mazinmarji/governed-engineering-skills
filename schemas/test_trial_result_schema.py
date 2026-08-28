"""The trial-result schema, measured against the contradiction that produced it.

M2, from Trial A: the first schema required `outcome`, `counterfactual_answer`,
`adjudicator` and `claim_licensed` of a single flat record -- exactly the four
fields the execution protocol forbids the builder to author. The trial runner
could either violate the protocol or ship an invalid record. Trial A shipped the
invalid record and reported the contradiction.

These tests fix the property, not the wording: an un-adjudicated builder record
must be VALID, and a builder who fills the adjudication in must be REFUSED.

Trial A's own record is deliberately NOT retrofitted to this schema. It was
produced against the frozen instrument and stands as evidence of what that
instrument did.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

jsonschema = pytest.importorskip("jsonschema")

SCHEMA = json.loads((Path(__file__).parent / "trial_result.schema.json").read_text(encoding="utf-8"))


def _builder_record(**overrides) -> dict:
    """The record a trial runner can actually produce, on its own authority."""
    record = {
        "record_status": "AWAITING_ADJUDICATION",
        "trial_id": "X-example",
        "pre_registration_digest": "abc123",
        "executed_at": "2026-08-28",
        "head_sha": "0" * 40,
        "findings": [
            {
                "id": "F1", "lens": "S4", "attribution": "PRE_REGISTERED",
                "description": "a control that could not fail",
                "evidence": ["mutation: specimen stayed green"],
                "material": True,
            }
        ],
    }
    record.update(overrides)
    return record


ADJUDICATION = {
    "outcome": "P-VALIDATED",
    "authored_by": "an adjudicator",
    "adjudicator": "an adjudicator",
    "counterfactual_answer": "the ordinary baseline probably would not have caught it",
    "claim_licensed": "value shown on one bounded change",
}


def _errors(record: dict) -> list[str]:
    validator = jsonschema.Draft202012Validator(SCHEMA)
    return [error.message for error in validator.iter_errors(record)]


def test_a_builder_record_without_an_adjudication_is_valid(tmp_path: Path):
    """THE FIX. This exact shape was invalid under the first schema.

    A record awaiting adjudication is complete and valid, not a draft. If this
    fails, the trial runner is again forced to choose between violating the
    protocol and shipping an invalid record.
    """
    assert _errors(_builder_record()) == [], (
        "a record the builder is permitted to author does not validate; M2 is back"
    )


def test_a_builder_who_fills_in_the_adjudication_is_refused(tmp_path: Path):
    """The other direction, which matters more.

    Making the un-adjudicated record valid is worth nothing if the builder can
    also author the adjudicator's verdict and still pass. The status and the
    section must agree.
    """
    errors = _errors(_builder_record(adjudication=dict(ADJUDICATION)))
    assert errors, (
        "a record still marked AWAITING_ADJUDICATION carried a completed "
        "adjudication and validated, so the builder can author the verdict"
    )


def test_an_adjudicated_record_must_carry_the_adjudication(tmp_path: Path):
    """The status may not claim what the record does not contain."""
    errors = _errors(_builder_record(record_status="ADJUDICATED"))
    assert errors, "a record claimed ADJUDICATED while carrying no adjudication"

    assert _errors(_builder_record(record_status="ADJUDICATED", adjudication=dict(ADJUDICATION))) == []


@pytest.mark.parametrize(
    "missing",
    ["outcome", "authored_by", "adjudicator", "counterfactual_answer", "claim_licensed"],
)
def test_every_adjudication_field_is_required_of_the_adjudicator(missing: str):
    """A partial adjudication is not an adjudication.

    Each of these was required of the BUILDER by the first schema. They are
    still required -- of the party who may actually author them.
    """
    partial = {key: value for key, value in ADJUDICATION.items() if key != missing}
    errors = _errors(_builder_record(record_status="ADJUDICATED", adjudication=partial))
    assert errors, f"an adjudication missing {missing!r} validated"


def test_the_middle_outcome_cannot_be_spelled_as_a_pass():
    """The enum is closed. `P-USEFUL-BUT-NOT-VALIDATING` must not become a pass
    by being renamed into something that sounds like one."""
    for invented in ("P-PASS", "PASS", "P-USEFUL", "VALIDATED"):
        adjudication = dict(ADJUDICATION, outcome=invented)
        errors = _errors(_builder_record(record_status="ADJUDICATED", adjudication=adjudication))
        assert errors, f"invented outcome {invented!r} validated"
