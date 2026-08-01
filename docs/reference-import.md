# Local Reference Import

The static scanner can use tables extracted from user-supplied reference PDFs as
known-value anchors. The source PDFs and generated catalog are local inputs and
must not be committed.

```bash
python -m bakugan_ds.analysis import-reference \
  --bakugan-csv /path/to/bakugan.csv \
  --gate-csv /path/to/gates.csv \
  --ability-csv /path/to/abilities.csv \
  --output references/generated/bakugan-guide.json
```

The importer normalizes line breaks, parses Bakugan statistics, stores Gate Card
attribute bonuses in Pyrus/Aquos/Subterra/Haos/Darkus/Ventus order, and stores
Ability Card names, types, and effects. The generated JSON is an analysis input,
not a statement that the ROM uses the same ordering or structure.

Do not promote an exact numeric match to a confirmed game table solely because
it matches a guide row. Require structural repetition, code references, a
controlled patch, or runtime observation.
