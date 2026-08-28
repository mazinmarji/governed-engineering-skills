"""The proof primitives, measured rather than asserted.

A proof library whose own controls cannot fail is the defect it exists to
detect. Every test here fails if its primitive stops working -- verified by
reverting each primitive during development, not by inspection.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from failure_attribution import (
    attribute, read_outcome,
    ABSENT, AMBIGUOUS, ERRORED, FAILED, PASSED, SKIPPED,
)
from revert_control import (
    BASELINE_NOT_GREEN,
    FIX_LOAD_BEARING,
    INVALID_WORKSPACE,
    MUTATION_INERT,
    REVERT_INERT,
    python_origin_probe,
    verify_revert,
)

NL = chr(10)


def _junit(tmp_path: Path, body: str) -> Path:
    report = tmp_path / "report.xml"
    report.write_text(
        '<?xml version="1.0" encoding="utf-8"?>' + NL
        + '<testsuites><testsuite name="pytest" tests="1">' + body + "</testsuite></testsuites>",
        encoding="utf-8",
    )
    return report


# --------------------------------------------------------------------------
# failure_attribution: every outcome must be distinguishable from every other
# --------------------------------------------------------------------------

def test_an_absent_node_is_not_a_passing_node(tmp_path: Path):
    """The distinction that a raw exit code destroys.

    A specimen deleted, renamed, or never collected produces the same green
    run as a specimen that passed. Collapsing the two is how a suite stays
    green over a control that no longer exists.
    """
    report = _junit(tmp_path, '<testcase classname="tests.test_other" name="test_unrelated"/>')

    seen = read_outcome(report, "test_missing")
    assert seen.outcome == ABSENT, "an absent node was not reported as absent"
    assert any("test_unrelated" in spelling for spelling in seen.available), (
        "the report's actual contents were not returned, so a caller cannot tell "
        f"an absent node from a misspelled one; got {seen.available}"
    )

    ok, why = attribute(report, "test_missing")
    assert not ok and "NODE_ABSENT" in why, why


def test_a_setup_error_is_not_a_call_phase_refusal(tmp_path: Path):
    """A red run whose assertion never executed proves nothing about its subject."""
    report = _junit(
        tmp_path,
        '<testcase classname="tests.test_x" name="test_guard">'
        '<error message="fixture not found">error at setup</error></testcase>',
    )
    seen = read_outcome(report, "test_guard")
    assert seen.outcome == ERRORED, seen

    ok, why = attribute(report, "test_guard")
    assert not ok and "WRONG_PHASE" in why, (
        "a setup error was accepted as a call-phase refusal, which is exactly the "
        "coarse-signal substitution this module exists to refuse: " + why
    )


def test_a_skip_is_not_a_pass_and_not_a_failure(tmp_path: Path):
    report = _junit(
        tmp_path,
        '<testcase classname="tests.test_x" name="test_guard">'
        '<skipped message="needs network"/></testcase>',
    )
    assert read_outcome(report, "test_guard").outcome == SKIPPED
    ok, why = attribute(report, "test_guard")
    assert not ok and "NODE_SKIPPED" in why, why


def test_the_right_node_failing_for_the_wrong_reason_is_not_attributed(tmp_path: Path):
    """Red is not proof. Red FOR THE NAMED PROPERTY is proof."""
    report = _junit(
        tmp_path,
        '<testcase classname="tests.test_x" name="test_guard">'
        '<failure message="AttributeError: NoneType has no attribute foo">boom</failure>'
        "</testcase>",
    )
    ok, why = attribute(report, "test_guard", expected_property="REVISION_MISMATCH")
    assert not ok and "WRONG_PROPERTY" in why, (
        "a specimen that went red on an unrelated crash was credited as evidence "
        "about its subject: " + why
    )

    ok, why = attribute(report, "test_guard")
    assert ok, "with no expected property, a call-phase failure should attribute: " + why


def test_a_genuine_call_phase_failure_for_the_named_property_attributes(tmp_path: Path):
    report = _junit(
        tmp_path,
        '<testcase classname="tests.test_x" name="test_guard">'
        '<failure message="AssertionError: REVISION_MISMATCH was not refused">x</failure>'
        "</testcase>",
    )
    ok, why = attribute(report, "test_guard", expected_property="REVISION_MISMATCH")
    assert ok, why
    assert read_outcome(report, "test_guard").failed_in_call


def test_node_matching_does_not_bleed_between_similarly_named_nodes(tmp_path: Path):
    """`test_guard` must not match `test_guard_variant`.

    Loose suffix matching would attribute one node's failure to another -- a
    substitution of subject, and the most dangerous kind because the report
    reads correct.
    """
    report = _junit(
        tmp_path,
        '<testcase classname="tests.test_x" name="test_guard_variant">'
        '<failure message="AssertionError: unrelated">x</failure></testcase>',
    )
    assert read_outcome(report, "test_guard").outcome == ABSENT, (
        "a failure in test_guard_variant was attributed to test_guard"
    )
    # ...while the legitimate suffix form still resolves.
    assert read_outcome(report, "test_x.py::test_guard_variant").outcome == FAILED


# --------------------------------------------------------------------------
# revert_control: end to end on a real git repository
# --------------------------------------------------------------------------

GUARDED = '''
def admit(revision, expected):
    """The fix under test: refuse a mismatched revision."""
    if revision != expected:
        raise ValueError("REVISION_MISMATCH")
    return True
'''

UNGUARDED = '''
def admit(revision, expected):
    """The fix reverted: admits anything."""
    return True
'''

SPECIMEN = '''
import pytest
from widget import admit


def test_guard_refuses_a_mismatched_revision():
    with pytest.raises(ValueError, match="REVISION_MISMATCH"):
        admit("aaa", "bbb")


def test_guard_admits_a_matching_revision():
    assert admit("aaa", "aaa") is True
'''


def _repo(tmp_path: Path, widget: str, specimen: str) -> Path:
    repo = tmp_path / "subject"
    repo.mkdir()
    (repo / "widget.py").write_text(textwrap.dedent(widget).strip() + NL, encoding="utf-8")
    (repo / "test_specimen.py").write_text(textwrap.dedent(specimen).strip() + NL, encoding="utf-8")
    for cmd in (
        ["git", "init", "--quiet"],
        ["git", "config", "user.email", "trial@example.invalid"],
        ["git", "config", "user.name", "trial"],
        ["git", "add", "-A"],
        ["git", "commit", "--quiet", "-m", "baseline"],
    ):
        proc = subprocess.run(cmd, cwd=str(repo), capture_output=True, text=True)
        assert proc.returncode == 0, cmd + [proc.stderr]
    return repo


TEST_CMD = f'"{sys.executable}" -m pytest -q --junit-xml=report.xml'


@pytest.mark.skipif(not shutil.which("git"), reason="git is required for revert controls")
def test_a_load_bearing_fix_is_proven_by_reverting_it(tmp_path: Path):
    """The positive case: remove the guard, the specimen must go red."""
    repo = _repo(tmp_path, GUARDED, SPECIMEN)

    def revert(workspace: Path) -> None:
        (workspace / "widget.py").write_text(textwrap.dedent(UNGUARDED).strip() + NL, encoding="utf-8")

    result = verify_revert(
        repo,
        specimen_node="test_guard_refuses_a_mismatched_revision",
        test_command=TEST_CMD,
        junit_path="report.xml",
        mutate=revert,
        expected_property="REVISION_MISMATCH",
    )
    assert result.verdict == FIX_LOAD_BEARING, result.why + NL + NL.join(result.steps)


@pytest.mark.skipif(not shutil.which("git"), reason="git is required for revert controls")
def test_a_mutation_that_changes_nothing_is_refused_not_credited(tmp_path: Path):
    """Question 3. A no-op revert must never score a kill.

    This is the failure that silently inflates a mutation campaign: a
    `replace()` whose pattern matched nothing returns successfully, the suite
    is re-run, something else is red, and the tool records a kill.
    """
    repo = _repo(tmp_path, GUARDED, SPECIMEN)

    def noop(workspace: Path) -> None:
        return None

    result = verify_revert(
        repo,
        specimen_node="test_guard_refuses_a_mismatched_revision",
        test_command=TEST_CMD,
        junit_path="report.xml",
        mutate=noop,
        expected_property="REVISION_MISMATCH",
    )
    assert result.verdict == MUTATION_INERT, result.why


@pytest.mark.skipif(not shutil.which("git"), reason="git is required for revert controls")
def test_a_specimen_that_does_not_detect_the_revert_is_reported_inert(tmp_path: Path):
    """The finding the source programme kept missing.

    Here the specimen asserts something true of BOTH the guarded and unguarded
    widget. Reverting the fix leaves it green, so the fix is not load-bearing
    with respect to this specimen -- and that must be reported, not passed.
    """
    weak = '''
        from widget import admit


        def test_guard_admits_a_matching_revision():
            assert admit("aaa", "aaa") is True
    '''
    repo = _repo(tmp_path, GUARDED, weak)

    def revert(workspace: Path) -> None:
        (workspace / "widget.py").write_text(textwrap.dedent(UNGUARDED).strip() + NL, encoding="utf-8")

    result = verify_revert(
        repo,
        specimen_node="test_guard_admits_a_matching_revision",
        test_command=TEST_CMD,
        junit_path="report.xml",
        mutate=revert,
    )
    assert result.verdict == REVERT_INERT, (
        "a fix whose removal no specimen detected was reported as proven: " + result.why
    )


@pytest.mark.skipif(not shutil.which("git"), reason="git is required for revert controls")
def test_a_failing_baseline_is_refused_before_any_mutation(tmp_path: Path):
    """Question 2. A specimen already red proves nothing about the revert."""
    broken = SPECIMEN.replace('admit("aaa", "aaa") is True', 'admit("aaa", "aaa") is False')
    repo = _repo(tmp_path, GUARDED, broken)

    def revert(workspace: Path) -> None:
        (workspace / "widget.py").write_text(textwrap.dedent(UNGUARDED).strip() + NL, encoding="utf-8")

    result = verify_revert(
        repo,
        specimen_node="test_guard_admits_a_matching_revision",
        test_command=TEST_CMD,
        junit_path="report.xml",
        mutate=revert,
    )
    assert result.verdict == BASELINE_NOT_GREEN, result.why


# --------------------------------------------------------------------------
# M1: a parametrized specimen must be addressable, and ambiguity must be named
# --------------------------------------------------------------------------

def test_a_base_name_reaches_its_single_parametrization(tmp_path: Path):
    """The measured failure that produced this fix.

    A revert control named a specimen by its base name and was told the node was
    ABSENT, surfaced as BASELINE_NOT_GREEN, because the JUnit id carries a
    `[parameter]` suffix. Safe direction, misleading diagnostic.
    """
    report = _junit(
        tmp_path,
        '<testcase classname="tests.test_x" name="test_projection_is_closed[case_a]">'
        '<failure message="AssertionError: the projection grew a key">x</failure></testcase>',
    )
    seen = read_outcome(report, "test_projection_is_closed")
    assert seen.outcome == FAILED, f"the base name did not reach its parametrization: {seen}"
    assert seen.failed_in_call

    ok, why = attribute(report, "test_projection_is_closed", expected_property="grew a key")
    assert ok, why


def test_a_base_name_covering_several_parametrizations_is_refused_not_guessed(tmp_path: Path):
    """Ambiguity is not resolved by picking the first.

    A base name naming five parametrizations does not identify a subject. A
    primitive that quietly chose one would answer a question about all of them
    with one of their verdicts -- substituting a part for the whole.
    """
    report = _junit(
        tmp_path,
        '<testcase classname="tests.test_x" name="test_sweep[a]"/>'
        '<testcase classname="tests.test_x" name="test_sweep[b]">'
        '<failure message="AssertionError: b failed">x</failure></testcase>',
    )
    seen = read_outcome(report, "test_sweep")
    assert seen.outcome == AMBIGUOUS, f"an ambiguous base name was resolved anyway: {seen}"
    assert any("test_sweep[a]" in s for s in seen.available), seen.available
    assert any("test_sweep[b]" in s for s in seen.available), seen.available

    ok, why = attribute(report, "test_sweep")
    assert not ok and "NODE_AMBIGUOUS" in why, why
    assert "test_sweep[b]" in why, "the diagnostic must NAME the candidates, not just refuse"

    # ...and naming one exactly still works.
    ok, why = attribute(report, "test_sweep[b]", expected_property="b failed")
    assert ok, why


def test_parametrized_matching_did_not_reopen_the_name_bleed(tmp_path: Path):
    """The anti-bleed property must survive the new `[` boundary."""
    report = _junit(
        tmp_path,
        '<testcase classname="tests.test_x" name="test_guard_variant[a]">'
        '<failure message="AssertionError: unrelated">x</failure></testcase>',
    )
    assert read_outcome(report, "test_guard").outcome == ABSENT, (
        "test_guard matched test_guard_variant[a]; the base-name fix reopened "
        "the exact bleed the anchor existed to refuse"
    )


# --------------------------------------------------------------------------
# M3: the origin probe that did not ship
# --------------------------------------------------------------------------

@pytest.mark.skipif(not shutil.which("git"), reason="git is required for revert controls")
def test_the_origin_probe_proves_the_executed_module_came_from_the_mutant_tree(tmp_path: Path):
    """Admission question 1, strict form -- previously always NOT PROVED."""
    repo = _repo(tmp_path, GUARDED, SPECIMEN)

    def revert(workspace: Path) -> None:
        (workspace / "widget.py").write_text(textwrap.dedent(UNGUARDED).strip() + NL, encoding="utf-8")

    result = verify_revert(
        repo,
        specimen_node="test_guard_refuses_a_mismatched_revision",
        test_command=TEST_CMD,
        junit_path="report.xml",
        mutate=revert,
        expected_property="REVISION_MISMATCH",
        origin_probe=python_origin_probe("widget", sys.executable),
    )
    assert result.verdict == FIX_LOAD_BEARING, result.why + NL + NL.join(result.steps)
    assert result.isolation == "clone+origin-proved", (
        "the control passed but did not record the strict isolation claim: " + result.isolation
    )
    assert any("origin proved" in step for step in result.steps), result.steps


@pytest.mark.skipif(not shutil.which("git"), reason="git is required for revert controls")
def test_an_origin_probe_pointing_outside_the_workspace_refuses(tmp_path: Path):
    """The probe must be able to FAIL, or it is decoration.

    `json` is importable everywhere and never lives in the mutant tree, so a
    probe naming it must be refused rather than accepted as proof of origin.
    """
    repo = _repo(tmp_path, GUARDED, SPECIMEN)

    result = verify_revert(
        repo,
        specimen_node="test_guard_refuses_a_mismatched_revision",
        test_command=TEST_CMD,
        junit_path="report.xml",
        mutate=lambda w: None,
        origin_probe=python_origin_probe("json", sys.executable),
    )
    assert result.verdict == INVALID_WORKSPACE, (
        "a module loaded from outside the mutant tree was accepted as proof "
        "that the mutant tree was executed: " + result.why
    )
    assert "ORIGIN_PROBE_FAILED" in result.why, result.why


@pytest.mark.skipif(not shutil.which("git"), reason="git is required for revert controls")
def test_a_specimen_in_an_uncommitted_new_file_reaches_the_mutant_tree(tmp_path: Path):
    """M4, measured: `git diff HEAD` describes TRACKED changes only.

    A specimen written into a new, not-yet-committed file was silently absent
    from the isolated workspace, and the control reported BASELINE_NOT_GREEN
    ... is absent. Fail-closed, so no kill was ever scored falsely -- but the
    caller was told their specimen did not exist when it did, which is the same
    misleading diagnostic M1 was about, one layer down.
    """
    repo = _repo(tmp_path, GUARDED, SPECIMEN)

    # A NEW file, deliberately never committed.
    (repo / "test_new_specimen.py").write_text(
        "from widget import admit" + NL + NL + NL
        + "def test_guard_still_refuses():" + NL
        + "    try:" + NL
        + "        admit('aaa', 'bbb')" + NL
        + "    except ValueError:" + NL
        + "        return" + NL
        + "    raise AssertionError('REVISION_MISMATCH was not refused')" + NL,
        encoding="utf-8",
    )

    def revert(workspace: Path) -> None:
        (workspace / "widget.py").write_text(
            textwrap.dedent(UNGUARDED).strip() + NL, encoding="utf-8"
        )

    result = verify_revert(
        repo,
        specimen_node="test_guard_still_refuses",
        test_command=TEST_CMD,
        junit_path="report.xml",
        mutate=revert,
        expected_property="REVISION_MISMATCH",
    )
    assert result.verdict == FIX_LOAD_BEARING, (
        "a specimen in an uncommitted new file did not reach the mutant tree: "
        + result.why
    )
    assert "untracked" in result.isolation, (
        "the untracked carry is not recorded in the isolation claim: " + result.isolation
    )


# --------------------------------------------------------------------------
# M5: uncommitted work must reach the mutant tree without patching
# --------------------------------------------------------------------------

@pytest.mark.skipif(not shutil.which("git"), reason="git is required for revert controls")
def test_uncommitted_modifications_reach_the_mutant_tree(tmp_path: Path):
    """M5, measured: `git diff HEAD` + `git apply` fails under CRLF normalization.

    With `core.autocrlf` the working tree and index disagree about line endings,
    the generated patch does not apply to a fresh clone, and every control
    returns INVALID_WORKSPACE. Fail-closed, so no kill was ever scored falsely,
    but the control produced no result at all.

    Here the fix is committed but the SPECIMEN is modified in the working tree
    only, so the run depends on that uncommitted modification arriving.
    """
    repo = _repo(tmp_path, GUARDED, SPECIMEN)
    subprocess.run(["git", "config", "core.autocrlf", "true"], cwd=str(repo), capture_output=True)

    # Uncommitted: rename the specimen so only the working-tree copy has it.
    specimen = repo / "test_specimen.py"
    specimen.write_text(
        specimen.read_text(encoding="utf-8").replace(
            "def test_guard_refuses_a_mismatched_revision():",
            "def test_guard_refuses_it_uncommitted():",
        ),
        encoding="utf-8",
    )

    def revert(workspace: Path) -> None:
        (workspace / "widget.py").write_text(
            textwrap.dedent(UNGUARDED).strip() + NL, encoding="utf-8"
        )

    result = verify_revert(
        repo,
        specimen_node="test_guard_refuses_it_uncommitted",
        test_command=TEST_CMD,
        junit_path="report.xml",
        mutate=revert,
        expected_property="REVISION_MISMATCH",
    )
    assert result.verdict == FIX_LOAD_BEARING, (
        "an uncommitted modification did not reach the mutant tree: " + result.why
    )
    assert "modified" in result.isolation, result.isolation


@pytest.mark.skipif(not shutil.which("git"), reason="git is required for revert controls")
def test_an_uncommitted_deletion_is_carried_too(tmp_path: Path):
    """A file deleted in the working tree must not reappear in the clone.

    Cloning restores it from the commit, so a deletion that is not carried gives
    the mutant a file the subject no longer has.
    """
    repo = _repo(tmp_path, GUARDED, SPECIMEN)
    extra = repo / "stale_helper.py"
    extra.write_text("VALUE = 1" + NL, encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=str(repo), capture_output=True)
    subprocess.run(["git", "commit", "--quiet", "-m", "add helper"], cwd=str(repo), capture_output=True)
    extra.unlink()  # uncommitted deletion

    seen: dict[str, bool] = {}

    def check(workspace: Path) -> None:
        seen["present"] = (workspace / "stale_helper.py").exists()
        (workspace / "widget.py").write_text(
            textwrap.dedent(UNGUARDED).strip() + NL, encoding="utf-8"
        )

    verify_revert(
        repo,
        specimen_node="test_guard_refuses_a_mismatched_revision",
        test_command=TEST_CMD,
        junit_path="report.xml",
        mutate=check,
    )
    assert seen.get("present") is False, (
        "a file deleted in the working tree reappeared in the mutant clone"
    )


# --------------------------------------------------------------------------
# M6: the origin probe must work where the package is not at the repo root
# --------------------------------------------------------------------------

def test_the_origin_probe_can_run_from_a_subdirectory():
    """M6: repositories that root their package in a subdirectory.

    The first version assumed repo-root importability, so callers had to
    hand-write the `cd` -- friction that gets skipped, and skipping it means
    falling back to the weaker isolation claim.
    """
    plain = python_origin_probe("widget", "py")
    assert plain.startswith('"py" -c'), plain
    assert "cd " not in plain

    scoped = python_origin_probe("myapp.domain.ranking", "py", cwd="packages/core")
    assert scoped.startswith("cd packages/core && "), scoped
    assert "myapp.domain.ranking" in scoped
