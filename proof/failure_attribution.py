"""Attribute a test failure to a named node, phase, and property.

THE DEFECT THIS EXISTS TO PREVENT
---------------------------------
A process exit code is a coarse signal. `returncode != 0` is produced by a
refusal, a crash, a timeout, a collection error, an import failure, and an
unrelated test failing earlier in the same run. Reading it as "the named
control refused the named input" is substitution S4: a weaker signal standing
for a stronger property.

In the source programme this produced green suites over dead controls, and a
mutation campaign that scored kills it had not made.

PORTABILITY
-----------
This reads JUnit XML, not pytest internals, so it works for any runner that
emits JUnit: pytest (--junit-xml), JUnit/Maven/Gradle, Jest (jest-junit),
Go (go-junit-report), .NET (trx2junit). The one runner-specific assumption is
documented at `_phase_of` and is checked, not assumed.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

#: Outcomes a JUnit <testcase> can carry.
PASSED = "passed"
FAILED = "failed"
ERRORED = "errored"
SKIPPED = "skipped"
ABSENT = "absent"
#: A base name that several parametrizations answer to. Not a subject.
AMBIGUOUS = "ambiguous"

#: Phases. JUnit has no phase element; see `_phase_of` for how this is derived
#: and why the derivation is conservative.
CALL = "call"
NOT_CALL = "not_call"
PHASE_UNKNOWN = "phase_unknown"


@dataclass
class NodeOutcome:
    """What a JUnit report says about ONE named node."""

    node_id: str
    outcome: str
    phase: str
    message: str = ""
    detail: str = ""
    #: Every node id the report DID contain, when the requested one was absent.
    #: Without this an absent node is indistinguishable from a passing one, and
    #: "absent" reported as "did not fail" is how a deleted test reads as green.
    available: list[str] = field(default_factory=list)

    @property
    def failed_in_call(self) -> bool:
        return self.outcome == FAILED and self.phase == CALL


def _node_ids(case: ET.Element) -> list[str]:
    """Every spelling of this testcase's identity, most specific first.

    Runners disagree: pytest writes classname="tests.test_x" name="test_y",
    Jest writes the describe chain, Go writes the package. Callers should be
    able to pass whichever form they have, so match against all of them.
    """
    name = case.get("name", "")
    classname = case.get("classname", "")
    file_attr = case.get("file", "")
    spellings = []
    if classname and name:
        spellings.append(f"{classname}.{name}")
        # pytest's canonical form: path/to/test_x.py::test_y
        spellings.append(f"{classname.replace('.', '/')}.py::{name}")
    if file_attr and name:
        spellings.append(f"{file_attr}::{name}")
    if name:
        spellings.append(name)
    return spellings


def _matches(case: ET.Element, node_id: str) -> str | None:
    """How `node_id` names this case, or None.

    Returns ``"exact"`` when the id names this case outright, ``"parametrized"``
    when it names the case's BASE and this case is one parametrization of it.

    Suffix matching is deliberate: a caller holding `test_y` should match
    `tests/test_x.py::test_y`. It is anchored on a separator so `test_y` does
    NOT match `test_y_variant` -- a looser match would attribute one node's
    failure to another, which is the exact error this module exists to refuse.

    BASE-NAME MATCHING WAS ADDED AFTER A MEASURED FAILURE. A revert control
    naming `test_projection_is_closed` against a parametrized specimen got
    `absent`, reported as BASELINE_NOT_GREEN, because the JUnit id carries a
    `[parameter]` suffix. The direction was safe -- it refused rather than
    scoring a kill it had not made -- but the caller was told the node did not
    exist when in fact five parametrizations of it did. The `[` boundary keeps
    the anti-bleed property: `test_guard` matches `test_guard[case]` and still
    does not match `test_guard_variant`.
    """
    wanted = node_id.strip()
    anchored = r"[./:\\]" + re.escape(wanted)

    for spelling in _node_ids(case):
        if spelling == wanted:
            return "exact"
        if spelling.endswith(wanted) and re.search(anchored + r"$", spelling):
            return "exact"

    for spelling in _node_ids(case):
        if spelling.startswith(wanted + "["):
            return "parametrized"
        if re.search(anchored + r"\[", spelling):
            return "parametrized"
    return None


def _phase_of(case: ET.Element, node: ET.Element) -> str:
    """Which phase failed: call, or setup/teardown/collection.

    JUnit XML has no phase field. The portable derivation:

      <failure>  an assertion inside the test body        -> CALL
      <error>    an exception outside the assertion path  -> NOT_CALL

    That mapping is the convention pytest, Jest and go-junit-report all follow,
    and it is the distinction that matters: a specimen that ERRORS during setup
    never executed its assertion, so it proves nothing about its subject even
    though the run is red.

    Where a runner annotates the phase explicitly, that wins over the
    convention. When neither is available the result is PHASE_UNKNOWN -- never
    CALL, because guessing CALL is the failure mode this module refuses.
    """
    explicit = case.get("phase") or node.get("phase")
    if explicit in {CALL, "setup", "teardown"}:
        return CALL if explicit == CALL else NOT_CALL

    text = ((node.get("message") or "") + " " + (node.text or "")).lower()
    if "error at setup" in text or "error at teardown" in text:
        return NOT_CALL

    tag = node.tag.lower()
    if tag == "failure":
        return CALL
    if tag == "error":
        return NOT_CALL
    return PHASE_UNKNOWN


def read_outcome(junit_xml: str | Path, node_id: str) -> NodeOutcome:
    """What did the report say about exactly this node?

    Returns ABSENT rather than raising when the node is not in the report: a
    caller must be able to distinguish "did not fail" from "was never run",
    and an exception here would collapse both into the caller's error handler.
    """
    root = ET.parse(str(junit_xml)).getroot()
    seen: list[str] = []
    exact: ET.Element | None = None
    parametrized: list[ET.Element] = []

    for case in root.iter("testcase"):
        primary = _node_ids(case)
        seen.append(primary[0] if primary else case.get("name", "?"))
        kind = _matches(case, node_id)
        if kind == "exact" and exact is None:
            exact = case
        elif kind == "parametrized":
            parametrized.append(case)

    case = exact
    if case is None:
        if len(parametrized) > 1:
            # AMBIGUOUS, NOT RESOLVED BY PICKING ONE. A base name covering
            # several parametrizations does not identify a subject, and a
            # primitive that quietly chose the first would attribute one
            # parametrization's verdict to a question about all of them.
            ids = sorted(_node_ids(item)[-1] for item in parametrized)
            return NodeOutcome(node_id, AMBIGUOUS, PHASE_UNKNOWN, available=ids)
        if len(parametrized) == 1:
            case = parametrized[0]

    if case is None:
        return NodeOutcome(node_id, ABSENT, PHASE_UNKNOWN, available=seen)

    for child in case:
        tag = child.tag.lower()
        if tag in {"failure", "error"}:
            return NodeOutcome(
                node_id=node_id,
                outcome=FAILED if tag == "failure" else ERRORED,
                phase=_phase_of(case, child),
                message=child.get("message", "") or "",
                detail=(child.text or "").strip(),
            )
        if tag == "skipped":
            return NodeOutcome(node_id, SKIPPED, NOT_CALL, child.get("message", "") or "")
    return NodeOutcome(node_id, PASSED, CALL)


def attribute(
    junit_xml: str | Path,
    node_id: str,
    expected_property: str | None = None,
) -> tuple[bool, str]:
    """Did THIS node fail in the call phase, for the expected reason?

    `expected_property` is matched against the failure message and detail. It
    is the difference between "the test went red" and "the test went red for
    the reason claimed" -- a specimen that fails on an unrelated AttributeError
    is not evidence about its subject.

    Returns (attributed, why). `why` is always populated, including on success,
    so a caller can record what was actually observed rather than restating
    what it expected.
    """
    seen = read_outcome(junit_xml, node_id)

    if seen.outcome == AMBIGUOUS:
        ids = ", ".join(seen.available[:8])
        return False, (
            f"NODE_AMBIGUOUS: {node_id!r} is the base name of several "
            f"parametrized nodes, so it does not identify one subject. Name one "
            f"of: {ids}"
        )
    if seen.outcome == ABSENT:
        near = ", ".join(seen.available[:5]) or "none"
        return False, (
            f"NODE_ABSENT: {node_id!r} is not in the report at all. A node that "
            f"did not run cannot have refused anything. Nodes present: {near}"
        )
    if seen.outcome == SKIPPED:
        return False, f"NODE_SKIPPED: {node_id!r} was skipped ({seen.message!r}); it asserted nothing"
    if seen.outcome == PASSED:
        return False, f"NODE_PASSED: {node_id!r} passed; no refusal occurred"
    if seen.outcome == ERRORED or seen.phase != CALL:
        return False, (
            f"WRONG_PHASE: {node_id!r} produced {seen.outcome} in phase {seen.phase!r}, "
            f"not a call-phase failure. The assertion did not run. Message: {seen.message[:200]!r}"
        )

    if expected_property:
        haystack = (seen.message + " " + seen.detail).lower()
        if expected_property.lower() not in haystack:
            return False, (
                f"WRONG_PROPERTY: {node_id!r} failed in the call phase, but not for "
                f"{expected_property!r}. Observed: {seen.message[:200]!r}"
            )

    return True, (
        f"ATTRIBUTED: {node_id!r} failed in the call phase"
        + (f" for {expected_property!r}" if expected_property else "")
        + f". Message: {seen.message[:200]!r}"
    )
