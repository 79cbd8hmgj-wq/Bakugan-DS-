# G-Power Runtime Validation

Milestone 4B is complete. See [`runtime-gpower-tracing.md`](runtime-gpower-tracing.md)
and `analysis/runtime-observations/gpower_tutorial.json` for normalized evidence.

Confirmed:

- `0x14`-byte battle participant entries with G-Power fields at entry `+0x0C`;
- constructor `0x0223CFE8` and starting formula `core_g + mutable_modifier`;
- participant initializer `0x022696B4`;
- general mutable-modifier routine `0x0226A380`, clamped to combined G `0..990`;
- target addition `0x0223D288` and store `0x0223D28C`;
- controlled equations `230 + 180 = 410` and `190 + 100 = 290`;
- Gate/attribute helper `0x02065BF4` and runtime table `0x020A15AC`;
- Gate lookup `card_id * 6 + attribute_id`, scaled by ten;
- display tween `0x0223DDAC`, separate from the formula.

Probable:

- two `+30` callsites are progression-related because they also increment byte
  `+0xFD`; their exact level/experience/battle-count semantics remain unresolved.

Candidate:

- evolution selecting a separate identity/source-stat record;
- participant field `+0x0A` as an Ability Card, minigame, or temporary modifier.

The central G-Power pipeline is confirmed without promoting those unresolved
semantics.
