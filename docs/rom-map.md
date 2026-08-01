# Verified ROM Map

## Supported image

- Profile: `b6re_rev0`
- Internal title: `BAKUGAN W`
- Game code: `B6RE`
- Revision: `0`
- Size: `134217728` bytes
- SHA-256: `7b8f0ac330d3bf7cef2acb8e4e9318e797e1f2e051f1c2f1c87d998ef8d2558b`

## Executables

| Component | ROM offset | RAM address | Size |
|---|---:|---:|---:|
| ARM9 | `0x00004000` | `0x02000000` | `448192` |
| ARM7 | `0x000D8A00` | `0x02380000` | `160048` |

## NitroFS

| Structure | ROM offset | Size |
|---|---:|---:|
| FNT | `0x000FFC00` | `212348` |
| FAT | `0x00133A00` | `88040` |

The FAT contains `11005` records. The FNT names `10996` files in `95`
directories. FAT entries `0` through `8` are the nine ARM9 overlay payloads and
therefore do not have NitroFS filenames.

## Overlays

The ARM9 overlay table begins at `0x00071800`, is `288` bytes long, and contains
nine entries. The ARM7 overlay table is empty. All nine ARM9 overlays declare
the load address `0x02219440`, so runtime addresses must always be paired with
an overlay ID and component-relative offset.

Overlay 7 is the largest known executable overlay:

- File ID: `7`
- RAM size: `467360` bytes
- BSS size: `1600` bytes
- Compressed payload size: `255740` bytes

These facts do not establish that overlay 7 is the battle engine. That remains
a candidate hypothesis until runtime call paths and controlled patches verify it.
