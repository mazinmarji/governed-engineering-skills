"""Prove a fix is load-bearing by reverting it and requiring a named specimen to fail.

THE DEFECT THIS EXISTS TO PREVENT
---------------------------------
A fix that makes the suite green is not necessarily a fix. In the source
programme, replacing a repaired function body with `return True` left every
control green: the suite proved the ABSENCE OF THE OLD SYMPTOM, not the
presence of the new control.

    A fix is not closed until reverting it makes a named specimen fail.

FOUR ADMISSION QUESTIONS
------------------------
A revert control that answers "the specimen failed" proves nothing unless all
four hold. Each was earned by a way the measurement lied:

  1. GIT-REAL WORKSPACE   -- the mutation is applied to an isolated checkout,
                             and the test run imports THAT source. A test that
                             imports the original package measures the original.
  2. PRISTINE GREEN       -- the specimen passes before the mutation. A specimen
                             already failing proves nothing about the revert.
  3. DISTINCT MUTATION    -- the revert actually changed the source. A no-op
                             `replace()` that matched nothing succeeds silently
                             and scores a kill it never made.
  4. CALL-PHASE FAILURE   -- the named node failed in the call phase, for the
                             named property. Not a non-zero exit; not a setup
                             error; not a different node.

PORTABILITY
-----------
Language-agnostic in structure: it needs git, a test command, and a JUnit
report. Question 1's *strict* form (proving the executed module was loaded from
the mutant tree) is Python-specific and is applied when a module origin probe
is supplied; otherwise the workspace isolation is verified structurally and the
result records which form was used. It does not silently claim the stronger one.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from failure_attribution import attribute, read_outcome, PASSED

# Verdicts. Only the first is a pass.
FIX_LOAD_BEARING = "FIX_LOAD_BEARING"
REVERT_INERT = "REVERT_INERT"
BASELINE_NOT_GREEN = "BASELINE_NOT_GREEN"
MUTATION_INERT = "MUTATION_INERT"
INVALID_WORKSPACE = "INVALID_WORKSPACE"


@dataclass
class RevertResult:
    verdict: str
    why: str
    workspace: str = ""
    isolation: str = ""
    steps: list[str] = field(default_factory=list)

    @property
    def proven(self) -> bool:
        return self.verdict == FIX_LOAD_BEARING


def python_origin_probe(module: str, interpreter: str = "python", cwd: str | None = None) -> str:
    """A ready-made `origin_probe` for Python.

    Answers admission question 1 in its STRICT form: that the code the test run
    executed was loaded from the mutant tree, not from an installed copy or the
    authoritative source that happens to be importable.

    Supplied because its absence was a measured gap: every control in the first
    trial reported ``Q1 strict: NOT PROVED``, so isolation rested on the clone
    being structurally separate rather than on the executed module's origin. The
    primitive was honest about the downgrade, but nobody could close it without
    writing this by hand.

    ``cwd`` is the directory the probe runs in, RELATIVE TO THE WORKSPACE ROOT.
    It exists because the first version assumed the package was importable from
    the repository root, which is false for any repository that roots its
    package in a subdirectory, as monorepos commonly do. That
    forced callers to hand-write the ``cd``, which is the kind of small friction
    that gets skipped, and skipping it means falling back to the weaker
    isolation claim.

    Pass the result as `origin_probe=`. It prints the module's `__file__`, which
    `verify_revert` requires to sit under the workspace.

    Inner quoting is single, so the whole command survives one level of shell
    quoting on both cmd.exe and POSIX shells.
    """
    probe = f'"{interpreter}" -c "import importlib;print(importlib.import_module(\'{module}\').__file__)"'
    return f"cd {cwd} && {probe}" if cwd else probe


def _run(cmd: list[str] | str, cwd: Path, timeout: int = 900) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        cwd=str(cwd),
        shell=isinstance(cmd, str),
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _isolated_checkout(repo: Path, into: Path) -> tuple[Path, str]:
    """A git-real copy of `repo` at its current revision.

    `git clone` rather than a file copy, because the mutation must be applied
    to a tree with real VCS identity: a copied directory cannot answer "is this
    modified relative to its baseline?", and that question is question 3.
    """
    target = into / "mutant"
    proc = _run(["git", "clone", "--quiet", "--no-hardlinks", str(repo), str(target)], into)
    if proc.returncode != 0:
        raise RuntimeError(f"clone failed: {proc.stderr.strip()[:300]}")

    # Carry uncommitted work across: the fix under test is frequently not yet
    # committed, and cloning alone would silently test the tree WITHOUT it --
    # which reads as REVERT_INERT for a fix that was never present.
    #
    # COPIED, NOT PATCHED. This used `git diff HEAD` piped into `git apply`, and
    # on Windows that fails outright: with `core.autocrlf` the working tree and
    # the index disagree about line endings, the generated patch does not apply
    # to a fresh clone, and every control returns INVALID_WORKSPACE. Measured on
    # a real repository -- four controls blocked, no false kill, but no result
    # either. Copying the file contents has no such failure mode, and it is what
    # the untracked path below already did.
    carried = []
    changed = _run(["git", "diff", "--name-status", "HEAD"], repo)
    modified = deleted = 0
    for line in changed.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        status, name = parts[0].strip(), parts[-1].strip()
        destination = target / name
        if status.startswith("D"):
            if destination.exists():
                destination.unlink()
                deleted += 1
            continue
        source = repo / name
        if not source.is_file():
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        modified += 1
    if modified:
        carried.append(f"{modified} modified")
    if deleted:
        carried.append(f"{deleted} deleted")

    # UNTRACKED FILES TOO. `git diff HEAD` describes tracked changes only, so a
    # specimen living in a NEW file was silently absent from the mutant tree.
    # Measured: a control naming a specimen in an uncommitted new file returned
    # BASELINE_NOT_GREEN ... is absent -- fail-closed, so no false kill, but the
    # caller was told their specimen did not exist when it did. Ignored files
    # are excluded, so build output and virtualenvs do not travel.
    untracked = _run(["git", "ls-files", "--others", "--exclude-standard"], repo)
    names = [line.strip() for line in untracked.stdout.splitlines() if line.strip()]
    for name in names:
        source = repo / name
        if not source.is_file():
            continue
        destination = target / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    if names:
        carried.append(f"{len(names)} untracked")

    return target, "clone" + ("+" + "+".join(carried) if carried else "")


def _tree_digest(repo: Path) -> str:
    """What git thinks the working tree is. Changes iff the source changed."""
    _run(["git", "add", "-A"], repo)
    proc = _run(["git", "write-tree"], repo)
    return proc.stdout.strip()


def verify_revert(
    repo: str | Path,
    specimen_node: str,
    test_command: str,
    junit_path: str,
    mutate: "callable[[Path], None]",
    expected_property: str | None = None,
    origin_probe: str | None = None,
) -> RevertResult:
    """Run the four admission questions and return a verdict.

    `mutate` receives the isolated workspace root and must revert the fix in it.
    It is a callable rather than a patch string so a caller can express the
    revert in whatever way is honest for the language at hand.

    `origin_probe` is an optional shell command run inside the workspace whose
    stdout must contain the workspace path -- the strict form of question 1,
    proving the executed code was loaded from the mutant tree. Supply it where
    the language can answer it; its absence downgrades the recorded isolation
    claim rather than being silently ignored.
    """
    repo = Path(repo).resolve()
    steps: list[str] = []
    holding = Path(tempfile.mkdtemp(prefix="revert-control-"))

    try:
        # ---- Q1: a git-real, isolated workspace ---------------------------
        try:
            workspace, isolation = _isolated_checkout(repo, holding)
        except RuntimeError as exc:
            return RevertResult(INVALID_WORKSPACE, str(exc), steps=steps)
        steps.append(f"Q1 workspace: {workspace} ({isolation})")

        if origin_probe:
            probe = _run(origin_probe, workspace)
            if str(workspace) not in probe.stdout:
                return RevertResult(
                    INVALID_WORKSPACE,
                    "ORIGIN_PROBE_FAILED: the executed code was not loaded from the "
                    f"mutant tree. Probe returned {probe.stdout.strip()[:200]!r}; "
                    f"expected a path under {workspace}. A test importing the original "
                    "source measures the original source.",
                    str(workspace), isolation, steps,
                )
            isolation = "clone+origin-proved"
            steps.append("Q1 strict: module origin proved inside the mutant tree")
        else:
            steps.append("Q1 strict: NOT PROVED (no origin probe supplied)")

        # ---- Q2: pristine baseline is green -------------------------------
        _run(test_command, workspace)
        report = workspace / junit_path
        if not report.exists():
            return RevertResult(
                INVALID_WORKSPACE,
                f"NO_REPORT: the test command produced no JUnit report at {junit_path}. "
                "Nothing can be attributed without one.",
                str(workspace), isolation, steps,
            )
        baseline = read_outcome(report, specimen_node)
        if baseline.outcome != PASSED:
            return RevertResult(
                BASELINE_NOT_GREEN,
                f"BASELINE_NOT_GREEN: {specimen_node!r} is {baseline.outcome} before any "
                f"mutation ({baseline.message[:160]!r}). A specimen that is not passing "
                "cannot demonstrate that reverting the fix broke it.",
                str(workspace), isolation, steps,
            )
        steps.append(f"Q2 pristine: {specimen_node} passed")
        before = _tree_digest(workspace)

        # ---- Q3: the mutation actually changed the source -----------------
        mutate(workspace)
        after = _tree_digest(workspace)
        if before == after:
            return RevertResult(
                MUTATION_INERT,
                "MUTATION_INERT: the revert changed nothing -- the working tree is "
                f"byte-identical ({before[:12]}). A no-op replacement succeeds silently "
                "and would otherwise score a kill it never made.",
                str(workspace), isolation, steps,
            )
        steps.append(f"Q3 mutation: tree {before[:12]} -> {after[:12]}")

        # ---- Q4: the named node failed in the call phase ------------------
        report.unlink(missing_ok=True)
        _run(test_command, workspace)
        if not report.exists():
            return RevertResult(
                INVALID_WORKSPACE,
                "NO_REPORT after mutation: the run produced no JUnit report. A mutant "
                "that cannot be collected proves nothing; this is not a kill.",
                str(workspace), isolation, steps,
            )
        ok, why = attribute(report, specimen_node, expected_property)
        steps.append(f"Q4 attribution: {why}")

        if not ok:
            return RevertResult(
                REVERT_INERT,
                f"REVERT_INERT: the fix was reverted and {specimen_node!r} did not fail "
                f"for its property. {why} Either the specimen tests something other than "
                "the fix, or the fix was never load-bearing. Both are findings.",
                str(workspace), isolation, steps,
            )

        return RevertResult(
            FIX_LOAD_BEARING,
            f"FIX_LOAD_BEARING: reverting the fix made {specimen_node!r} fail in the call "
            f"phase. {why}",
            str(workspace), isolation, steps,
        )
    finally:
        shutil.rmtree(holding, ignore_errors=True)
