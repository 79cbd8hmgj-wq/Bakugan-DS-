# G-Power Runtime Validation

The first runtime-validation pass is complete. See
[`runtime-gpower-tracing.md`](runtime-gpower-tracing.md) and
`analysis/runtime-observations/gpower_tutorial.json` for the normalized evidence.

Confirmed results:

- two adjacent 20-byte participant records;
- animated current, target total, base snapshot, and Gate attribute bonus fields;
- constructor at `0x0223CFE8`;
- initial base snapshot formed from source `+0x04 + +0x06`;
- Gate/attribute lookup result scaled by ten;
- target total formed as base snapshot plus Gate bonus;
- display tween at `0x0223DDAC`, separate from the formula.

The next controlled runtime matrix should vary level, evolution state, and one
Ability Card effect independently. Until then, the source components at `+0x04`
and `+0x06` remain probable base/growth inputs rather than fully named fields.
