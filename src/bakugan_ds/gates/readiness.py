from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from bakugan_ds.errors import WorkspaceError
from bakugan_ds.gates.discovery import DiscoveryArtifact, Presence
from bakugan_ds.gates.io import load_json_object


@dataclass(frozen=True)
class Requirement:
    name: str
    artifact: str
    field: str
    allow_absent: bool
    allow_deferred: bool

    def validate(self) -> None:
        for label, value in (
            ("name", self.name),
            ("artifact", self.artifact),
            ("field", self.field),
        ):
            if not value.strip():
                raise WorkspaceError(f"requirement {label} must be nonempty")
        if type(self.allow_absent) is not bool:
            raise WorkspaceError(
                f"requirement {self.name} allow_absent must be a boolean"
            )
        if type(self.allow_deferred) is not bool:
            raise WorkspaceError(
                f"requirement {self.name} allow_deferred must be a boolean"
            )
        if self.allow_deferred and self.name != "arena_id":
            raise WorkspaceError("only arena_id may allow deferred evidence")
        if self.name == "arena_id" and not self.allow_deferred:
            raise WorkspaceError("arena_id must explicitly allow deferred evidence")


@dataclass(frozen=True)
class ReadinessFailure:
    requirement: str
    reason: str


@dataclass(frozen=True)
class ReadinessResult:
    ready: bool
    confirmed: tuple[str, ...]
    deferred: tuple[str, ...]
    failures: tuple[ReadinessFailure, ...]


def _require_array(value: object, label: str) -> list[object]:
    if not isinstance(value, list):
        raise WorkspaceError(f"{label} must be a JSON array")
    return value


def _require_object(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise WorkspaceError(f"{label} must be a JSON object")
    return value


def _require_bool(value: object, label: str) -> bool:
    if not isinstance(value, bool):
        raise WorkspaceError(f"{label} must be a boolean")
    return value


def load_requirements(path: Path) -> tuple[Requirement, ...]:
    payload = load_json_object(path)
    if payload.get("format_version") != 1:
        raise WorkspaceError(f"unsupported requirement format in {path}")
    requirements: list[Requirement] = []
    names: set[str] = set()
    for index, raw in enumerate(
        _require_array(payload.get("requirements"), "requirements")
    ):
        item = _require_object(raw, f"requirements[{index}]")
        try:
            requirement = Requirement(
                name=str(item["name"]),
                artifact=str(item["artifact"]),
                field=str(item["field"]),
                allow_absent=_require_bool(
                    item["allow_absent"], f"requirements[{index}].allow_absent"
                ),
                allow_deferred=_require_bool(
                    item["allow_deferred"],
                    f"requirements[{index}].allow_deferred",
                ),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise WorkspaceError(f"invalid requirements[{index}]: {exc}") from exc
        requirement.validate()
        if requirement.name in names:
            raise WorkspaceError(f"duplicate requirement: {requirement.name}")
        names.add(requirement.name)
        requirements.append(requirement)
    if "arena_id" not in names:
        raise WorkspaceError("requirements must include arena_id")
    return tuple(sorted(requirements, key=lambda item: item.name))


def _failure(
    failures: list[ReadinessFailure],
    requirement: str,
    reason: str,
) -> None:
    candidate = ReadinessFailure(requirement=requirement, reason=reason)
    if candidate not in failures:
        failures.append(candidate)


def evaluate_readiness(
    requirements: tuple[Requirement, ...],
    artifacts: Mapping[str, DiscoveryArtifact],
) -> ReadinessResult:
    confirmed: list[str] = []
    deferred: list[str] = []
    failures: list[ReadinessFailure] = []

    for requirement in requirements:
        try:
            requirement.validate()
        except WorkspaceError as exc:
            _failure(failures, requirement.name, str(exc))
            continue
        artifact = artifacts.get(requirement.artifact)
        if artifact is None:
            _failure(
                failures,
                requirement.name,
                f"missing discovery artifact: {requirement.artifact}",
            )
            continue
        try:
            artifact.validate()
        except WorkspaceError as exc:
            _failure(
                failures,
                requirement.name,
                f"invalid discovery artifact {requirement.artifact}: {exc}",
            )
            continue

        field = artifact.field_by_name(requirement.field)
        if field is not None:
            try:
                field.validate(
                    required=True,
                    allow_absent=requirement.allow_absent,
                    allow_deferred=requirement.allow_deferred,
                )
            except WorkspaceError as exc:
                _failure(failures, requirement.name, str(exc))
                continue
            if field.presence is Presence.DEFERRED:
                deferred.append(requirement.name)
            else:
                confirmed.append(requirement.name)
            continue

        check = artifact.check_by_name(requirement.field)
        if check is not None:
            if requirement.allow_absent or requirement.allow_deferred:
                _failure(
                    failures,
                    requirement.name,
                    "behavior checks cannot allow absent or deferred evidence",
                )
                continue
            try:
                check.validate(required=True)
            except WorkspaceError as exc:
                _failure(failures, requirement.name, str(exc))
                continue
            confirmed.append(requirement.name)
            continue

        _failure(
            failures,
            requirement.name,
            f"missing discovery field or check: {requirement.field}",
        )

    for artifact in artifacts.values():
        for unresolved in artifact.unresolved:
            if unresolved != "arena_id":
                _failure(
                    failures,
                    unresolved,
                    f"non-arena unresolved field in {artifact.domain}",
                )

    unique_deferred = tuple(sorted(set(deferred)))
    if unique_deferred != ("arena_id",) and not any(
        item.requirement == "arena_id" for item in failures
    ):
        _failure(
            failures,
            "arena_id",
            "arena_id must be explicitly present as the sole deferred field",
        )

    ordered_failures = tuple(
        sorted(failures, key=lambda item: (item.requirement, item.reason))
    )
    return ReadinessResult(
        ready=not ordered_failures and unique_deferred == ("arena_id",),
        confirmed=tuple(sorted(set(confirmed))),
        deferred=unique_deferred,
        failures=ordered_failures,
    )
