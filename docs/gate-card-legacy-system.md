# Legacy Gate Card System

## Supported build

This evidence applies only to **Bakugan: Battle Brawlers** for Nintendo DS, USA revision 0, profile `b6re_rev0`.

## Attribute-bonus table

The original Gate lookup is ARM9 helper `0x02065BF4`:

```text
raw_bonus = gate_table[card_id * 6 + attribute_id]
gate_bonus_g = raw_bonus * 10
target_total_g = base_snapshot_g + gate_bonus_g
```

Confirmed table properties:

| Property | Value |
|---|---:|
| Runtime base | `0x020A15AC` |
| End | `0x020A1AAA` |
| Global record count | 213 |
| Record stride | 6 bytes |
| Element encoding | unsigned byte |
| Display conversion | stored value × 10 G |
| Region SHA-256 | `6445b00c88445b736e2fa36dae804fce4e7595255403d56039d6da64db478fc4` |

The attribute indexes are:

```text
0 Pyrus
1 Aquos
2 Subterra
3 Haos
4 Darkus
5 Ventus
```

This order is confirmed from indexed entries `0–5` in the game's own `font/mes_Bakugan.mes` resource and selected table rows. It is not inferred from an external guide.

The table uses the complete global card-ID domain `0–212`. Global card metadata classifies IDs `0–103` as Gate-category entries and IDs `104–212` as Ability-category entries. ID `0` is a placeholder, leaving Gate Cards at IDs `1–103`. Rows outside the active Gate range remain part of the global indexed table and must not be assumed to be free solely because their six values are zero.

## Selected confirmed IDs

The game resource `font/mes_CardName.mes` contains 213 indexed names. Its message index matches the global card ID used by executable bounds checks and adjacent metadata tables.

Selected mappings committed as evidence:

| Global ID | Name | Class | Attribute values in displayed G |
|---:|---|---|---|
| 19 | Juggernoid | Gold | 80, 160, 70, 100, 70, 40 |
| 20 | Robotallion | Gold | 160, 110, 90, 120, 90, 40 |
| 22 | Serpenoid | Gold | 180, 60, 90, 140, 130, 50 |

Each mapping is cross-checked through the indexed in-game name, the executable table row, and the matching card graphic asset. The repository does not commit the complete 213-name catalog or complete Gate table.

## Battle-type selection

The original normal selector is fixed rather than random:

```text
battle_type_id = card_metadata[card_id * 4 + 2]
```

- Metadata table: `0x020A1258`
- Accessor: `0x02065C0C`
- Overlay-7 selector: `0x022433AC`
- Battle object storage: byte `+0x20`
- Six-way dispatcher: `0x0224183C`

Confirmed type IDs:

| ID | Type |
|---:|---|
| 0 | Scratch |
| 1 | Timing |
| 2 | Pop |
| 3 | Spin |
| 4 | Trace |
| 5 | Bound |

The normal path contains no RNG call or probability range. An explicit constructor argument or scripted battle-data byte `+0x07` can overwrite the fixed metadata result.

## Battle context

Confirmed fields suitable for future hook use include:

- global Gate card ID;
- attribute ID;
- compressed core G before mutable modifiers;
- mutable G modifier;
- base snapshot G;
- Gate bonus G;
- target total G;
- current combatant record pointer;
- selected battle type ID;
- battle-state byte.

Gate ownership, score, Ability Card usage, activation count, battle history, landing conditions, arena, difficulty, and human/AI identity remain excluded because canonical hook-safe fields have not been confirmed.

## Local inspection and export

A runtime-decompressed ARM9 image is required because the stored ARM9 is BLZ-compressed.

Inspect confirmed metadata without dumping the table:

```bash
bakugan-ds gate inspect work/bakugan \
  --runtime-arm9 work/runtime/arm9.bin \
  --metadata analysis/gates/legacy-table-metadata.json
```

Export the complete table to an ignored local report:

```bash
bakugan-ds gate export-legacy work/bakugan \
  work/reports/gates/legacy-table.json \
  --runtime-arm9 work/runtime/arm9.bin \
  --metadata analysis/gates/legacy-table-metadata.json
```

Generate the confirmed System 2.0 context subset:

```bash
bakugan-ds gate report-context work/bakugan \
  work/reports/gates/battle-context.json \
  --evidence analysis/gates/battle-context.json
```

Complete exports are local-only and ignored by Git.

## Copyright and evidence boundary

The repository may contain addresses, hashes, formulas, selected normalized examples, schemas, tests, and confidence labels. It does not contain ROMs, extracted executables, complete original tables, complete game-text catalogs, RAM dumps, saves, save states, screenshots, or raw debugger logs.
