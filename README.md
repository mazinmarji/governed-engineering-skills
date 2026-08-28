# governed-engineering-skills

A provider-neutral core for **proving that AI-assisted engineering did what it
claims, for the reason it claims, on the artifact it claims** — and for knowing
when to stop proving and ship.

It is not a prompt collection. It is a taxonomy, a set of non-negotiable rules,
three agent-followable protocols, and deterministic proof primitives that an
agent cannot negotiate with.

## The one idea

Every assurance defect this core was derived from reduces to a single act:
**substitution** — a cheaper artifact standing where an expensive one was
claimed. A name for a measurement. A nearby path for the production path. A
non-zero exit for a refusal. A declaration for an authority.

The central review question:

> **What cheaper proxy could be standing here in place of the property this code
> claims to establish?**

`taxonomy/SUBSTITUTION.md` gives seven kinds, each with a detection question you
can ask mechanically.

| | substitution | detection question |
|---|---|---|
| **S1** | Claim | Which line of code fails if this name is false? |
| **S2** | Path | Does the assertion route through the decisive production consumer? |
| **S3** | Representation | Give the same semantic state two encodings — does the check answer identically? |
| **S4** | Proof | What else produces this same signal? |
| **S5** | Authority | Who signed it, against which trust store, and can the subject write it? |
| **S6** | Temporal / state | Does this survive a clean checkout by a stranger? |
| **S7** | Closure | What is the corpus this ran over, and what is outside it? |

## Layout

    ENGINEERING_CONSTITUTION.md   EC-01..EC-22, frozen at 22
    taxonomy/SUBSTITUTION.md      S1-S7, plus the declaration-to-effect chain
    protocols/                    SK-4 specimen promoter
                                  SK-5 substitution review
                                  SK-6 loop escape
    proof/                        deterministic primitives; NOT negotiable
    schemas/                      pre-registration and result contracts

## The proof primitives

`proof/` is the part that does not take your word for anything.

**`failure_attribution.py`** — decides whether a *named node* failed in the
*call phase* for the *named property*, from JUnit XML. A process exit code is a
signal shared by a refusal, a crash, a timeout, a collection error and an
unrelated failure; reading it as the named subject's verdict is S4. Works with
any runner that emits JUnit.

**`revert_control.py`** — answers *is this fix load-bearing?* by reverting it on
an isolated git clone and requiring a named specimen to fail. Four admission
questions, each earned by a way the measurement lied:

1. a git-real workspace, with the executed module's origin proved inside it;
2. the specimen passes before the mutation;
3. the mutation actually changed the source;
4. the named node failed in the call phase, for the named property.

Both fail **closed**. Neither has ever scored a kill it did not make.

## How far this has been validated

    demonstrated portability to ONE codebase outside its origin, by detecting a
    material engineering problem beyond the observed ordinary development
    baseline

That is the whole claim. Specifically, it does **not** establish:

- general portability;
- portability across languages or organizations;
- independent assurance of any kind.

The validation repository is **private**, so its raw evidence is not publicly
reproducible. That is a real limit on what an outside reader can check here, and
it is stated rather than buried.

The method's own rule — EC-16, *a property claimed over a declared range is
measured across that range* — applies to this repository as much as to anything
it reviews. One validation is one point in a range.

## Using it

The protocols are written for an agent that has never seen this repository's
history. If a protocol only works because its reader already knows what it
means, that is a defect in the protocol.

    proof/  needs Python 3.10+, git, and a test runner that emits JUnit XML

Run the primitives' own tests before trusting them:

```bash
python -m pytest proof schemas -q
```

A proof library whose own controls cannot fail is the defect it exists to
detect.

## Status

Incubation. The interface is not stable, and the constitution is frozen at 22
rules deliberately — a constitution nobody finishes reading is not a control.
Extend it only on evidence of a genuinely new root principle.

## License

MIT.
