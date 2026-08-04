from pathlib import Path


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text()
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected one match, found {count}: {old!r}")
    path.write_text(text.replace(old, new, 1))


def replace_count(path: Path, old: str, new: str, expected: int) -> None:
    text = path.read_text()
    count = text.count(old)
    if count != expected:
        raise SystemExit(f"{path}: expected {expected} matches, found {count}: {old!r}")
    path.write_text(text.replace(old, new))


def rename_overlay_loop(path: Path, loop_header: str, end_marker: str) -> None:
    text = path.read_text()
    start = text.index(loop_header)
    end = text.index(end_marker, start)
    block = text[start:end]
    block = block.replace(
        loop_header,
        loop_header.replace("entry", "overlay_entry"),
        1,
    )
    block = block.replace("entry.", "overlay_entry.")
    path.write_text(text[:start] + block + text[end:])


rename_overlay_loop(
    Path("src/bakugan_ds/workspace/validate.py"),
    "    for entry in manifest.overlays:\n",
    "    unmatched_overlay_ids =",
)
rename_overlay_loop(
    Path("src/bakugan_ds/workspace/rebuild.py"),
    "    for entry in validated.manifest.overlays:\n",
    '    for kind in ("arm9", "arm7"):',
)

cli = Path("src/bakugan_ds/gates/cli.py")
replace_once(
    cli,
    "        _, spec, records = _load_verified_legacy(arguments)\n",
    "        _, spec, legacy_records = _load_verified_legacy(arguments)\n",
)
replace_once(
    cli,
    "        export_legacy_table(output, records, spec)\n",
    "        export_legacy_table(output, legacy_records, spec)\n",
)
replace_once(
    cli,
    "        records = load_authoring_document(arguments.authoring)\n",
    "        gate_records = load_authoring_document(arguments.authoring)\n",
)
replace_once(
    cli,
    "        trailer = build_trailer(records)\n",
    "        trailer = build_trailer(gate_records)\n",
)
replace_once(
    cli,
    "        report = install_milestone_6c(\n",
    "        install_report = install_milestone_6c(\n",
)
text = cli.read_text()
start = text.index('    if arguments.gate_command == "install-milestone-6c":')
end = text.index('    if arguments.gate_command == "validate-trailer":', start)
block = text[start:end].replace("report.", "install_report.")
cli.write_text(text[:start] + block + text[end:])
replace_once(
    cli,
    "        report = generate_readiness_report(\n",
    "        readiness_report = generate_readiness_report(\n",
)
text = cli.read_text()
start = text.index('    if arguments.gate_command == "readiness":')
end = text.index("    raise WorkspaceError", start)
block = text[start:end].replace("report.", "readiness_report.")
cli.write_text(text[:start] + block + text[end:])

replace_once(
    cli,
    "handle = tempfile.NamedTemporaryFile(",
    "handle = tempfile.NamedTemporaryFile(  # noqa: SIM115",
)
rebuild = Path("src/bakugan_ds/workspace/rebuild.py")
replace_count(
    rebuild,
    "_handle = tempfile.NamedTemporaryFile(",
    "_handle = tempfile.NamedTemporaryFile(  # noqa: SIM115",
    2,
)
validate = Path("src/bakugan_ds/workspace/validate.py")
replace_once(
    validate,
    '                f"modified {name.upper()} size mismatch: expected {expected_size}, got {len(modified)}"',
    '                f"modified {name.upper()} size mismatch: expected {expected_size}, got {len(modified)}"  # noqa: E501',
)
