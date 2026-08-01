# DeSmuME Debug Bundle Builder Design

## Goal

Add a manually triggered GitHub Actions workflow that builds a Linux x86_64
DeSmuME command-line emulator with the ARM9 GDB stub enabled, packages the
runtime files needed by the ChatGPT execution sandbox, and exposes the bundle as
a downloadable workflow artifact.

The workflow exists only to obtain the debugger required for Milestone 4B. It
must not upload, download, embed, or process the Bakugan ROM, battery saves, save
states, extracted assets, or rebuilt ROMs.

## Selected approach

Use GitHub Actions on `ubuntu-24.04` and follow DeSmuME's official POSIX
Autotools build path:

1. Check out this repository.
2. Clone `TASEmulators/desmume` at a pinned source commit.
3. Install the same core Linux build dependencies used by DeSmuME's official
   workflow, plus tools for dependency collection and archive verification.
4. Run `autoreconf -i`.
5. Configure with `--enable-gdb-stub` and without unrelated optional features.
6. Compile and stage-install `desmume-cli`.
7. Package the executable, required non-system shared libraries, launch wrapper,
   diagnostics, source revision, license, and SHA-256 checksums.
8. Upload one compressed artifact.

This is preferred over building on the user's Catalina Mac because GitHub's
Linux runner matches the required artifact platform. It is preferred over
asking the user to locate a third-party binary because the source revision,
build flags, and resulting hashes remain auditable.

## Workflow interface

Create:

```text
.github/workflows/build-desmume-debug.yml
```

The workflow uses `workflow_dispatch` only. It accepts one optional string input:

- `desmume_ref`: DeSmuME commit, tag, or branch to build. The default is a
  tested pinned commit. Overriding it makes the run intentionally non-default
  and the selected ref is recorded in `BUILD_INFO.txt`.

The workflow requires only `contents: read` permission.

## Build configuration

Runner:

```text
ubuntu-24.04
```

Required configuration flag:

```text
--enable-gdb-stub
```

The official DeSmuME POSIX configuration exposes this flag and the official
project workflow builds the CLI through Autotools. The installed executable is
`desmume-cli`.

The workflow will disable or omit unrelated optional features where supported.
It will not enable Wi-Fi because Milestone 4B does not require networking.

## Artifact layout

Artifact name:

```text
desmume-linux-gdb-x86_64
```

Archive contents:

```text
desmume-debug/
├── desmume-cli
├── run-desmume-debug.sh
├── lib/
├── BUILD_INFO.txt
├── README.txt
├── desmume-help.txt
├── desmume-ldd.txt
├── SHA256SUMS
└── license.txt
```

`run-desmume-debug.sh` will:

- resolve its own directory;
- prepend the bundled `lib` directory to `LD_LIBRARY_PATH`;
- default SDL video and audio drivers to `dummy` when the caller has not set
  them;
- execute `desmume-cli` with the caller's arguments.

The expected Milestone 4B invocation is:

```bash
./run-desmume-debug.sh --arm9gdb=20000 /path/to/game.nds
```

## Shared-library policy

The workflow records the original `ldd` output and copies non-system runtime
libraries required by `desmume-cli` into `lib/`. It must not bundle the Linux
dynamic loader or glibc core libraries. The target sandbox is Debian 13 x86_64
with a newer glibc than Ubuntu 24.04, so the Ubuntu-built executable remains
compatible while bundled SDL and other optional libraries reduce host-package
dependence.

If a required library cannot be resolved, packaging fails rather than producing
a partial artifact.

## Verification

The workflow fails unless all checks pass:

1. `desmume-cli` exists and is executable.
2. `file` identifies an x86-64 Linux ELF executable.
3. The executable's help output can be captured.
4. Help output contains the ARM9 GDB option or the binary contains the expected
   GDB-stub option string.
5. `ldd` reports no `not found` dependency.
6. The wrapper starts the executable far enough to display help using bundled
   libraries and dummy SDL drivers.
7. `SHA256SUMS` verifies every packaged regular file other than itself.
8. The final archive is non-empty and uploaded with `if-no-files-found: error`.

No ROM-based emulation test runs in GitHub Actions.

## Artifact retention and handoff

Retain the workflow artifact for seven days. After a successful run, the user
will download the artifact from the workflow run and upload it to this chat.
The user will separately upload a compatible `.dsv` battery save or raw `.sav`
with accessible battles. The ROM already supplied in this conversation remains
local to the sandbox and is never sent to GitHub Actions.

## Security and legal boundaries

- No repository secrets are required.
- No write token permission is required.
- No untrusted pull-request code triggers the workflow automatically.
- The workflow fetches only the public DeSmuME source repository and Ubuntu
  packages.
- The DeSmuME GPL license is included in the artifact.
- The artifact contains emulator code only, not copyrighted game material.

## Failure handling

Every shell step uses strict mode. Clone, configuration, compilation,
installation, dependency collection, verification, packaging, and upload errors
stop the job. Diagnostic files are generated before packaging so a successful
artifact records exactly what was built; a failed build remains diagnosable
through the GitHub Actions log.

## Scope boundary

This design produces the runtime debugger dependency for Milestone 4B. It does
not itself locate the live G-Power value. After the artifact and game progress
save are uploaded, Milestone 4B resumes with emulator startup, ARM9 memory
searches, write watchpoints, call-path capture, and controlled confirmation of
the G-Power pipeline.
