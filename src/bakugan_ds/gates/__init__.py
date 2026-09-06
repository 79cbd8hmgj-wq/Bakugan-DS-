"""Gate Card reverse-engineering evidence models and tooling."""

from bakugan_ds.gates.install import (
    InstallReport,
    install_milestone_6c,
    install_milestone_6d,
)
from bakugan_ds.gates.model import (
    AddressRef,
    Confidence,
    GateControlCase,
    LegacyGateTableSpec,
)
from bakugan_ds.gates.record import (
    GateArchetype,
    GateConditionId,
    GateEffectId,
    GateTargetMode,
    GateTimingPhase,
)
from bakugan_ds.gates.roster_analysis import (
    REFERENCE_CASE_COUNT,
    build_roster_analysis,
    write_roster_analysis,
)
from bakugan_ds.gates.roster_identity import (
    GateRosterIdentityEntry,
    GateRosterIdentityMap,
    load_gate_roster_identity_map,
)
from bakugan_ds.gates.roster_metadata import (
    DesignTier,
    GateRosterMetadataEntry,
    MappingConfidence,
    ReviewStatus,
    RosterFamily,
    load_gate_roster_metadata,
)

__all__ = [
    "REFERENCE_CASE_COUNT",
    "AddressRef",
    "Confidence",
    "DesignTier",
    "GateArchetype",
    "GateConditionId",
    "GateControlCase",
    "GateEffectId",
    "GateRosterIdentityEntry",
    "GateRosterIdentityMap",
    "GateRosterMetadataEntry",
    "GateTargetMode",
    "GateTimingPhase",
    "InstallReport",
    "LegacyGateTableSpec",
    "MappingConfidence",
    "ReviewStatus",
    "RosterFamily",
    "build_roster_analysis",
    "install_milestone_6c",
    "install_milestone_6d",
    "load_gate_roster_identity_map",
    "load_gate_roster_metadata",
    "write_roster_analysis",
]
