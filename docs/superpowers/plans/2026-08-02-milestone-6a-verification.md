# Milestone 6A Verification Record

## Fresh verification completed

The focused Gate Card System 2.0 foundation harness produced:

```text
63 passed
4 skipped
0 failed
```

The four skipped tests require the repository's complete historical workspace extractor. The focused execution harness intentionally contains only a stub for that older subsystem, so setting the exact-ROM environment variables produces `NotImplementedError` during fixture setup rather than exercising the branch code.

The following checks passed in the focused harness:

- Python compilation for the new Gate package and focused tests;
- `bakugan-ds gate --help` with `inspect`, `export-legacy`, and `report-context`;
- parsing and final-newline validation for all six committed `analysis/gates/*.json` artifacts;
- placeholder scan for `TODO`, `TBD`, and `FIXME`;
- all Gate unit and artifact tests.

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

The verifier completed with:

```text
exact ROM/runtime verification passed
gate_table_records=213 selector_cases=6 hook_sites=4 card_names=213
```

## Unavailable checks

`ruff` and `mypy` are not installed in the execution container, so no success is claimed for those commands.

A complete checkout of the repository could not be obtained because direct GitHub cloning and archive download failed DNS resolution in the execution container. The available GitHub connector can read and write repository files but cannot start a fresh workflow run. Therefore, the full pre-existing repository suite has not been rerun for this branch.

The pull request remains draft until the complete repository suite, configured Ruff checks, and configured mypy checks are run in a normal checkout or CI environment.
