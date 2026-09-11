"""Milestone 6E Task 13: bounded live representative runtime acceptance.

This module builds (but does not itself execute) the runtime scenarios for
Task 13, using only:

- the pinned NDS Disassembly Toolkit orchestration layer (session/checkpoint/
  scenario primitives, hardened under the runtime-reliability milestone:
  real health probes, a persistent watchdog, auto-relaunch from checkpoints,
  enforced checkpoint verification regions, and hard subprocess deadlines -
  see that toolkit's docs/runtime-debugging.md);
- the confirmed Gate System 2.0 loader/calculation/selector breakpoints in
  ``analysis/symbols/gate_system2_context.csv``;
- the approved Milestone 6E roster metadata in
  ``config/gates/milestone-6e-roster-metadata.json``.

It deliberately does not set any breakpoint or memory region outside the
confirmed symbol table (no broad RAM scans), and it does not fabricate a
button/touch navigation sequence from title screen to a specific Gate
selection: that sequence is only known empirically, from a live session, and
per this project's repository boundary a live session's frames/states/
journals are never committed. A local runner must capture one checkpoint per
sample-matrix case (see :func:`describe_required_checkpoints`) by hand
before running its scenario, with that specific card already selected and
about to be evaluated.

Each case gets its own :class:`ScenarioDefinition` with its checkpoint baked
into ``ScenarioDefinition.checkpoint``, which ``run_scenario`` restores
automatically. This is deliberately not built on
``orchestration.acceptance.AcceptanceMatrix``: that matrix restores a single
shared baseline checkpoint for every case and differentiates cases only
through step parameters, which does not fit "one already-positioned
checkpoint per representative Gate" - see :func:`build_scenario_for_case`.

Actually executing this against the exact rebuilt ROM requires a local
DeSmuME build with GDB-stub support and the user-owned reference ROM, per
this project's own repository boundary (ROMs, saves, frames, and states are
never committed) - see ``docs/milestone-6e-task13-local-runbook.md`` and
``analysis/runtime-observations/gate-system2-milestone-6e-validation.json``
for current status.
"""

from __future__ import annotations

from dataclasses import dataclass

from nds_disassembly_toolkit.analysis.orchestration.model import (
    SCENARIO_SCHEMA_VERSION,
    EmulatorKind,
)
from nds_disassembly_toolkit.analysis.orchestration.scenario import (
    AssertStep,
    CaptureTraceStep,
    PredicateDefinition,
    ScenarioDefinition,
)
from nds_disassembly_toolkit.analysis.runtime.model import RuntimeCpu

# --- Confirmed Gate System 2.0 breakpoints -----------------------------
# Source: analysis/symbols/gate_system2_context.csv (mapping_confidence ==
# "confirmed" for every entry below). Values are live overlay_0007 RAM
# addresses (the overlay is loaded to a fixed address, so these are usable
# directly as GDB breakpoint addresses without further relocation).

TIMING_PRE_GATE = 0x0223D1D0
"""Pre-Gate boundary, after Gate identity/cache availability, before
contribution evaluation."""

TIMING_POST_GATE = 0x0223D290
"""Post-Gate boundary, immediately after the target-total G store."""

TIMING_PRE_BATTLE_TYPE = 0x0223E338
"""Boundary before explicit or fallback battle-type assignment."""

TIMING_POST_BATTLE_TYPE = 0x0224183C
"""Final battle-type boundary, after scripted overrides, before dispatch."""

TIMING_BATTLE_START = 0x02241908
"""Common convergence after the battle-type controller is constructed."""

TIMING_BATTLE_RESULT = 0x022423E0
"""Settled-result boundary, before capture-score mutation."""

TIMING_GATE_CAPTURE = 0x022423F0
"""Capture boundary, before score and ledger updates."""

TIMING_GATE_REMOVAL = 0x022626B8
"""Physical arena-placement removal boundary - the natural point to confirm
the 64-byte Gate System 2.0 cache has been fully cleared."""

TIMING_ROUND_RESET = 0x0223D3F4
"""Battle-object destructor boundary, ending per-round pointer validity."""

TIMING_MATCH_RESET = 0x0225FD5C
"""Gate-session constructor boundary, clearing match-local state - the
natural point to confirm a tutorial/session reset landed cleanly."""

LOOKUP_GATE_ATTRIBUTE_BONUS = 0x02065BF4
"""arm9 (not overlay_0007): pure Gate/attribute lookup, no state mutation."""

# --- Milestone 6E runtime contract geometry -----------------------------
# Source: analysis/gates/milestone-6e-runtime-contract.json. Unchanged from
# the frozen Milestone 6D runtime module/cache geometry.

MODULE_BASE = 0x0228BC20
MODULE_SIZE = 32768
GATE_SYSTEM2_CACHE_START = 0x02293C20
GATE_SYSTEM2_CACHE_LENGTH = 0x40  # 64 bytes: 0x02293C20..0x02293C60


@dataclass(frozen=True, slots=True)
class SampleMatrixCase:
    """One representative Gate ID in the Task 13 bounded sample matrix."""

    card_id: int
    label: str
    rationale: str

    @property
    def checkpoint_name(self) -> str:
        return f"gate-{self.card_id:03d}-{self.label}"


# --- Task 13 sample matrix ------------------------------------------------
# Selected from config/gates/milestone-6e-roster-metadata.json (the approved
# 103-record Milestone 6E table) to satisfy every requirement in
# docs/superpowers/plans/2026-08-05-milestone-6e-complete-gate-roster-conversion.md
# Task 13's "Sample matrix" section with the fewest distinct cards:
#
#   - Juggernoid                                    -> 19 (frozen fixture)
#   - one representative of each archetype           -> 1, 16, 19, 32, 40, 82, 96
#   - one landing-conditioned Gate                    -> 32 (shared with Control)
#   - one owner/non-owner Control Gate                -> 32 (owner) / 33 (non-owner)
#   - one owner/opponent-at-match-point Gate          -> 6
#   - one high-risk drawback Gate                     -> 82 (shared with Risk)
#
# Selection is reproducible: see tests/unit/test_milestone_6e_task13.py,
# which re-derives it from the roster metadata rather than hardcoding it
# independently.
SAMPLE_MATRIX: tuple[SampleMatrixCase, ...] = (
    SampleMatrixCase(
        19, "juggernoid-comeback", "Juggernoid; frozen Milestone 6D fixture; Comeback archetype."
    ),
    SampleMatrixCase(
        1, "power-unconditional", "Power archetype representative; unconditional flat G."
    ),
    SampleMatrixCase(
        16, "skill-tied-score", "Skill archetype representative; tied-score condition."
    ),
    SampleMatrixCase(
        32,
        "control-owner-landing",
        "Control archetype; owner-targeted; landing-conditioned.",
    ),
    SampleMatrixCase(
        33,
        "control-nonowner-landing",
        "Control archetype; non-owner-targeted; landing-conditioned.",
    ),
    SampleMatrixCase(
        40, "attribute-tied-score", "Attribute archetype representative; tied-score condition."
    ),
    SampleMatrixCase(
        82,
        "risk-behind-drawback",
        "Risk archetype representative; explicit high-risk drawback.",
    ),
    SampleMatrixCase(
        96,
        "chaos-behind-drawback",
        "Chaos archetype representative; asymmetric G plus drawback.",
    ),
    SampleMatrixCase(6, "power-owner-match-point", "Owner-side-at-match-point condition."),
)


def describe_required_checkpoints() -> dict[str, str]:
    """What a local operator must capture (live, with the real ROM/DeSmuME)
    before running each case's scenario: one savestate checkpoint per
    sample-matrix case, named ``case.checkpoint_name``, captured with that
    specific Gate ID selected and about to be evaluated (i.e. paused just
    before :data:`TIMING_PRE_GATE` would next execute for that card).
    """
    return {
        case.checkpoint_name: (
            f"Card {case.card_id} ({case.label}) selected and about to be "
            f"evaluated; captured just before TIMING_PRE_GATE (0x{TIMING_PRE_GATE:08x}) "
            "would next execute for this card. " + case.rationale
        )
        for case in SAMPLE_MATRIX
    }


def build_scenario_for_case(case: SampleMatrixCase) -> ScenarioDefinition:
    """The scenario for one sample-matrix case.

    ``ScenarioDefinition.checkpoint`` is set to ``case.checkpoint_name``, so
    ``run_scenario`` restores it automatically before the first step - the
    checkpoint must already have been captured locally (see
    :func:`describe_required_checkpoints`).

    Uses only real GDB breakpoints (``CaptureTraceStep(break_address=...)``,
    mode BREAKPOINT, limit 1) at the confirmed Timing* boundaries, never a
    polled/broad memory scan. Each trace also captures the 64-byte Gate
    System 2.0 cache as BEFORE/AFTER memory evidence.
    """
    cache_region = (GATE_SYSTEM2_CACHE_START, GATE_SYSTEM2_CACHE_LENGTH)
    return ScenarioDefinition(
        schema_version=SCENARIO_SCHEMA_VERSION,
        name=f"milestone-6e-task13-{case.checkpoint_name}",
        backend=EmulatorKind.DESMUME,
        cpu=RuntimeCpu.ARM9,
        required_capabilities=("debugger_arm9", "save_state"),
        checkpoint=case.checkpoint_name,
        steps=(
            AssertStep(
                id="assert-runtime-healthy",
                condition=PredicateDefinition(type="process_alive"),
                timeout=5.0,
            ),
            AssertStep(
                id="assert-debugger-reachable",
                condition=PredicateDefinition(type="debugger_reachable"),
                timeout=5.0,
            ),
            CaptureTraceStep(
                id="trace-pregate",
                output="pregate.ndstrace",
                break_address=TIMING_PRE_GATE,
                memory=(cache_region,),
            ),
            CaptureTraceStep(
                id="trace-postgate",
                output="postgate.ndstrace",
                break_address=TIMING_POST_GATE,
                memory=(cache_region,),
            ),
            CaptureTraceStep(
                id="trace-pre-battle-type",
                output="pre-battle-type.ndstrace",
                break_address=TIMING_PRE_BATTLE_TYPE,
                memory=(cache_region,),
            ),
            CaptureTraceStep(
                id="trace-post-battle-type",
                output="post-battle-type.ndstrace",
                break_address=TIMING_POST_BATTLE_TYPE,
                memory=(cache_region,),
            ),
            CaptureTraceStep(
                id="trace-gate-removal",
                output="gate-removal.ndstrace",
                break_address=TIMING_GATE_REMOVAL,
                memory=(cache_region,),
            ),
        ),
    )


def build_all_scenarios() -> dict[str, ScenarioDefinition]:
    """One scenario per :data:`SAMPLE_MATRIX` entry, keyed by checkpoint
    name. A local runner executes each independently (e.g. via
    ``run_scenario`` directly, or wrapped in ``runtime job start ... --
    scenario run SESSION SCENARIO_PATH`` so each run happens in the
    background instead of blocking)."""
    return {case.checkpoint_name: build_scenario_for_case(case) for case in SAMPLE_MATRIX}
