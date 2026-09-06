# Milestone 6E Verification

## Completed static and deterministic gates

- Final roster and metadata contain exactly 103 sorted entries.
- All seven archetypes are represented.
- All records are approved and nonlegacy.
- Juggernoid compatibility is preserved.
- No unsupported or deferred runtime fields are used.
- No hard duplicate or unresolved dominance finding remains.
- Host calculation and exact emitted-ARM parity is exercised over the complete reference matrix.
- Controlled selector seeds cover every authored weight vector.
- The Milestone 6E installer uses the frozen Milestone 6D module and transactional workspace writes.
- Module size remains `0x8000`; cache size remains 64 bytes; arena memory begins at `0x02293C60`.

## Runtime acceptance boundary

The unchanged Milestone 6D module, tutorial completion, standard arena exit, and cache clearing retain their accepted live evidence. A new natural representative capture for each Milestone 6E archetype remains required before the pull request can be marked ready and merged. The current runtime lacks the previously validated Linux DeSmuME bundle and playable battle save/state, so this requirement is not represented as complete.

## Required final commands

```bash
PYTHONPATH=src python -m pytest -q
python -m compileall -q src tests tools
python -m ruff check .
python -m mypy src/bakugan_ds
git diff --check
```
