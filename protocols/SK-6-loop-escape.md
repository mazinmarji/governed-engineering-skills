# SK-6 — Loop escape

## Purpose

Terminate a remediation loop by classification rather than by another attempt or
by quietly lowering the bar.

## Trigger — apply mechanically, not by judgement

| Condition | Action |
|-----------|--------|
| A second sibling finding of the same mechanism | Stop patching instances. Define the class and fix the root. |
| Two failed implementations of the same strategy | Change strategy materially. A third variation of the same idea is the same attempt. |
| **Three distinct failed approaches** | **Stop autonomous remediation. Classify and hand over.** |

There is no fourth attempt. The trigger counts *approaches*, not edits.

## Classifications

Exactly one, chosen honestly:

- **`UNMEASURABLE`** — the property cannot be observed with available
  instruments.
- **`INVALID_TEST_AIM`** — the test targets something other than the property.
- **`INVALID_MUTATION_ENVIRONMENT`** — the workspace cannot execute the mutant
  faithfully (wrong source imported, stale bytecode, non-git workspace).
- **`MISSING_PRODUCTION_PATH`** — no production consumer exists to assert
  through.
- **`EXTERNAL_DEPENDENCY`** — resolution requires a system outside the change.
- **`ARCHITECTURE_DECISION_REQUIRED`** — the remedy requires a design choice
  that is a human's to make.

## The rule that makes this work

> **Never downgrade severity to escape a loop.**

A finding does not become P3 because it resisted three repairs. Classify the
*approach* as failed and hand the *finding* over at its true severity. Severity
reduction under repair pressure is the single most tempting false exit, and it
converts an open defect into a closed record with no change in the code.

## Output

    trigger:         <which row above fired>
    approaches:      [{n, strategy, why it failed}]
    classification:  <one of the six>
    finding severity: <unchanged from before the loop>
    handover:        <what a human or a different agent needs to decide>

## What does NOT count as an escape

- Declaring the finding out of scope after failing to fix it.
- Narrowing the claim so the finding no longer applies, *unless* the narrowed
  claim is what the code actually supports and the narrowing is recorded as a
  disclosed limitation.
- A fourth attempt described as "a different approach" that shares the failed
  mechanism of the first three.
