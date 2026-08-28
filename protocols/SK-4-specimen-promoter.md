# SK-4 — Specimen promoter

## Purpose

Convert an observed escape into a permanent, collected specimen, and prove the
repair is load-bearing.

The failure this exists to prevent: *exploit found -> fix applied -> probe
discarded*. The fix survives; the knowledge does not; the sibling defect returns
under a different spelling. In the source programme this cycle, not the defects
themselves, produced fifteen review rounds.

## Trigger

A reproducible escape. **Only a reproducible escape.** If the behaviour cannot
be reproduced deterministically, classify it (see stop conditions) — do not
promote a specimen for it, and do not manufacture one to demonstrate this
protocol.

## Procedure

1. **Reproduce** the escape on the exact revision, and record the command.
2. **Name the property** the escape violates, in one sentence. If the property
   cannot be named, the specimen cannot assert anything (`PROPERTY_UNNAMED`).
3. **Generalize to the class.** Ask: what else is the same act under a different
   spelling? Promote the specimen for the *class*, and record the sibling
   encodings you considered. Repairing the instance and stopping is how a class
   survives nine separate discoveries.
4. **Write the specimen** so it fails on the unrepaired revision, in the call
   phase, at a named node.
5. **Verify collection.** Run the suite and confirm the runner *collected and
   executed* the named node. A specimen in a file the runner does not collect
   asserts nothing and reports green.
6. **Repair** the root, not the instance.
7. **Run the revert control** (`proof/revert_control.py`). The specimen must
   fail when the repair is reverted. A repair no specimen detects the absence
   of is not a repair.
8. **Keep the specimen permanently.** It is not deleted when the class stops
   recurring; that is when it starts working.

## Both directions, always

Every specimen ships with its over-reach counterpart: an input that is
*legitimate* and must continue to pass. A control with only negative cases
cannot distinguish "refuses the attack" from "refuses everything", and the
second passes the first's tests.

## Stop conditions

- **`NOT_REPRODUCIBLE`** — record the observation, do not promote.
- **`PROPERTY_UNNAMED`** — the violated property cannot be stated; classify and
  hand over.
- **`NOT_COLLECTED`** — the specimen exists but the runner does not execute it.
  This is a defect in the specimen, not in the subject.
- **`REVERT_INERT`** — reverting the repair does not fail the specimen. Either
  the specimen tests the wrong thing or the repair was never load-bearing.
  Both are findings; neither is a pass.

## What does NOT count

- A specimen written to demonstrate that this protocol was used.
- A specimen that passes on the unrepaired revision.
- A repair closed without step 7.
