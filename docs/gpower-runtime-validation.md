# G-Power Runtime Validation

Milestone 4B is complete. See [`runtime-gpower-tracing.md`](runtime-gpower-tracing.md)
and `analysis/runtime-observations/gpower_tutorial.json` for normalized evidence.

Confirmed results:

- adjacent 20-byte participant entries with G-Power fields at entry `+0x0C`;
- constructor at `0x0223CFE8`;
- initial base snapshot formed from source `+0x04 + +0x06`;
- target addition at `0x0223D288` and store at `0x0223D28C`;
- two write-watchpoint hits at post-store PC `0x0223D290`;
- opponent operands `230 + 180 = 410`;
- player operands `190 + 100 = 290`;
- display tween at `0x0223DDAC`, separate from the formula.

The ARM9 helper at `0x02065BF4` and its result-times-ten code path are recorded
as probable Gate/attribute lookup evidence. Its exact table and argument
semantics, plus the meanings of source fields `+0x04`, `+0x06`, and later
participant field `+0x0A`, require additional controlled comparisons.
