# Player Level and Experience Storage

## Confirmed packed format

The four-byte auxiliary record returned by ARM9 helper `0x02023248` is located at:

```text
global_roster + 0x88 + identity_index * 4
```

Its first halfword packs level and experience:

```text
level_index = packed & 0x000F
experience  = packed >> 4
packed      = (experience << 4) | level_index
displayed_level = level_index + 1
```

Bits `0–3` therefore store a **zero-based level**, while bits `4–15` store up to
`4095` experience. The second halfword packs five field stats using three bits
per stat; the UI unpacker begins at `0x0205B124`.

## Experience Boost

The green field Experience Boost handler begins at `0x0222B600`. Its primary
packed-halfword update is at `0x0222B668–0x0222B6A0`; an equivalent update is at
`0x0222CB98–0x0222CBC8`.

```text
if current_xp < 4055:
    packed = ((current_xp + 40) << 4) | level_index
```

The pickup awards **40 XP** and preserves the level nibble. `4055` is the
pre-add guard, not the stored cap. Because the award is 40, that guard keeps the
result within the 12-bit maximum of `4095`.

## Normal battle XP

The battle-result state function begins at `0x0223F918`. Its XP update at
`0x0224224C–0x02242280` performs:

```text
if current_xp <= 4095 - reward_xp:
    packed = ((current_xp + reward_xp) << 4) | level_index
```

This path preserves the level nibble and prevents overflow. It accumulates XP
but does **not** promote the Bakugan to the next level. The state exits afterward,
so threshold comparison, level increment, and persistent G growth occur in a
later scene that remains unidentified.

## Runtime anchor

For tutorial Pyrus Serpenoid (`identity_index = 132`):

| Field | Runtime address/value |
| --- | --- |
| Persistent packed level/XP | `0x020D4688` |
| Persistent G byte | `0x020D48D4` |
| Battle-copy packed level/XP | `0x022E24EC` |
| Forced packed value | `0xFD70` |
| Decoded level | index `0`, displayed level `1` |
| Decoded XP | `4055` |
| Persistent G | `190` |

The forced value was reproduced in the persistent and battle-copy records while
G remained 190. Skipping the tutorial did not run a normal reward or persistent
level/G write, so it cannot identify the promotion routine.

## Modding boundary

The XP format and accumulation arithmetic are confirmed. A safe growth rebalance
still requires the later promotion routine that:

1. compares XP against the next-level threshold;
2. increments the low level nibble;
3. raises the persistent G byte; and
4. serializes the auxiliary record.

No gameplay patch is included in this milestone.
