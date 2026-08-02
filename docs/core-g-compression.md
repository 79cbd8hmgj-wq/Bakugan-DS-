# Core G-Power Compression

This is the first conservative gameplay balance patch for the exact `B6RE` USA revision 0 ROM. It preserves **core G-Power at or below 400** and compresses only the amount above 400:

```text
compressed_core = core                              when core <= 400
compressed_core = 200 + floor(core / 2)             when core > 400
base_snapshot = compressed_core + mutable_modifier
target_total = base_snapshot + gate_bonus
```

Examples: `400 -> 400`, `440 -> 420`, `500 -> 450`, `650 -> 525`, `670 -> 535`, and `900 -> 650`.

## Scope and safety boundary

The constructor rewrite applies identically to **both combatants**. It changes only the core-G halfword before later contributions are added. It does not change the persistent roster table, the general mutable G modifier, field G-Power pickups, or Gate Card and attribute bonuses. Persistent save values remain unchanged.

The patch is an in-place guarded replacement with **no code cave**, no branch hook, no overlay growth, and no BSS movement. Overlay 7 remains exactly 467,360 decoded bytes.

## Guarded regions

| Runtime address | Overlay offset | Purpose |
| --- | ---: | --- |
| `0x0223D058` | `0x23C18` | Replace dead `mov r7, #12` with `mov r7, #200` |
| `0x0223D0F0` | `0x23CB0` | Compress both core-G inputs and preserve later stores |
| `0x0223D1B8` | `0x23D78` | Replace `mov r8, r11` with direct `mov r8, #10` |

Every region includes exact expected original bytes. The patch fails closed if the workspace is stale or belongs to another ROM revision.

## Apply and rebuild

```bash
bakugan-ds extract "/path/to/Bakugan - Battle Brawlers (USA) (En,Fr).nds" work/core-g-400
bakugan-ds patch work/core-g-400 patches/core-g-compression-400.json
bakugan-ds rebuild \
  "/path/to/Bakugan - Battle Brawlers (USA) (En,Fr).nds" \
  work/core-g-400 \
  output/Bakugan-Core-G-400.nds
```

For rollback, create a fresh workspace or restore `modified/overlays/overlay_007.bin` from `original/decoded/overlays/overlay_007.bin`. Do not reverse-patch an uncertain workspace.

## Verification evidence

The exact replacement block was executed through DeSmuME's ARM9 GDB stub with controlled source records and readback-verified memory writes:

- low inputs remained unchanged: opponent `230`, player `190`;
- high inputs followed the same curve for both combatants: `650 -> 525`;
- a `+30` mutable modifier remained separate: `525 + 30 = 555`;
- the unchanged Gate path still produced `525 + 100 = 625` and `555 + 100 = 655`;
- all Gate fields were zero-initialized before the later lookup.

A separate clean, no-debugger boot of the rebuilt ROM created a new profile and reached the first battle. Serpenoid displayed `190 G` on the selection screen, and no overlay-load failure was observed. This smoke test does **not** claim that a full battle was completed. Normalized evidence is stored in `analysis/runtime-observations/core_g_compression_400.json`; ROM bytes, RAM dumps, screenshots, and save data remain local.
