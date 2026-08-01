from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
from pathlib import Path
from typing import Any

from bakugan_ds.analysis.arm import function_address_for_reference
from bakugan_ds.analysis.model import Component, SymbolCandidate
from bakugan_ds.analysis.numeric import cluster_numeric_matches, scan_scaled_byte_rows
from bakugan_ds.analysis.strings import (
    extract_ascii_strings,
    filter_strings,
    find_pointer_references,
)

DEFAULT_KEYWORDS = (
    "gpower",
    "g_power",
    "gp_",
    "fieldpower",
    "bakugan",
    "gate",
    "ability",
    "battle",
)


def analyze_components(
    components: tuple[Component, ...],
    reference_catalog: dict[str, Any],
    *,
    keywords: tuple[str, ...] = DEFAULT_KEYWORDS,
) -> dict[str, object]:
    if not components:
        raise ValueError("at least one component is required")
    strings = tuple(
        record
        for component in components
        for record in filter_strings(extract_ascii_strings(component), keywords)
    )
    string_rows: list[dict[str, object]] = []
    evidence_by_function: dict[tuple[str, int], list[str]] = {}
    by_name = {component.name: component for component in components}
    if len(by_name) != len(components):
        raise ValueError("component names must be unique")

    for record in strings:
        references = find_pointer_references(components, record.address)
        string_rows.append(
            asdict(record) | {"references": [asdict(reference) for reference in references]}
        )
        if record.text in {"gp_pickup2", "gp_down"}:
            for reference in references:
                source = by_name[reference.component]
                function_address = function_address_for_reference(source, reference.offset)
                if function_address is not None:
                    evidence_by_function.setdefault((source.name, function_address), []).append(
                        f"literal 0x{reference.address:08X} references "
                        f"{record.text!r} at 0x{record.address:08X}"
                    )

    symbol_candidates = tuple(
        SymbolCandidate(
            component=component_name,
            address=address,
            offset=address - by_name[component_name].base_address,
            name=f"Candidate_GPEffect_State_{address:08X}",
            confidence="candidate",
            evidence="; ".join(sorted(set(evidence))),
        )
        for (component_name, address), evidence in sorted(evidence_by_function.items())
    )

    gates = reference_catalog.get("gate_cards", [])
    if not isinstance(gates, list):
        raise ValueError("gate_cards must be a list")
    numeric_matches = scan_scaled_byte_rows(
        components,
        gates,
        values_key="bonuses",
        divisor=10,
    )
    return {
        "format_version": 1,
        "components": [
            {
                "name": component.name,
                "file_name": component.path.name,
                "sha256": hashlib.sha256(component.data).hexdigest(),
                "base_address": component.base_address,
                "size": len(component.data),
                "end_address": component.end_address,
            }
            for component in components
        ],
        "keyword_strings": string_rows,
        "numeric_matches": [asdict(match) for match in numeric_matches],
        "numeric_clusters": list(cluster_numeric_matches(numeric_matches)),
        "symbol_candidates": [asdict(candidate) for candidate in symbol_candidates],
    }


def write_report(path: Path, report: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)
