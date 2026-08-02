# Milestone 5: First G-Power Rebalance Patch

## Goal

Ship the first reproducible gameplay modification using only runtime-confirmed
G-Power inputs and guarded overlay instructions.

## Baseline patch

Reduce the additive progression component to 50% for both combatants while
preserving form base G and every later Gate/attribute calculation.

## Tasks

1. Add a failing artifact test for both runtime instruction locations.
2. Add a guarded patch document targeting overlay 7 offsets `0x23CB8` and
   `0x23CC8`.
3. Verify replacement words encode ARM `ADD` with `LSR #1`.
4. Document expected roster-level effects and explicit limitations.
5. Apply the patch to the exact decoded overlay 7.
6. Rebuild the exact ROM with overlay 7 stored uncompressed.
7. Verify ROM size, overlay metadata, patched bytes, and boot behavior.
8. Publish the patch and evidence tests as a pull request.

## Evidence boundary

This milestone does not claim individual growth curves, evolution-base
compression, or Gate Card tuning. Those require separate data mapping and
playtesting.
