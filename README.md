# ReuseGate

A standalone GenLayer Intelligent Contract that decides whether one registered work is a
derivative reuse of another, and exposes that finding as a gate a paying contract can read
before it releases value.

**Status:** deployed on GenLayer Studionet (chain `61999`) at
`0x756DD19B75ce173B8EbdA79F9df93ac983Dd5EFd`. Four transactions are finalized and
successfully executed: deployment, two registrations, and one full-consensus assessment
that returned `DERIVATIVE` with 3 of 5 validators agreeing. GenVM lint, semantic
validation and type checking pass, and **16 Direct Mode tests** pass with the model mocked.
Local tests are not distributed-network results; the live receipts are linked below.

## The problem

A prize or grant pool can only be withheld from a plagiarised entry if the reuse finding
itself is neutral. In practice that finding is made by an organiser reading two
submissions by hand, which means the organiser can always justify keeping the pool.
ReuseGate puts a closed-vocabulary finding on chain next to a deterministic overlap
measurement, so withholding an award requires a consensus result rather than an opinion.

## Why this needs GenLayer

No deterministic chain can read two documents and decide that one is an edited version of
the other. That judgment is language, and language needs validators that can interpret it
and still agree. GenLayer supplies exactly that: a leader proposes a finding, the validator
committee re-runs the same judgment independently, and only an accepted finding is written
to state.

The contract also shows the boundary of that power. A hash or a diff can prove that text
was copied. Nothing in code can prove that text was *not* copied, because a paraphrase
rewrites every word. ReuseGate therefore never treats "no overlap" as proof of
independence, and that decision is the core of the design.

## How the decision is made

The order is deliberate: cheap and exact first, expensive and interpretive second.
