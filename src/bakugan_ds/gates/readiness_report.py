from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from pathlib import Path

from bakugan_ds.errors import WorkspaceError
from bakugan_ds.gates.discovery import DiscoveryArtifact, load_discovery_artifact
from bakugan_ds.gates.io import load_json_object
from bakugan_ds.gates.readiness import (
    ReadinessFailure,
    evaluate_readiness,
    load_requirements,
)


@dataclass(frozen=True)
class ReadinessReport:
    confirmed: tuple[str, ...]
    deferred: tuple[str, ...]
    failures: tuple[ReadinessFailure, ...]
    artifact_hashes: dict[str, str]
    ready_for_milestone_6c: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "artifact_hashes": dict(sorted(self.artifact_hashes.items())),
            "confirmed": list(self.confirmed),
            "deferred": list(self.deferred),
            "failures": [asdict(failure) for failure in self.failures],
            "ready_for_milestone_6c": self.ready_for_milestone_6c,
        }


def _hash_file(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        raise WorkspaceError(f"cannot hash Gate evidence {path}: {exc}") from exc


def _candidate_files(evidence_dir: Path) -> tuple[Path, ...]:
    if not evidence_dir.is_dir():
        raise WorkspaceError(f"Gate evidence directory does not exist: {evidence_dir}")
    return tuple(sorted(evidence_dir.glob("*.json"), key=lambda path: path.name))


def _load_artifacts(
    evidence_dir: Path,
    required_domains: set[str],
) -> tuple[
    dict[str, DiscoveryArtifact],
    dict[str, str],
    tuple[ReadinessFailure, ...],
]:
    artifacts: dict[str, DiscoveryArtifact] = {}
    hashes: dict[str, str] = {}
    failures: list[ReadinessFailure] = []
    domain_paths: dict[str, Path] = {}

    for path in _candidate_files(evidence_dir):
        try:
            payload = load_json_object(path)
        except WorkspaceError:
            continue
        raw_domain = payload.get("domain")
        if not isinstance(raw_domain, str) or raw_domain not in required_domains:
            continue
        previous = domain_paths.get(raw_domain)
        if previous is not None:
            failures.append(
                ReadinessFailure(
                    requirement=f"artifact:{raw_domain}",
                    reason=(
                        "duplicate discovery domain in "
                        f"{previous.name} and {path.name}"
                    ),
                )
            )
            continue
        domain_paths[raw_domain] = path
        hashes[raw_domain] = _hash_file(path)
        try:
            artifact = load_discovery_artifact(path)
        except WorkspaceError as exc:
            failures.append(
                ReadinessFailure(
                    requirement=f"artifact:{raw_domain}",
                    reason=f"invalid discovery artifact {path.name}: {exc}",
                )
            )
            continue
        if artifact.domain != raw_domain:
            failures.append(
                ReadinessFailure(
                    requirement=f"artifact:{raw_domain}",
                    reason=f"artifact domain changed during normalization: {path.name}",
                )
            )
            continue
        artifacts[raw_domain] = artifact

    return (
        artifacts,
        dict(sorted(hashes.items())),
        tuple(sorted(failures, key=lambda item: (item.requirement, item.reason))),
    )


def generate_readiness_report(
    requirements_path: Path,
    evidence_dir: Path,
) -> ReadinessReport:
    requirements = load_requirements(requirements_path)
    required_domains = {requirement.artifact for requirement in requirements}
    artifacts, hashes, collection_failures = _load_artifacts(
        evidence_dir,
        required_domains,
    )
    result = evaluate_readiness(requirements, artifacts)
    failures = tuple(
        sorted(
            {*collection_failures, *result.failures},
            key=lambda item: (item.requirement, item.reason),
        )
    )
    ready = (
        not failures
        and result.deferred == ("arena_id",)
        and result.ready
    )
    return ReadinessReport(
        confirmed=result.confirmed,
        deferred=result.deferred,
        failures=failures,
        artifact_hashes=hashes,
        ready_for_milestone_6c=ready,
    )
