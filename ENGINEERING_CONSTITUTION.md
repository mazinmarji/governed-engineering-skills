# Engineering constitution

Twenty-two rules. Each was earned by a specific defect in the source programme;
none is aspirational. They are frozen at 22 — do not extend this list except on
evidence of a genuinely new root principle, because a constitution nobody
finishes reading is not a control.

## Measurement

- **EC-01** — A gate may claim only the exact property it mechanically measures.
  Names, labels, comments, counts, non-zero exits and green aggregates are not
  semantics.
- **EC-02** — A reproducible escape stays open until it is a permanent,
  collected specimen. A finding that lives only in a review note or commit
  message is not closed.
- **EC-03** — A fix is not closed until reverting that fix makes the named
  specimen fail. One fix at a time, measured — not argued.
- **EC-04** — A test must prove the intended refusal mechanism, not a non-zero
  exit. Attribute the failure to the named node, in the call phase.
- **EC-05** — Assert through the production consumer, never a reimplementation
  of it. A test that recomputes the property proves the recomputation.

## Decidability

- **EC-06** — Decide the property, not the spelling. If two encodings of one
  state get two answers, the rule is a naming convention.
- **EC-07** — Where a target cannot be resolved statically, refuse the construct
  rather than guess. Refusal is decidable; resolution of arbitrary expressions
  is not.
- **EC-08** — Discovery and inspection share one implementation, or a test
  proves they agree. Two analyses of one question drift, and the weaker one
  simply passes.
- **EC-09** — A gate reports; it does not raise where it is relied on to report.
  A failure to record becomes part of the returned decision.

## Authority

- **EC-10** — Independent assurance requires independently authenticated
  identity. Derived from signatures against an out-of-tree store — never read
  from the artifact.
- **EC-11** — An AI builder may not create authority over its own output. No
  approval, attestation, or inspection may be created, adopted, inferred, or
  backdated.
- **EC-12** — Content may not authorise its own exemption from a control that
  reads it. Exemption requires a context the subject cannot author.
- **EC-13** — Presence is not propagation; propagation is not consumption;
  consumption is not decision sensitivity. Demonstrate each transition where
  authority depends on it.

## Durability

- **EC-14** — Evidence is revision-bound; regenerate it in the same commit as
  the governed change. Integration produces a new artifact requiring new
  binding.
- **EC-15** — Authority must survive a clean checkout by a stranger. Gitignored,
  machine-local, or session state is never authority.

## Range

- **EC-16** — A property claimed over a declared range is measured across that
  range. Otherwise the claim narrows to the point actually measured.
- **EC-17** — A cancelled or unrun job proves nothing about its subject. The
  environment must be able to answer the question the test asks.

## Disclosure

- **EC-18** — Prefer deleting a number in prose to correcting it. A quantity
  beside a live value that nothing parses will rot.
- **EC-19** — Documents are scanned by the guards they describe, and state the
  narrow claim last. The reader who stops at the closing sentence must not be
  misled.

## Termination

- **EC-20** — A release review may attack a frozen contract; it may not silently
  redefine it. A finding about the contract is filed against the next version.
- **EC-21** — Never downgrade severity to escape a loop; classify instead. Three
  failed approaches means classify and hand over, not attempt four.
- **EC-22** — Do not proceed past a gate you have read as failing. A process
  that reports a failure and commits anyway is a control that cannot fail.
