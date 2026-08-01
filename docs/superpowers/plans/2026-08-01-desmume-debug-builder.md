# DeSmuME Debug Bundle Builder Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add and verify a manual GitHub Actions workflow that builds a Linux x86_64 DeSmuME CLI with ARM9 GDB-stub support and packages a self-contained debugger bundle for Milestone 4B.

**Architecture:** The repository contains one policy test, one workflow, and one handoff document. The workflow clones a pinned DeSmuME revision, follows its supported POSIX Autotools build path, stages `desmume-cli`, bundles non-glibc runtime libraries, generates diagnostics and checksums, verifies the GDB option, and uploads one seven-day artifact without ever handling ROM or save data.

**Tech Stack:** GitHub Actions, Ubuntu 24.04, Bash, GNU Autotools, Make, Python 3.11, pytest.

## Global Constraints

- Workflow trigger is `workflow_dispatch` only.
- Workflow permission is exactly `contents: read`.
- Default DeSmuME revision is `84e445159ccf2fd7900748094518eb1e88bdc7d0`.
- Runner is `ubuntu-24.04`.
- Configuration includes `--enable-gdb-stub` and does not enable Wi-Fi.
- Artifact is named `desmume-linux-gdb-x86_64` and retained for seven days.
- No ROM, save, save state, extracted asset, rebuilt ROM, or repository secret is read or uploaded.
- The artifact contains `desmume-cli`, `run-desmume-debug.sh`, `lib/`, `BUILD_INFO.txt`, `README.txt`, `desmume-help.txt`, `desmume-ldd.txt`, `SHA256SUMS`, and `license.txt`.
- Packaging fails on an unresolved shared library, absent GDB option, failed wrapper help invocation, checksum failure, or empty archive.

---

### Task 1: Lock the Workflow Contract with Tests

**Files:**
- Create: `tests/unit/test_desmume_debug_workflow.py`

**Interfaces:**
- Consumes: repository text files under `.github/workflows/` and `docs/`.
- Produces: a pytest contract that rejects unsafe triggers, missing permissions, unpinned source defaults, missing verification, or game-data handling.

- [ ] **Step 1: Write the failing workflow-policy tests**

```python
from pathlib import Path

WORKFLOW = Path(".github/workflows/build-desmume-debug.yml")


def test_desmume_workflow_is_manual_and_read_only() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "workflow_dispatch:" in text
    assert "pull_request:" not in text
    assert "push:" not in text
    assert "permissions:\n  contents: read" in text


def test_desmume_workflow_pins_and_verifies_debug_build() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    for required in (
        "84e445159ccf2fd7900748094518eb1e88bdc7d0",
        "ubuntu-24.04",
        "--enable-gdb-stub",
        "desmume-cli",
        "arm9gdb",
        "ldd",
        "SHA256SUMS",
        "retention-days: 7",
        "if-no-files-found: error",
    ):
        assert required in text


def test_desmume_workflow_never_handles_game_data() -> None:
    text = WORKFLOW.read_text(encoding="utf-8").lower()
    for forbidden in ("*.nds", "*.sav", "*.dsv", "save state", "bakugan - battle brawlers"):
        assert forbidden not in text
```

- [ ] **Step 2: Run the focused tests and confirm the expected failure**

Run:

```bash
python -m pytest tests/unit/test_desmume_debug_workflow.py -v
```

Expected: failure because `.github/workflows/build-desmume-debug.yml` does not exist.

- [ ] **Step 3: Commit the red test**

```bash
git add tests/unit/test_desmume_debug_workflow.py
git commit -m "test: define DeSmuME debug workflow contract"
```

---

### Task 2: Build and Package the DeSmuME Debug Bundle

**Files:**
- Create: `.github/workflows/build-desmume-debug.yml`

**Interfaces:**
- Consumes: optional `workflow_dispatch.inputs.desmume_ref` string.
- Produces: GitHub Actions artifact `desmume-linux-gdb-x86_64` containing `desmume-linux-gdb-x86_64.tar.xz`.

- [ ] **Step 1: Add the manual workflow declaration**

Use this exact interface:

```yaml
name: Build DeSmuME Debug Bundle

on:
  workflow_dispatch:
    inputs:
      desmume_ref:
        description: DeSmuME commit, tag, or branch
        required: false
        default: 84e445159ccf2fd7900748094518eb1e88bdc7d0
        type: string

permissions:
  contents: read
```

- [ ] **Step 2: Add dependency installation and the pinned source checkout**

The job must use `ubuntu-24.04`, `timeout-minutes: 45`, strict Bash mode, and install:

```text
autoconf automake build-essential file git libasound2-dev libglib2.0-dev
libglu1-mesa-dev libgtk2.0-dev libpcap-dev libsdl2-dev libtool
libx11-dev libzzip-dev make pax-utils pkg-config xz-utils zlib1g-dev
```

Clone `https://github.com/TASEmulators/desmume.git`, checkout the requested ref, and record the resolved commit with `git rev-parse HEAD`.

- [ ] **Step 3: Configure and compile through the official POSIX path**

Run from `source/desmume/src/frontend/posix`:

```bash
autoreconf -i
./configure --prefix=/usr --enable-gdb-stub
make -j"$(nproc)"
```

Locate `cli/desmume-cli`, require it to be executable, and copy it into `bundle/desmume-debug/desmume-cli`.

- [ ] **Step 4: Add the headless launcher**

Create `run-desmume-debug.sh` with:

```bash
#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export LD_LIBRARY_PATH="$ROOT/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export SDL_VIDEODRIVER="${SDL_VIDEODRIVER:-dummy}"
export SDL_AUDIODRIVER="${SDL_AUDIODRIVER:-dummy}"
exec "$ROOT/desmume-cli" "$@"
```

Mark both executable files with mode `0755`.

- [ ] **Step 5: Record and bundle runtime dependencies**

Capture `ldd` output in `desmume-ldd.txt`, fail if it contains `not found`, and copy every resolved dependency into `lib/` except the dynamic loader and these glibc core libraries:

```text
libc.so.6 libm.so.6 libdl.so.2 libpthread.so.0 librt.so.1 libresolv.so.2
```

Use `cp -L` and preserve each dependency's runtime basename.

- [ ] **Step 6: Add provenance, instructions, license, and GDB verification**

`BUILD_INFO.txt` must include the requested ref, resolved commit, runner OS, compiler version, configure command, UTC build timestamp, and repository workflow commit.

`README.txt` must include the invocation:

```bash
./run-desmume-debug.sh --arm9gdb=20000 /path/to/game.nds
```

Copy `source/desmume/COPYING` to `license.txt`.

Capture help output without allowing a nonzero help exit status to abort the job. Require either the help output or `strings desmume-cli` to contain `arm9gdb`.

- [ ] **Step 7: Generate and verify checksums and archive**

From `bundle/desmume-debug`:

```bash
find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum > SHA256SUMS
sha256sum -c SHA256SUMS
```

Run the wrapper with `--help` and require captured output. Create:

```text
bundle/desmume-linux-gdb-x86_64.tar.xz
```

Require the archive to be non-empty and list its contents in the Actions log.

- [ ] **Step 8: Upload the artifact**

Use `actions/upload-artifact@v4` with:

```yaml
name: desmume-linux-gdb-x86_64
path: bundle/desmume-linux-gdb-x86_64.tar.xz
retention-days: 7
if-no-files-found: error
```

- [ ] **Step 9: Run the focused tests**

Run:

```bash
python -m pytest tests/unit/test_desmume_debug_workflow.py -v
```

Expected: all workflow-contract tests pass.

- [ ] **Step 10: Commit the workflow**

```bash
git add .github/workflows/build-desmume-debug.yml tests/unit/test_desmume_debug_workflow.py
git commit -m "ci: build DeSmuME ARM9 debug bundle"
```

---

### Task 3: Document the Artifact Handoff

**Files:**
- Create: `docs/desmume-debug-bundle.md`
- Modify: `README.md`
- Modify: `tests/unit/test_desmume_debug_workflow.py`

**Interfaces:**
- Consumes: successful workflow artifact.
- Produces: exact user steps for running the workflow, downloading the artifact, and uploading the emulator bundle and save file for Milestone 4B.

- [ ] **Step 1: Extend the tests for handoff documentation**

```python
def test_desmume_handoff_documents_required_steps() -> None:
    text = Path("docs/desmume-debug-bundle.md").read_text(encoding="utf-8")
    for required in (
        "Build DeSmuME Debug Bundle",
        "Run workflow",
        "desmume-linux-gdb-x86_64",
        "run-desmume-debug.sh --arm9gdb=20000",
        ".dsv",
        ".sav",
        "Do not upload the ROM to GitHub",
    ):
        assert required in text
```

- [ ] **Step 2: Write the handoff document**

Document:

1. Open the repository's **Actions** tab.
2. Select **Build DeSmuME Debug Bundle**.
3. Choose **Run workflow** and keep the default source revision.
4. Download `desmume-linux-gdb-x86_64` after the run succeeds.
5. Upload the downloaded artifact to this chat.
6. Separately upload a `.dsv` or raw `.sav` with accessible battles.
7. Do not upload the ROM to GitHub; the ROM remains in this conversation only.

Also document local archive extraction and the expected debugger command.

- [ ] **Step 3: Add a concise README link**

Add a `## Build the runtime debugger` section linking to `docs/desmume-debug-bundle.md` and explaining that this dependency is needed only for Milestone 4B.

- [ ] **Step 4: Run tests and compile checks**

Run:

```bash
python -m pytest tests/unit/test_desmume_debug_workflow.py -v
python -m compileall -q tests
git diff --check
```

Expected: all commands pass.

- [ ] **Step 5: Commit the documentation**

```bash
git add README.md docs/desmume-debug-bundle.md tests/unit/test_desmume_debug_workflow.py
git commit -m "docs: add DeSmuME debugger artifact handoff"
```

---

### Task 4: Publish and Validate the Builder

**Files:**
- No new source files.

**Interfaces:**
- Consumes: completed feature branch.
- Produces: reviewable PR, then one successful manual workflow run and downloadable artifact after merge.

- [ ] **Step 1: Run repository verification**

```bash
python -m pytest tests/unit/test_desmume_debug_workflow.py -v
python -m compileall -q tests
git diff --check
git ls-files | grep -E '\.(nds|sav|dsv|ds[0-9]|bin)$' && exit 1 || true
```

- [ ] **Step 2: Open the implementation pull request**

PR title:

```text
Add DeSmuME ARM9 debug bundle builder
```

The body must state that the workflow is manual-only, read-only, ROM-free, pinned by default, and intended solely to unblock Milestone 4B.

- [ ] **Step 3: Merge the reviewed PR**

The workflow must exist on the default branch before `workflow_dispatch` can be used.

- [ ] **Step 4: Trigger the default manual run**

In GitHub Actions, run **Build DeSmuME Debug Bundle** with the default `desmume_ref`.

- [ ] **Step 5: Verify the completed run**

Require:

- job conclusion `success`;
- artifact named `desmume-linux-gdb-x86_64`;
- non-expired artifact containing a non-empty `.tar.xz`;
- logs showing `--enable-gdb-stub`, no missing libraries, successful wrapper help, and successful checksum verification.

- [ ] **Step 6: Download and inspect the artifact**

Verify the archive contains every path required by the design and that `SHA256SUMS` passes after extraction. Upload the artifact to the active execution environment for Milestone 4B.
