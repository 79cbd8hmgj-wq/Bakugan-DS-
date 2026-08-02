# G-Power Rebalance — Progression 50%

## Scope

This is the first gameplay patch built on the runtime-confirmed G-Power pipeline.
It changes only the additive progression component used when the battle record is
initialized. Form base G, Gate Card bonuses, attributes, Ability Card effects,
and the display animation remain unchanged.

Original initialization:

```text
initial_base_G = base_G + progression_G
```

Patched initialization:

```text
initial_base_G = base_G + (progression_G >> 1)
```

The ARM logical right shift implements an integer **50%** scale. Odd progression
values round down by one before being halved.

## Guarded instructions

Overlay 7 loads at `0x02219440`.

| Combatant | Runtime address | Overlay offset | Original | Replacement |
| --- | ---: | ---: | --- | --- |
| First | `0x0223D0F8` | `0x00023CB8` | `add r1, r2, r1` | `add r1, r2, r1, lsr #1` |
| Second | `0x0223D108` | `0x00023CC8` | `add r0, r1, r0` | `add r0, r1, r0, lsr #1` |

The patch file verifies the exact original instruction bytes before changing
either location. A stale or different ROM/overlay fails closed.

## Expected balance effect

The published roster uses a universal `+250 G` span from level 1 to maximum
level. Under this patch that progression span becomes `+125 G`:

| Example | Original level 1 / max | Patched level 1 / max |
| --- | ---: | ---: |
| Serpenoid | `190 / 440` | `190 / 315` |
| Dragonoid | `400 / 650` | `400 / 525` |
| Omega Leonidas | `650 / 900` | `650 / 775` |

Level-1 G is unchanged because the progression component is zero there. The
absolute effect grows with progression, so the patch primarily reduces late-game
level scaling.

## Deliberate limitations

- Gate Card bonuses are unchanged.
- Attribute lookup and conversion are unchanged.
- Ability Card and minigame modifiers are unchanged.
- form-base and evolution gaps are unchanged.
- This patch does not yet give weak forms individual growth curves.

The next balance phase should identify the form-selection/evolution data and
compress excessive evolved-form base gaps or introduce per-form growth profiles.

## Apply and rebuild

Starting from a clean extracted workspace:

```bash
bakugan-ds patch workspace patches/gpower-progression-50.json
bakugan-ds rebuild \
  "Bakugan - Battle Brawlers (USA) (En,Fr).nds" \
  workspace \
  Bakugan-GPower-Progression-50.nds
```

The rebuild stores changed overlay 7 uncompressed, clears its compression
metadata, repacks FAT payloads, and preserves the original ROM size.

## Verification performed

- exact `B6RE` revision 0 source ROM SHA-256 validated;
- both original overlay instructions matched their guarded bytes;
- replacements decode as ARM `ADD` with `LSR #1`;
- changed overlay 7 remained exactly 467,360 bytes;
- rebuilt ROM remained exactly 134,217,728 bytes;
- patched ROM reached the title screen in DeSmuME.
