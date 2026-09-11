# Running Milestone 6E Task 13 locally

Task 13 (bounded live representative runtime acceptance) requires the
user-owned reference ROM and a GDB-capable DeSmuME build. Neither can be
present in this repository or in a hosted CI/agent sandbox, so the scenario
and acceptance matrix in `src/bakugan_ds/runtime/milestone_6e_task13.py` are
constructed and unit-tested against the real toolkit API, but have not been
executed. This is a runbook for a local operator to finish the job.

## Prerequisites

1. Install the `runtime` extra, which pulls in the hardened NDS
   Disassembly Toolkit orchestration layer:

   ```bash
   pip install -e ".[dev,runtime]"
   ```

2. A GDB-enabled DeSmuME build (`--arm9gdb`). Verify it with the toolkit's
   doctor, including the live-probe mode, against a disposable ROM first:

   ```bash
   nds-toolkit runtime doctor --emulator desmume --rom /path/to/any.nds \
     --require debugger_arm9 --require window_input --destructive
   ```

3. The exact rebuilt ROM produced by:

   ```bash
   bakugan-ds rebuild "/path/to/Bakugan - Battle Brawlers.nds" \
     <workspace> output/Bakugan-modded.nds
   ```

   using the `b6re_rev0` profile, with the current Milestone 6E workspace.

## Capture the required checkpoints

Each sample-matrix case needs one savestate checkpoint captured by hand,
with that specific Gate ID selected and about to be evaluated. List exactly
what each one must capture:

```python
from bakugan_ds.runtime.milestone_6e_task13 import describe_required_checkpoints

for name, description in describe_required_checkpoints().items():
    print(name, "->", description)
```

For each one:

```bash
nds-toolkit runtime launch output/Bakugan-modded.nds --emulator desmume \
  --cpu arm9 --session-root ./sessions/task13
# ... drive the UI manually to the required in-game state ...
nds-toolkit runtime checkpoint save ./sessions/task13/<session-id> \
  gate-019-juggernoid-comeback
# repeat for every name printed above
```

## Write out each case's scenario

Each sample-matrix case is its own `ScenarioDefinition` with its checkpoint
baked in (`ScenarioDefinition.checkpoint`), which `run_scenario` restores
automatically - there's no shared baseline checkpoint to coordinate. Write
each one out with `store_scenario` (the write side of `load_scenario`,
added alongside this runbook):

```python
from pathlib import Path

from nds_disassembly_toolkit.analysis.orchestration import store_scenario
from bakugan_ds.runtime.milestone_6e_task13 import build_all_scenarios

scenario_dir = Path("./sessions/task13/scenarios")
scenario_dir.mkdir(parents=True, exist_ok=True)
for checkpoint_name, scenario in build_all_scenarios().items():
    store_scenario(scenario_dir / f"{checkpoint_name}.json", scenario)
```

## Run each case

Each run is independent and bounded (two health asserts plus five real
breakpoint hits), so a plain shell loop over the toolkit CLI is enough:

```bash
session=./sessions/task13/<session-id>
for scenario in ./sessions/task13/scenarios/*.json; do
  nds-toolkit runtime scenario run "$session" "$scenario" \
    --output "${scenario%.json}.result.json"
done
```

Prefer not to block your shell for the whole loop? Wrap each run in a
background job instead - `runtime job start` returns immediately and
`runtime job status` polls for completion:

```bash
nds-toolkit runtime job start ./sessions/task13/jobs/gate-019 -- \
  scenario run "$session" ./sessions/task13/scenarios/gate-019-juggernoid-comeback.json
nds-toolkit runtime job status ./sessions/task13/jobs/gate-019
```

## Record the results

Update `analysis/runtime-observations/gate-system2-milestone-6e-validation.json`
with the real outcome once the matrix has actually run - `status`,
`task13_scaffold.not_yet_done`, and `rejected_claims` should all change to
reflect what was actually observed, per this project's evidentiary
discipline. Per the repository boundary, do not commit the ROM, savestates,
screenshots, or raw frames themselves - only normalized hashes and derived
observations.
