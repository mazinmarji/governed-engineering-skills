# The substitution taxonomy (S1-S7)

Every defect in the source programme reduced to one act: **a cheaper artifact
standing where an expensive one was claimed.**

That is the whole model. The seven kinds below are where the substitution
happens, not seven different phenomena.

The central review question, which subsumes all seven:

> **What cheaper proxy could be standing here in place of the property this
> code claims to establish?**

## The seven kinds

| ID | Substitution | Detection question |
|----|--------------|--------------------|
| **S1** | **Claim** — a property named, not established | Which line of code fails if this name is false? |
| **S2** | **Path** — a nearby path for the production path | Does the assertion route through the decisive production consumer? |
| **S3** | **Representation** — one spelling for the state | Give the same semantic state two encodings; does the check answer identically? |
| **S4** | **Proof** — a weaker signal for a stronger property | What else produces this same signal? |
| **S5** | **Authority** — a declaration resembling authority | Who signed it, against which trust store, and can the subject write it? |
| **S6** | **Temporal / state** — transient treated as durable | Does this survive a clean checkout by a stranger? |
| **S7** | **Closure** — "no known issue" read as "proven" | What is the corpus this ran over, and what is outside it? |

## Notes that carry weight

**S1 is the most common and the least visible.** A test named
`test_findings_cannot_be_edited_after_review` passed in the source programme
while findings could be edited. The name was doing the work the assertion was
believed to be doing. Ask the detection question against the *name*, not
against the code you expect to find.

**S2 is the one that quietly invalidates whole test suites.** A test that
recomputes the property it is checking proves the recomputation. The assertion
must reach the consumer whose decision actually gates the effect.

**S3 is answered by construction, not by inspection.** Do not reason about
whether two encodings are handled alike — build both and compare answers.

**S4 is where "green" and "non-zero exit" live.** A process exit code is a
coarse signal shared by refusal, crash, timeout, collection error and import
failure. Reading it as the named subject's verdict is S4.

**S5's most dangerous form is self-exemption**: content authorising its own
exclusion from the control that reads it. It appeared twice in the source
programme, the second time introduced *by the repair for the first*. The fix
requires a context the subject cannot author — a registry outside the subject
**and** a declaration inside it, neither sufficient alone.

**S6 is answered by `git clone` into a clean directory**, not by reasoning.
Gitignored state, machine-local caches, and stale compiled bytecode are all S6.

**S7 is the range question.** "All tests pass" is a statement about the corpus
that ran. Always name what was outside it.

## Beneath the taxonomy: the control-path chain

For any control on which authority or assurance depends, the five transitions
must each be demonstrated, not assumed:

    DECLARATION -> PROPAGATION -> CONSUMPTION -> DECISION SENSITIVITY -> EFFECT

    Is it declared?
      Does it reach the real consumer?
        Does the consumer actually consult it?
          Would changing it change the decision?
            Does that decision gate the effect?

Presence is not propagation; propagation is not consumption; consumption is not
decision sensitivity. An unverified signed field, an uncalled helper, and a
trust object nobody consults are the same defect at different steps.

## How to apply this in review

For each claim the change makes, in order:

1. State the claim in one sentence, as narrowly as the code actually supports.
2. Ask each detection question above; record `applicable` / `not applicable`
   with one line of reasoning either way.
3. Where a question cannot be answered by pointing at code, that is a finding,
   not a pass.
4. Record the claims you could NOT reduce to a mechanism. Those are the
   document's honest limits and belong in its disclosure, not in its summary.

A review that returns "no substitutions found" without naming the corpus it
examined has committed S7 in the act of reporting.
