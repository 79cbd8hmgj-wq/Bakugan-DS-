# G-Power Runtime Validation

Milestone 4B is complete. See [`runtime-gpower-tracing.md`](runtime-gpower-tracing.md)
and `analysis/runtime-observations/gpower_tutorial.json` for normalized evidence.

Confirmed results:

- adjacent 20-byte participant entries with G-Power fields at entry `+0x0C`;
- constructor at `0x0223CFE8`;
- initial base snapshot formed from source `+0x04 + +0x06`;
- source `+0x04` confirmed as the form's level-1/base G value;
- source `+0x06` confirmed as an additive progression component, with level growth the probable semantic role;
- all 38 reference forms share a +250 G level-1-to-max range;
- target addition at `0x0223D288` and store at `0x0223D28C`;
- two write-watchpoint hits at post-store PC `0x0223D290`;
- opponent operands `230 + 180 = 410`;
- player operands `190 + 100 = 290`;
- confirmed Gate/attribute helper at `0x02065BF4` and table at `0x020A15AC`;
- Gate lookup indexed as `card_id * 6 + attribute_id`, then scaled by ten;
- display tween at `0x0223DDAC`, separate from the formula.

The next controlled runtime matrix should capture a nonzero progression value,
an evolution transition, and one Ability Card effect independently. These are
follow-up semantic checks; the central G-Power pipeline is confirmed. The later
participant field `+0x0A` remains unresolved.
