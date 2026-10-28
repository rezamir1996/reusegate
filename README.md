# ReuseGate

A standalone GenLayer Intelligent Contract that decides whether one registered work is a
derivative reuse of another, and exposes that finding as a gate a paying contract can read
before it releases value.

**Status:** deployed on GenLayer Studionet (chain `61999`) at
`0x756DD19B75ce173B8EbdA79F9df93ac983Dd5EFd`. Four transactions are finalized and
successfully executed: deployment, two registrations, and one full-consensus assessment
that returned `DERIVATIVE` with 3 of 5 validators agreeing. GenVM lint, semantic validation
and type checking pass, and **16 Direct Mode tests** pass with the model mocked. Local tests
are not distributed-network results; the live receipts are linked below.

## The problem

A prize or grant pool can only be withheld from a plagiarised entry if the reuse finding
itself is neutral. In practice that finding is made by an organiser reading two submissions
by hand, which means the organiser can always justify keeping the pool. ReuseGate puts a
closed-vocabulary finding on chain next to a deterministic overlap measurement, so
withholding an award requires a consensus result rather than an opinion.

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

    assess(work_id, reference_id)
            |
            v
    [1] deterministic tier        normalized 5-gram shingle Jaccard plus the longest
        runs on every node        verbatim token run, against two thresholds
            |
            +-- threshold met --> DERIVATIVE, tier=DETERMINISTIC_COPY, no model called
            |
            v
    [2] model tier                leader and every validator independently ask the model
        ambiguous pairs only      for one value from a closed vocabulary
            |
            +-- agree on verdict and on both measurements --> finding, tier=MODEL
            |
            +-- disagreement or unusable answer ---------> INCONCLUSIVE, gate closed

Two details matter for reviewers:

- The validator compares the **verdict** and the two **deterministic measurements**. The
  model's free-text reason code is stored for humans but never compared, because two honest
  models word the same finding differently.
- Any unusable answer fails closed. Off-vocabulary verdicts, malformed JSON and model errors
  all become `INCONCLUSIVE`, never `INDEPENDENT`.

## Outcomes

| Verdict | Meaning | Gate |
| --- | --- | --- |
| `DERIVATIVE` | The subject reproduces the reference's wording, structure or substance with only cosmetic changes, including translation. | closed |
| `INDEPENDENT` | The subject shares only topic, common knowledge or generic phrasing and could not have been produced by editing the reference. | open |
| `INCONCLUSIVE` | The excerpts were too short, truncated or ambiguous, or validators disagreed. | closed |
| (no finding) | The pair has never been assessed. | closed |

`gate_open` returns `true` only for `INDEPENDENT`. A consumer that pays on any other value
is outside this contract's design.

## Public methods

| Method | Kind | Purpose |
| --- | --- | --- |
| `register_work(work_id, title, text)` | write | Register one work permanently. 80 to 6000 bytes, at least 12 normalized tokens, unique ID. |
| `assess(work_id, reference_id)` | write | Adjudicate one ordered pair. Writes one finding, once, and never overwrites it. |
| `gate_open(work_id, reference_id)` | view | The only boolean a paying contract should read. Fails closed. |
| `verdict_of`, `tier_of`, `reason_of` | view | The finding, the tier that produced it, and the model's stored reason code. |
| `overlap_bp_of`, `run_of` | view | The deterministic measurements, always recorded even when the model decided. |
| `config` | view | The deployed thresholds, so a reader never has to trust this file. |
| `is_registered`, `title_of`, `registered_count` | view | Registry lookups. |

No admin method, no pause, no payout and no fund custody exists. Anyone may register and
anyone may assess. Inputs and findings are public.

## Normalization

Both texts are folded before comparison: lowercasing, Arabic and Farsi letter variants
unified (`U+064A` and `U+0649` to `U+06CC`, `U+0643` to `U+06A9`, `U+0629` to `U+0647`),
harakat, tatweel, ZWNJ, ZWJ and direction marks dropped, punctuation collapsed to single
spaces. Without this, two spellings of the same word compare as different words. The folding
is language agnostic; it does not attempt stemming, lemmatization or translation.

## Reproduce the local checks

From the repository root, with Python 3.12 or newer:

    python -m venv .venv
    source .venv/bin/activate
    python -m pip install -r requirements-dev.txt
    python scripts/prepare_test_sdk.py
    genvm-lint check contracts/reuse_gate.py
    genvm-lint typecheck contracts/reuse_gate.py
    python -m pytest tests -q

Keep the virtual environment activated: `genvm-lint typecheck` looks for `pyright` on
`PATH`. The helper script links the GenVM release archive that direct mode expects; it does
not patch the contract or any installed package.

Expected output:

    Lint passed (3 checks)
    Validation passed
      Contract: ReuseGate
      Methods: 12 (10 view, 2 write)

    No type errors found

    16 passed

All model calls are mocked in Direct Mode. The tests cover a near-verbatim copy decided
without any model call, Arabic and Farsi letter variants folding to equality, ZWNJ and
tatweel not hiding a copy, zero-overlap pairs that must not short-circuit to `INDEPENDENT`,
off-vocabulary and malformed model output failing closed, duplicate IDs, thin text,
self-comparison, unknown references, immutability of findings, the gate being closed before
any assessment, the reported configuration, and both constructor bounds.

## Live Studionet evidence

Observed 2026-10-27 on Studionet, chain `61999`, contract
[`0x756DD19B75ce173B8EbdA79F9df93ac983Dd5EFd`](https://explorer-studio.genlayer.com/address/0x756DD19B75ce173B8EbdA79F9df93ac983Dd5EFd).
All calls sent `0 GEN`. The assessment ran in Normal (Full Consensus) mode with five initial
validators, zero leader rotations and no appeal.

| Action | Transaction | Result |
| --- | --- | --- |
| Deploy (`copy_bp=2000`, `copy_run=12`) | [`0xf11176bc...359d0a`](https://explorer-studio.genlayer.com/tx/0xf11176bc6c5da2b6d8def4f2ffb78eec8a19c0abfe85d8e0f51bb34cbd359d0a) | `FINALIZED`, GenVM `SUCCESS` |
| `register_work("grant-original")` | [`0xa2f495ad...e2a8b4`](https://explorer-studio.genlayer.com/tx/0xa2f495ad240a117b27a7d57a4706bb0f2b878416e6ef8e1eef44ae6e35e2a8b4) | `FINALIZED` |
| `register_work("grant-resubmission")` | [`0x3d628c3c...c6001a9a`](https://explorer-studio.genlayer.com/tx/0x3d628c3cdbdbbac188900063b9e6015e1ba15c993f156a79fd558253c6001a9a) | `FINALIZED` |
| `assess("grant-resubmission", "grant-original")` | [`0x70be3a4d...1c233e68`](https://explorer-studio.genlayer.com/tx/0x70be3a4d98b4d374710f2c2dc07d6301c2c27679fe30df5759c646bf1c233e68) | `FINALIZED`, 3 agree of 5, consensus `DERIVATIVE` |

Reads against the deployed contract after that assessment:

| Call | Value | What it shows |
| --- | --- | --- |
| `config()` | `2000` then `12` | The deployed thresholds, read from state rather than from this file. |
| `tier_of(...)` | `MODEL` | The deterministic tier could not decide, so the model tier did. |
| `overlap_bp_of(...)` | `0` | The two texts share no five-token shingle at all. |
| `verdict_of(...)` | `DERIVATIVE` | Validators agreed the second text is an edited version of the first. |
| `gate_open(...)` | `false` | The gate closed, so a paying contract must not release the award. |

That single assessment is the interesting evidence: the overlap was **zero**, so no
deterministic rule could have called it either way, and a hash-based contract would have had
to either pass the entry or reject it on a guess. Consensus over the model's reading decided
it instead.

The exact texts used on chain, so a reviewer can reproduce the pair:

    reference (grant-original):
    Our proposal introduces a neutral arbitration layer for community grants. Every payout
    above one hundred tokens is reviewed by three independent validators who read the
    submitted milestone report and decide whether the promised deliverable was actually
    shipped. Validators compare the report against the original commitment and publish the
    finding before any funds leave the pool.

    subject (grant-resubmission):
    We suggest adding an impartial judging layer to community funding. Any transfer larger
    than a hundred tokens gets checked by three separate reviewers who examine the milestone
    write-up and determine if the agreed output genuinely reached users. The reviewers set
    the write-up beside the initial promise and make the conclusion public before the
    treasury releases anything.

## What this contract does not do

- **It is not a plagiarism detector.** It compares one pair, on excerpts of at most 1800
  characters each, and returns one of three values. It cannot search a corpus, and it does
  not know about citations, licences or attribution conventions.
- **It does not move or hold funds.** A prize contract that wants to consume the gate has to
  do that itself and must re-read `gate_open` after finality.
- **A finding is final.** One ordered pair gets exactly one assessment, with no appeal and no
  re-run, because an overwritable finding would not be worth reading. If a pair lands as
  `INCONCLUSIVE`, it stays that way; register a new work id to try again.
- **Assessment is retrospective over stored text.** Works are registered as text, not fetched
  from a URL. Whoever registers a work asserts that the text is what it claims to be; this
  contract cannot verify authorship, ownership or whether the registration predates someone
  else's copy.
- **Paraphrase detection is the model's job.** The deterministic tier is a proof tool, not a
  filter, and it is deliberately biased toward silence. Translated or rewritten copying
  reaches the model tier, where the outcome depends on genuine validator agreement.
- **Consensus can simply fail.** If validators see different model output, the transaction
  can end undetermined and no finding is written. That is intended: the contract would
  rather store nothing than store a guess.
- **Studionet is a hosted development network.** Its state is temporary and its validators
  run real models, but it is not a production network and this deployment carries no
  security audit. Nothing here is a legal judgment or a substitute for one.

## License

MIT. See [LICENSE](LICENSE).
