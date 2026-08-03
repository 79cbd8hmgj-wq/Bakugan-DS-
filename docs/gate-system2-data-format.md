# Gate System 2.0 data format v1

`G2DT` is a deterministic little-endian trailer appended after the original raw LZ10 stream selected by the approved storage strategy. Native LZ10 decoding stops at the declared output size, so the original message resource remains unchanged.

## Header

The header is exactly 32 bytes: magic `G2DT`, version `1`, header size `32`, record size `40`, first card ID `1`, record count `103`, zero flags, payload size `4120`, payload CRC-32, header CRC-32, and a zero reserved word. The payload CRC covers all record bytes. The header CRC covers the complete header with the header-CRC field encoded as zero.

## Records

There are exactly 103 sorted records, one for every Gate Card ID `1..103`. Each record is exactly 40 bytes. Multi-byte integers are little-endian. Signed percentages use raw Q8.8 integers; runtime code must use integer arithmetic and explicit rounding. Six attribute modifiers and six battle-type weights are stored inline.

Version 1 reserves ID `255`, requires record and header flags to be zero, accepts target modes `0..6`, timing phases `0..11`, and uses `255` only as the no-preferred-battle-type sentinel. Arena IDs, landing zones, shot paths, and board positions are intentionally absent.

## Validation and fallback

The host serializer and future runtime loader reject wrong magic or version, wrong geometry, nonzero reserved values, unsupported IDs or enums, unsorted or duplicate card IDs, and either CRC mismatch. Rejection must invalidate the cache and preserve the original Gate calculation and fixed battle-type path.

## Authoring and diagnostics

`schemas/gate-system2-v1.schema.json` is the authoring contract. The binary serializer remains authoritative for cross-record ordering and CRC checks. Calculation traces are deterministic JSON objects containing each integer bonus component, the provisional and final battle type, validation status, and whether legacy fallback was used. Trace output is diagnostic only.
