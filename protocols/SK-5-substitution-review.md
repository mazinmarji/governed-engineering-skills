# SK-5 — Substitution review

**Read `../taxonomy/SUBSTITUTION.md` first. This protocol is how it is applied;
that document is what is applied.**

## Purpose

Determine, for a specific change, whether any claim it makes is established by a
cheaper artifact than the claim requires.

This is a **read-only review protocol**. It produces findings. It does not
implement, repair, or approve.

## Inputs (all required)

| Input | Why |
|-------|-----|
| Repository and exact revision under review | Binds the review; a review of "the branch" is unbound |
| The change under review (diff, PR, or issue scope) | Defines the corpus |
| The claims the change makes | The subject; if unstated, extract and echo them back before reviewing |
| The production entry points relevant to those claims | Needed for S2; without them S2 cannot be answered |

If the claims cannot be enumerated, stop and produce them first. A substitution
review with no claim list will find nothing, and will report that as a pass.

## Procedure

1. **Enumerate claims.** One sentence each, narrowed to what the code supports.
   Number them C1..Cn.
2. **For each claim, ask all seven detection questions.** Record for each:
   `applicable` / `not applicable`, and one line of evidence — a file:line, a
   command, or an observation. "Looks fine" is not evidence.
3. **Answer S2 by tracing, not reading.** Name the function the production
   caller invokes, and the function the assertion invokes. If they differ,
   that is a finding regardless of whether the behaviour matches today.
4. **Answer S3 by construction.** Build the second encoding and run the check.
   Do not reason about whether it would pass.
5. **Answer S7 explicitly.** Name the corpus the review covered and what was
   outside it. This goes in the output whether or not findings were made.
6. **Classify each finding** by the substitution kind and by whether it is
   demonstrated or suspected. A suspected substitution is a finding of lower
   confidence, not a lower severity.

## Output

    revision:            <sha>
    claims examined:     C1..Cn
    corpus:              <what was reviewed>
    outside corpus:      <what was not>
    findings:            [{id, claim, kind Sn, demonstrated|suspected, evidence}]
    claims not reducible to a mechanism: [...]

## Stop conditions

- **`CLAIMS_UNSTATED`** — the change's claims cannot be enumerated from the
  change, its issue, or its tests. Produce the claim list and stop.
- **`NO_PRODUCTION_PATH`** — a claim has no identifiable production consumer.
  This is itself a finding of kind S2; report it and stop reviewing that claim.
- **`OUT_OF_SCOPE`** — a finding concerns a property the change never claimed.
  Record it as an observation against the next version. Do not raise it as a
  defect in this change (EC-20).

## What does NOT count as a finding

- "Add more tests", without naming the substitution a specific test would close.
- Restating the acceptance criteria of the change under review.
- Style, naming, or structure with no claim consequence.
- A stronger property the change could have had but never claimed.

## The self-application rule

This protocol is subject to itself. A review that reports "no substitutions
found" without naming its corpus has committed S7 in the act of reporting, and
the review is incomplete rather than clean.
