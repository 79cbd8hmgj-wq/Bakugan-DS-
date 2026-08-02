# Milestone 6A Verification Record

## GitHub Actions verification

Pull request #14 now runs the repository's Python verification workflow on Ubuntu 24.04 with Python 3.11.

Workflow run `30747686566` completed successfully against branch head `4f99a12c380a55bf0d4dd416738a9a7b9b69930f`.

Passed checks:

- editable installation with the declared development dependencies;
- `python -m compileall -q src tests tools`;
- Ruff on every Python file changed by the pull request;
- strict mypy on all 13 changed package source files;
- the complete repository pytest suite;
- `git diff --check` against `main`.

The test result was:

```text
237 collected
226 passed
11 skipped
0 failed
```

The eleven skips are expected environment-gated checks requiring a user-supplied ROM, runtime-decompressed ARM9 image, decoded overlay 7, or other local reverse-engineering input. No integration test failed.

During CI enablement, the workflow found and the branch corrected:

- changed-file Ruff formatting findings;
- eleven strict typing defects in new Gate evidence parsers and CLI variables;
- one stale core-G validation test that still expected an older evidence schema.

The corrected core-G test now validates the current clean tutorial exit, responsive story return, high-G constructor cases, preserved mutable modifiers, and unscaled Gate bonuses.

## Focused Gate verification

Before full CI was available, the focused Gate Card System 2.0 harness produced:

```text
63 passed
4 skipped
0 failed
```

It also confirmed:

- `bakugan-ds gate --help` exposes `inspect`, `export-legacy`, and `report-context`;
- all six committed `analysis/gates/*.json` artifacts parse and end with a newline;
- the placeholder scan for `TODO`, `TBD`, and `FIXME` is empty;
- all Gate unit and artifact tests pass.

## Direct exact-ROM verification

A separate direct verifier used the user-supplied supported ROM, runtime-decompressed ARM9, and decoded overlay 7. It confirmed:

- supported ROM SHA-256;
- runtime ARM9 and overlay-7 SHA-256 values;
- 213 Gate-table records and the confirmed table-region hash;
- selected rows for Juggernoid, Robotallion, and Serpenoid;
- the fixed battle-type metadata table and all six selected type cases;
- all four hook-site byte hashes and non-overlap with protected core-G ranges;
- 213 indexed in-game card names;
- the six attribute labels and order;
- raw-LZ10 trailer append leaves native decoded card-name messages byte-identical;
- overlay-7 RAM/BSS metadata and the original battle-arena boundary literal.

The direct verifier completed with:

```text
exact ROM/runtime verification passed
gate_table_records=213 selector_cases=6 hook_sites=4 card_names=213
```

## Verification boundary

Public CI cannot contain or download the copyrighted ROM or extracted runtime binaries. The corresponding integration tests therefore remain environment-gated and are supplemented by the direct exact-ROM verification above.

Milestone 6A is ready for normal pull-request review. It does not implement or claim a System 2.0 gameplay effect; the first prototype remains assigned to Milestone 6B.
