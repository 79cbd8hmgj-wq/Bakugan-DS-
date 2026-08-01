# DeSmuME Debug Bundle

Milestone 4B requires a Linux x86_64 DeSmuME command-line build with the ARM9
GDB stub enabled. The repository provides a manual GitHub Actions workflow named
**Build DeSmuME Debug Bundle** to create that dependency without sending the ROM
or save data to GitHub.

## Build the artifact

1. Open the repository on GitHub.
2. Select the **Actions** tab.
3. Select **Build DeSmuME Debug Bundle** in the workflow list.
4. Select **Run workflow**.
5. Keep the default DeSmuME source revision unless a different revision is
   intentionally being tested.
6. Wait for the single build job to complete successfully.
7. Download the artifact named `desmume-linux-gdb-x86_64` from the workflow run.

The downloaded GitHub artifact contains
`desmume-linux-gdb-x86_64.tar.xz`. Extract it before use:

```bash
unzip desmume-linux-gdb-x86_64.zip
mkdir desmume-linux-gdb-x86_64
tar -xJf desmume-linux-gdb-x86_64.tar.xz -C desmume-linux-gdb-x86_64
cd desmume-linux-gdb-x86_64/desmume-debug
sha256sum -c SHA256SUMS
```

## Start the ARM9 debugger

The expected Milestone 4B invocation is:

```bash
./run-desmume-debug.sh --arm9gdb=20000 /path/to/game.nds
```

The launcher uses bundled shared libraries and defaults SDL video and audio to
headless dummy drivers. The ARM9 GDB remote server listens on TCP port `20000`.

## Return the files for Milestone 4B

Upload the downloaded GitHub artifact to the active ChatGPT conversation. Also
upload one game-progress file with accessible battles:

- Preferred: a DeSmuME `.dsv` battery save.
- Acceptable: a raw `.sav` file.

A DeSmuME numbered state may be version-specific, so a battery save is safer.
Record any known Bakugan, level, evolution state, Gate Card, Ability Card, and
displayed G-Power values that can be reproduced from the save.

**Do not upload the ROM to GitHub.** The legally obtained ROM remains local to
the active analysis environment and is never part of the workflow artifact.

## Artifact contents

The extracted `desmume-debug/` directory contains:

```text
desmume-cli
run-desmume-debug.sh
lib/
BUILD_INFO.txt
README.txt
desmume-help.txt
desmume-ldd.txt
desmume-file.txt
SHA256SUMS
license.txt
```

`BUILD_INFO.txt` records the requested and resolved DeSmuME revisions, compiler,
configure command, workflow commit, and build timestamp. `desmume-ldd.txt`
records the original runtime dependency resolution. `SHA256SUMS` protects every
packaged regular file except itself.

## Scope

This artifact supplies the emulator and ARM9 debug transport only. Milestone 4B
still requires a live RAM search, a write watchpoint on the changing G-Power
value, call-path capture, and controlled confirmation before any candidate
function is labeled confirmed.
