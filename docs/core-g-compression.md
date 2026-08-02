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

### Exact overlay and rebuild

The three guards match the confirmed decoded overlay 7. The rebuilt ROM remains
134,217,728 bytes, reparses without layout mismatches, and stores overlay 7
uncompressed at its unchanged 467,360-byte RAM size with the original 1,600-byte
BSS. Exactly 41 instruction bytes change inside the declared regions; all other
11,004 FAT payloads remain byte-identical.

### Controlled ARM9 execution

The exact replacement block was executed through DeSmuME's ARM9 GDB stub with
controlled source records and readback-verified memory writes:

- low inputs remained unchanged: opponent `230`, player `190`;
- both `650 G` core inputs compressed symmetrically to `525 G`;
- a separate `+30 G` mutable modifier remained fully additive, producing `555 G`;
- the unchanged Gate path produced `525 + 100 = 625` and `555 + 100 = 655`;
- Gate fields remained zero-initialized until the later Gate lookup/store path.

### Clean full-game smoke test

A separate clean boot used the rebuilt ROM and created a new profile without
loading any save state, so overlay 7 came from the patched ROM rather than stale
saved executable RAM. The run:

1. reached the title screen and created a Pyrus profile;
2. entered the first tutorial battle;
3. selected Serpenoid at its unchanged `190 G`;
4. completed two throws and stood on the required Gate Card;
5. displayed the original controlled Gate totals, opponent `230 + 180 = 410`
   and player `190 + 100 = 290`;
6. entered the attribute-rub minigame;
7. used the game's built-in tutorial-skip option after a failed rub retry;
8. displayed the tutorial-completion dialogue;
9. returned to the surrounding park story and accepted another input.

This smoke test proves boot, battle entry, normal low-G arithmetic, throw/stand,
Gate calculation, tutorial exit, overlay stability, and return to responsive
story state. It does not claim a natural win of the rub minigame.

Normalized evidence is stored in
`analysis/runtime-observations/core_g_compression_validation.json`. The rebuilt
ROM, extracted overlay, RAM data, save states, screenshots, and debugger captures
remain local and are not committed.
