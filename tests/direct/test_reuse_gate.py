"""Direct-mode tests for ReuseGate. No network, no Studio: the GenVM runs in memory.

Every fixture in this file is ASCII. Script folding is exercised with codepoint
escapes so the file stays plain ASCII while still testing the real letters.
"""

REFERENCE = (
    "Our proposal introduces a neutral arbitration layer for community grants. "
    "Every payout above one hundred tokens is reviewed by three independent validators "
    "who read the submitted milestone report and decide whether the promised deliverable "
    "was actually shipped. Validators compare the report against the original commitment "
    "and publish the finding before any funds leave the pool."
)

COPY = (
    "Our proposal introduces a neutral arbitration layer for community grants! "
    "Every payout above 100 tokens is reviewed by three independent validators, "
    "who read the submitted milestone report and decide whether the promised deliverable "
    "was actually shipped. Validators compare the report against the original commitment "
    "and publish the finding before any funds leave the pool."
)

PARAPHRASE = (
    "We suggest adding an impartial judging layer to community funding. "
    "Any transfer larger than a hundred tokens gets checked by three separate reviewers "
    "who examine the milestone write-up and determine if the agreed output genuinely "
    "reached users. The reviewers set the write-up beside the initial promise and make "
    "the conclusion public before the treasury releases anything."
)

UNRELATED = (
    "Photosynthesis converts light energy into chemical energy inside chloroplasts. "
    "The light dependent reactions split water molecules and release oxygen gas, while "
    "the Calvin cycle fixes carbon dioxide into sugar using ATP and NADPH that the "
    "earlier reactions produced. Chlorophyll absorbs mostly blue and red light."
)

# Codepoints used by the folding table in the contract.
ARABIC_YEH = "\u064a"
FARSI_YEH = "\u06cc"
ARABIC_KAF = "\u0643"
KEHEH = "\u06a9"
ZWNJ = "\u200c"
TATWEEL = "\u0640"
HAMZA_ABOVE = "\u0654"


def _repeat(word: str, times: int) -> str:
    return " ".join([word] * times)


def _gate(direct_deploy, bp=2000, run=12):
    return direct_deploy("contracts/reuse_gate.py", bp, run)


# ----------------------------------------------------------- deterministic tier
def test_near_verbatim_copy_is_derivative_without_any_model(direct_vm, direct_deploy):
    gate = _gate(direct_deploy)
    gate.register_work("a", "Original grant proposal", REFERENCE)
    gate.register_work("b", "Resubmission", COPY)

    # No mock_llm is registered: if the contract called the model this would fail.
    assert gate.assess("b", "a") == "DERIVATIVE"
    assert gate.tier_of("b", "a") == "DETERMINISTIC_COPY"
    assert int(gate.overlap_bp_of("b", "a")) > 5000
    assert int(gate.run_of("b", "a")) >= 12
    assert gate.gate_open("b", "a") is False


def test_arabic_and_farsi_letter_variants_are_folded(direct_vm, direct_deploy):
    """Two spellings of the same words must compare equal, not different."""
    farsi = _repeat(FARSI_YEH + KEHEH, 30)
    arabic = _repeat(ARABIC_YEH + ARABIC_KAF, 30)
    gate = _gate(direct_deploy)
    gate.register_work("orig", "Original spelling", farsi)
    gate.register_work("variant", "Resubmitted in arabic letters", arabic)

    assert gate.assess("variant", "orig") == "DERIVATIVE"
    assert gate.tier_of("variant", "orig") == "DETERMINISTIC_COPY"
    assert int(gate.overlap_bp_of("variant", "orig")) == 10000


def test_zwnj_and_tatweel_do_not_hide_a_copy(direct_vm, direct_deploy):
    """Joining marks and harakat are dropped before comparison."""
    plain = _repeat(FARSI_YEH + KEHEH + FARSI_YEH, 24)
    decorated = _repeat(FARSI_YEH + ZWNJ + KEHEH + TATWEEL + FARSI_YEH + HAMZA_ABOVE, 24)
    gate = _gate(direct_deploy)
    gate.register_work("orig", "Plain spelling", plain)
    gate.register_work("variant", "Decorated spelling", decorated)

    assert gate.assess("variant", "orig") == "DERIVATIVE"
    assert int(gate.overlap_bp_of("variant", "orig")) == 10000


def test_zero_overlap_never_short_circuits_to_independent(direct_vm, direct_deploy):
    """The core asymmetry: no overlap is not proof of independence."""
    gate = _gate(direct_deploy)
    gate.register_work("a", "Original grant proposal", REFERENCE)
    gate.register_work("p", "Paraphrased resubmission", PARAPHRASE)
    direct_vm.mock_llm(
        r"(?s).*neutral reuse auditor.*",
        '{"verdict": "DERIVATIVE", "reason_code": "paraphrase"}',
    )

    assert int(gate.overlap_bp_of("p", "a")) == 0
    assert gate.assess("p", "a") == "DERIVATIVE"
    assert gate.tier_of("p", "a") == "MODEL"
    assert gate.reason_of("p", "a") == "paraphrase"


# ----------------------------------------------------------------- model tier
def test_model_tier_finds_independent_work(direct_vm, direct_deploy):
    gate = _gate(direct_deploy)
    gate.register_work("a", "Original grant proposal", REFERENCE)
    gate.register_work("u", "Biology notes", UNRELATED)
    direct_vm.mock_llm(
        r"(?s).*neutral reuse auditor.*",
        '{"verdict": "INDEPENDENT", "reason_code": "common_knowledge"}',
    )

    assert gate.assess("u", "a") == "INDEPENDENT"
    assert gate.tier_of("u", "a") == "MODEL"
    assert gate.gate_open("u", "a") is True


def test_off_vocabulary_model_output_fails_closed(direct_vm, direct_deploy):
    gate = _gate(direct_deploy)
    gate.register_work("a", "Original grant proposal", REFERENCE)
    gate.register_work("p", "Paraphrased resubmission", PARAPHRASE)
    direct_vm.mock_llm(r"(?s).*neutral reuse auditor.*", '{"verdict": "ok fine"}')

    assert gate.assess("p", "a") == "INCONCLUSIVE"
    assert gate.gate_open("p", "a") is False


def test_malformed_model_output_fails_closed(direct_vm, direct_deploy):
    gate = _gate(direct_deploy)
    gate.register_work("a", "Original grant proposal", REFERENCE)
    gate.register_work("p", "Paraphrased resubmission", PARAPHRASE)
    direct_vm.mock_llm(r"(?s).*neutral reuse auditor.*", "not json at all")

    assert gate.assess("p", "a") == "INCONCLUSIVE"
    assert gate.gate_open("p", "a") is False


# ------------------------------------------------------------------- state rules
def test_duplicate_work_id_is_rejected(direct_vm, direct_deploy):
    gate = _gate(direct_deploy)
    gate.register_work("a", "Original grant proposal", REFERENCE)
    with direct_vm.expect_revert("WORK_EXISTS"):
        gate.register_work("a", "Copy of the same id", UNRELATED)


def test_thin_text_is_rejected(direct_vm, direct_deploy):
    gate = _gate(direct_deploy)
    with direct_vm.expect_revert("BAD_TEXT"):
        gate.register_work("x", "Too short", "just a few words")


def test_self_comparison_is_rejected(direct_vm, direct_deploy):
    gate = _gate(direct_deploy)
    gate.register_work("a", "Original grant proposal", REFERENCE)
    with direct_vm.expect_revert("SELF_COMPARE"):
        gate.assess("a", "a")


def test_unknown_work_is_rejected(direct_vm, direct_deploy):
    gate = _gate(direct_deploy)
    gate.register_work("a", "Original grant proposal", REFERENCE)
    with direct_vm.expect_revert("REFERENCE_NOT_FOUND"):
        gate.assess("a", "ghost")


def test_findings_are_immutable(direct_vm, direct_deploy):
    gate = _gate(direct_deploy)
    gate.register_work("a", "Original grant proposal", REFERENCE)
    gate.register_work("b", "Resubmission", COPY)
    gate.assess("b", "a")
    with direct_vm.expect_revert("ALREADY_ASSESSED"):
        gate.assess("b", "a")


def test_config_reports_the_deployed_thresholds(direct_vm, direct_deploy):
    gate = _gate(direct_deploy, bp=2500, run=14)
    assert gate.config() == "2500|14"


def test_gate_fails_closed_before_any_assessment(direct_vm, direct_deploy):
    gate = _gate(direct_deploy)
    gate.register_work("a", "Original grant proposal", REFERENCE)
    gate.register_work("b", "Resubmission", COPY)
    assert gate.gate_open("b", "a") is False
    assert gate.verdict_of("b", "a") == ""


# One contract class per test is a direct-mode limitation, so each bound gets its own test.
def test_copy_threshold_lower_bound_is_enforced(direct_vm, direct_deploy):
    with direct_vm.expect_revert("BAD_COPY_BP"):
        direct_deploy("contracts/reuse_gate.py", 10, 12)


def test_copy_run_lower_bound_is_enforced(direct_vm, direct_deploy):
    with direct_vm.expect_revert("BAD_COPY_RUN"):
        direct_deploy("contracts/reuse_gate.py", 2000, 2)
