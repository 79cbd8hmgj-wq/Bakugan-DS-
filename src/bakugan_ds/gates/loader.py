from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import StrEnum

from bakugan_ds.compression.lz10 import lz10_declared_size
from bakugan_ds.errors import WorkspaceError
from bakugan_ds.gates.authoring import (
    approved_juggernoid_record,
    legacy_passthrough_record,
)
from bakugan_ds.gates.record import (
    G2DT_MAGIC,
    G2DT_VERSION,
    GATE_RECORD_SIZE,
    TRAILER_SIZE,
    GateRecordV1,
    build_trailer,
    parse_record,
    parse_trailer,
    serialize_record,
)
from bakugan_ds.gates.storage import append_lz10_trailer

REFERENCE_FILE_ID = 2762
REFERENCE_RAW_SIZE = 2840
REFERENCE_RAW_SHA256 = "76a03522a5031762eb51d07b72a19331bc06a5b6dc0eab60e227a199466d4c4e"
REFERENCE_OVERLAY_SIZE = 0x721A0
REFERENCE_OVERLAY_SHA256 = "82904b4ec35e5eeae243324259e0c984ed8a0f3be2c4c5992d35d71249c194e1"
PRESERVED_BSS_SIZE = 0x640
SYSTEM2_MODULE_SIZE = 0x8000
EXPANDED_OVERLAY_SIZE = 0x7A7E0
CACHE_RECORD_SIZE = GATE_RECORD_SIZE
CACHE_SIZE = 0x40
ACTIVATION_COUNTER_COUNT = 12
ARM9_DECODED_SHA256 = "7cc01c584d2ecdd7166471f218f9fc3a58cf102b5fbe925287b9b95bae0c221e"
FS_FILE_SIZE = 72
ROM_ARCHIVE_ADDRESS = 0x020BFCB4
FS_INIT_FILE_ADDRESS = 0x0200A7B4
FS_OPEN_FILE_FAST_ADDRESS = 0x0200AA24
FS_CLOSE_FILE_ADDRESS = 0x0200AADC
FS_READ_FILE_ADDRESS = 0x0200AC30
FS_SEEK_FILE_ADDRESS = 0x0200AC40
CACHE_ADDRESS = 0x02293C20
GATE_LOADER_HOOK_ADDRESS = 0x0223D1CC
GATE_LOADER_RETURN_ADDRESS = 0x0223D1D0
GATE_CLEAR_HOOK_ADDRESS = 0x022424B4
GATE_CLEAR_RETURN_ADDRESS = 0x022424B8
INSTRUMENTED_ROM_SHA256 = "8177aff2ca1c6cfe401c4401ccfca954e17d1d546612628d0bc6e032b2d15388"
SYSTEM2_RUNTIME_MODULE_SHA256 = "d18dd0f7eba1279295e2314fa2d125030f0d382e577fad2fd9d712a623202ca6"
INITIALIZED_CACHE_SHA256 = "8ecef0a63d0ba161fe000ab688d847fe774bbbd4a5da412d281eb68d9d1b657d"
INVALIDATED_CACHE_SHA256 = "f5a5fd42d16a20302798ef6ed309979b43003d2320d9f0e8ea9831a92759fb4b"


@dataclass(frozen=True)
class CacheLayout:
    overlay_base: int = 0x02219440
    original_payload_size: int = REFERENCE_OVERLAY_SIZE
    preserved_bss_size: int = PRESERVED_BSS_SIZE
    module_start: int = 0x0228BC20
    module_size: int = SYSTEM2_MODULE_SIZE
    cache_start: int = CACHE_ADDRESS
    cache_size: int = CACHE_SIZE
    arena_low: int = 0x02293C60
    arena_high: int = 0x023E0000

    def validate(self) -> None:
        if (
            self.overlay_base + self.original_payload_size + self.preserved_bss_size
            != self.module_start
        ):
            raise WorkspaceError("System 2.0 module start does not follow preserved BSS")
        if self.module_start + self.module_size != self.cache_start:
            raise WorkspaceError("System 2.0 cache does not follow the module")
        if self.cache_start + self.cache_size != self.arena_low:
            raise WorkspaceError("battle arena low boundary does not follow the cache")
        if self.arena_low >= self.arena_high:
            raise WorkspaceError("battle arena has no remaining address space")
        if self.cache_size != CACHE_SIZE:
            raise WorkspaceError("Gate cache must be exactly 64 bytes")


@dataclass(frozen=True)
class NitroFsOperation:
    name: str
    function: int
    calling_convention: str
    arguments: str
    result: str
    confidence: str
    evidence: str

    def validate(self) -> None:
        if not self.name.strip():
            raise WorkspaceError("NitroFS operation name must be nonempty")
        if self.function <= 0:
            raise WorkspaceError("NitroFS operation function must be positive")
        for label, value in (
            ("calling convention", self.calling_convention),
            ("arguments", self.arguments),
            ("result", self.result),
            ("confidence", self.confidence),
            ("evidence", self.evidence),
        ):
            if not value.strip():
                raise WorkspaceError(f"NitroFS operation {label} must be nonempty")


@dataclass(frozen=True)
class LoaderEvidence:
    open_op: NitroFsOperation
    seek_op: NitroFsOperation
    read_op: NitroFsOperation
    close_op: NitroFsOperation
    file_id: int
    raw_size: int
    trailer_size: int
    stack_read_size: int
    cache_layout: CacheLayout
    initialization: str
    invalidation: str
    fallback: str

    def validate(self) -> None:
        for operation in (
            self.open_op,
            self.seek_op,
            self.read_op,
            self.close_op,
        ):
            operation.validate()
        if self.file_id != REFERENCE_FILE_ID:
            raise WorkspaceError("Gate trailer loader file ID must be 2762")
        if self.raw_size != REFERENCE_RAW_SIZE:
            raise WorkspaceError("Gate trailer carrier raw size must be 2840")
        if self.trailer_size != TRAILER_SIZE:
            raise WorkspaceError("Gate trailer size must be 4152")
        if self.stack_read_size != FS_FILE_SIZE:
            raise WorkspaceError("Gate loader stack read size must be 72")
        self.cache_layout.validate()
        for label, value in (
            ("initialization", self.initialization),
            ("invalidation", self.invalidation),
            ("fallback", self.fallback),
        ):
            if not value.strip():
                raise WorkspaceError(f"loader {label} must be nonempty")


def reference_loader_evidence() -> LoaderEvidence:
    return LoaderEvidence(
        open_op=NitroFsOperation(
            name="FS_OpenFileFast",
            function=FS_OPEN_FILE_FAST_ADDRESS,
            calling_convention=("ARM AAPCS: r0=FSFile*, r1=FSArchive*, r2=u32 file_id"),
            arguments=(
                "Initialize the 72-byte FSFile with FS_InitFile at 0x0200A7B4, "
                "then use ROM archive 0x020BFCB4 and file ID 2762."
            ),
            result=(
                "Returns BOOL in r0; success populates arc, own_id, top, bottom, "
                "and pos and marks the handle as a file."
            ),
            confidence="confirmed",
            evidence=(
                "Decoded ARM9 function 0x0200AA24 and a clean-boot runtime call "
                "returned 1 and populated an initialized FSFile."
            ),
        ),
        seek_op=NitroFsOperation(
            name="FS_SeekFile",
            function=FS_SEEK_FILE_ADDRESS,
            calling_convention=("ARM AAPCS: r0=FSFile*, r1=s32 offset, r2=FSSeekFileMode"),
            arguments=(
                "Modes 0, 1, and 2 are SET, CUR, and END. The loader seeks to "
                "raw offset 2840 with mode 0 before reading the appended trailer."
            ),
            result=(
                "Returns 1 for valid modes after clamping the absolute position "
                "to file top..bottom; an invalid mode returns 0 without updating pos."
            ),
            confidence="confirmed",
            evidence=(
                "Decoded ARM9 function 0x0200AC40 and a clean-boot SET/0 runtime "
                "call returned 1 with the expected position."
            ),
        ),
        read_op=NitroFsOperation(
            name="FS_ReadFile",
            function=FS_READ_FILE_ADDRESS,
            calling_convention=(
                "ARM AAPCS: r0=FSFile*, r1=destination, r2=s32 length; the wrapper "
                "passes async=0 to FSi_ReadFileCore at 0x0200A920."
            ),
            arguments=(
                "The handle is a 72-byte FSFile. Length is bounded to the remaining "
                "file range before the synchronous command is submitted."
            ),
            result=(
                "Returns the number of bytes read and advances pos by that amount; "
                "returns -1 when the synchronous wait fails."
            ),
            confidence="confirmed",
            evidence=(
                "A clean-boot stack FSFile at sp+4 requested 88040 bytes, returned "
                "88040, and advanced pos by exactly 88040 bytes."
            ),
        ),
        close_op=NitroFsOperation(
            name="FS_CloseFile",
            function=FS_CLOSE_FILE_ADDRESS,
            calling_convention="ARM AAPCS: r0=FSFile*",
            arguments="The handle must still be marked as an open file.",
            result=(
                "Returns BOOL in r0; success clears arc, restores command 14 "
                "(invalid), and clears the file and directory status bits."
            ),
            confidence="confirmed",
            evidence=(
                "Decoded ARM9 function 0x0200AADC and a clean-boot runtime call "
                "returned 1 and invalidated the same stack FSFile in place."
            ),
        ),
        file_id=REFERENCE_FILE_ID,
        raw_size=REFERENCE_RAW_SIZE,
        trailer_size=TRAILER_SIZE,
        stack_read_size=FS_FILE_SIZE,
        cache_layout=CacheLayout(),
        initialization=(
            "A single instrumented-ROM run returned at 0x0223D1D0 after loading "
            "Gate ID 21 into the 64-byte cache at 0x02293C20 with version 1, "
            "valid flag 1, and selected arena entry 0."
        ),
        invalidation=(
            "The same run returned at 0x022424B8 after battle completion with "
            "all 64 cache bytes zero and the valid flag cleared."
        ),
        fallback=(
            "Any file-operation failure or invalid G2DT header, geometry, ID, or "
            "checksum leaves the cache invalid and preserves legacy Gate behavior."
        ),
    )


def append_validated_trailer(
    original_raw: bytes,
    trailer: bytes,
    *,
    expected_raw_sha256: str | None = REFERENCE_RAW_SHA256,
) -> bytes:
    try:
        lz10_declared_size(original_raw)
    except Exception as exc:
        raise WorkspaceError(f"carrier payload is not valid LZ10: {exc}") from exc
    if len(original_raw) >= TRAILER_SIZE and original_raw[-TRAILER_SIZE:].startswith(G2DT_MAGIC):
        raise WorkspaceError("carrier already contains a G2DT trailer")
    if expected_raw_sha256 is not None:
        if len(original_raw) != REFERENCE_RAW_SIZE:
            raise WorkspaceError("reference carrier raw size does not match")
        actual = hashlib.sha256(original_raw).hexdigest()
        if actual != expected_raw_sha256:
            raise WorkspaceError("reference carrier SHA-256 does not match")
    parse_trailer(trailer)
    return append_lz10_trailer(
        original_raw,
        trailer,
        maximum_size=TRAILER_SIZE,
    )


def load_trailer_or_none(
    raw_with_optional_trailer: bytes,
    *,
    raw_size: int = REFERENCE_RAW_SIZE,
) -> tuple[GateRecordV1, ...] | None:
    if raw_size <= 0:
        raise WorkspaceError("raw carrier size must be positive")
    if len(raw_with_optional_trailer) == raw_size:
        return None
    if len(raw_with_optional_trailer) != raw_size + TRAILER_SIZE:
        return None
    trailer = raw_with_optional_trailer[raw_size:]
    try:
        _header, records = parse_trailer(trailer)
    except WorkspaceError:
        return None
    return records


def build_expanded_overlay(original_decoded: bytes, module: bytes) -> bytes:
    if len(original_decoded) != REFERENCE_OVERLAY_SIZE:
        raise WorkspaceError("original decoded overlay 7 size must be 0x721A0")
    if len(module) != SYSTEM2_MODULE_SIZE:
        raise WorkspaceError("System 2.0 module size must be 0x8000")
    expanded = original_decoded + (b"\0" * PRESERVED_BSS_SIZE) + module
    if len(expanded) != EXPANDED_OVERLAY_SIZE:
        raise WorkspaceError("expanded overlay 7 size must be 0x7A7E0")
    return expanded


def validate_overlay_expansion(
    original: bytes,
    expanded: bytes,
    layout: CacheLayout,
    *,
    expected_original_sha256: str | None = REFERENCE_OVERLAY_SHA256,
) -> None:
    layout.validate()
    if len(original) != layout.original_payload_size:
        raise WorkspaceError("original overlay payload size does not match layout")
    if expected_original_sha256 is not None:
        actual = hashlib.sha256(original).hexdigest()
        if actual != expected_original_sha256:
            raise WorkspaceError("original overlay SHA-256 does not match")
    expected_expanded_size = (
        layout.original_payload_size + layout.preserved_bss_size + layout.module_size
    )
    if len(expanded) != expected_expanded_size:
        raise WorkspaceError("expanded overlay size does not match layout")
    if expanded[: len(original)] != original:
        raise WorkspaceError("expanded overlay does not preserve original payload")
    bss_start = len(original)
    bss_end = bss_start + layout.preserved_bss_size
    if expanded[bss_start:bss_end] != b"\0" * layout.preserved_bss_size:
        raise WorkspaceError("expanded overlay preserved BSS bytes must be zero")
    if layout.overlay_base + len(expanded) != layout.cache_start:
        raise WorkspaceError("expanded overlay does not end at the cache start")


def build_cache(record: GateRecordV1, *, arena_entry: int) -> bytes:
    record.validate()
    if not 0 <= arena_entry < ACTIVATION_COUNTER_COUNT:
        raise WorkspaceError("arena entry must be between 0 and 11")
    cache = bytearray(CACHE_SIZE)
    cache[0:CACHE_RECORD_SIZE] = serialize_record(record)
    cache[0x28] = record.card_id
    cache[0x29] = G2DT_VERSION
    cache[0x2A] = 1
    cache[0x2B] = arena_entry
    return bytes(cache)


def parse_cache(cache: bytes) -> GateRecordV1 | None:
    if len(cache) != CACHE_SIZE:
        raise WorkspaceError("Gate cache must be exactly 64 bytes")
    if cache[0x2A] != 1 or cache[0x29] != G2DT_VERSION:
        return None
    if cache[0x2B] >= ACTIVATION_COUNTER_COUNT:
        return None
    if any(cache[0x3C:0x40]):
        return None
    try:
        record = parse_record(cache[:CACHE_RECORD_SIZE])
    except WorkspaceError:
        return None
    if cache[0x28] != record.card_id:
        return None
    return record


def invalidate_cache(cache: bytes) -> bytes:
    if len(cache) != CACHE_SIZE:
        raise WorkspaceError("Gate cache must be exactly 64 bytes")
    return b"\0" * CACHE_SIZE


GATE_LOADER_EXPECTED_BYTES = bytes.fromhex("b400c6e1")
GATE_LOADER_EXPECTED_SHA256 = "27aa2bf905753b3fb923bdedf4c5fc04a4a49644f762287418628bf307e480a3"
GATE_CLEAR_EXPECTED_BYTES = bytes.fromhex("b0091fe5")
GATE_CLEAR_EXPECTED_SHA256 = "81ed494e48704eb8e92898df48c8a785c3d4901700d6239a4b7678c1c961e66e"


class RuntimeLoaderFault(StrEnum):
    NONE = "none"
    OPEN_FAILURE = "open_failure"
    HEADER_SEEK_FAILURE = "header_seek_failure"
    SHORT_HEADER_READ = "short_header_read"
    BAD_MAGIC = "bad_magic"
    BAD_VERSION = "bad_version"
    BAD_GEOMETRY = "bad_geometry"
    BAD_HEADER_CRC = "bad_header_crc"
    INVALID_CARD_ID = "invalid_card_id"
    RECORD_SEEK_FAILURE = "record_seek_failure"
    SHORT_RECORD_READ = "short_record_read"
    SELECTED_RECORD_MISMATCH = "selected_record_mismatch"
    UNSUPPORTED_SEMANTICS = "unsupported_semantics"
    CLOSE_FAILURE = "close_failure"


def _approved_runtime_records() -> tuple[GateRecordV1, ...]:
    return tuple(
        approved_juggernoid_record() if card_id == 19 else legacy_passthrough_record(card_id)
        for card_id in range(1, 104)
    )


def approved_runtime_header() -> bytes:
    return build_trailer(_approved_runtime_records())[:32]


def runtime_record_is_supported(record: GateRecordV1) -> bool:
    if record.card_id == 19:
        return record == approved_juggernoid_record()
    return record == legacy_passthrough_record(record.card_id)


def simulate_runtime_load(
    raw_with_trailer: bytes,
    *,
    card_id: int,
    arena_entry: int = 0,
    fault: RuntimeLoaderFault = RuntimeLoaderFault.NONE,
) -> bytes:
    """Model the bounded live loader and its fail-closed cache policy."""

    empty = b"\0" * CACHE_SIZE
    if not isinstance(fault, RuntimeLoaderFault):
        raise WorkspaceError("runtime loader fault is invalid")
    if fault is RuntimeLoaderFault.OPEN_FAILURE:
        return empty
    if fault is RuntimeLoaderFault.HEADER_SEEK_FAILURE:
        return empty
    selected_id = card_id
    if fault is RuntimeLoaderFault.INVALID_CARD_ID:
        selected_id = 0
    if isinstance(selected_id, bool) or not isinstance(selected_id, int):
        return empty
    if not 1 <= selected_id <= 103:
        return empty
    if not 0 <= arena_entry < ACTIVATION_COUNTER_COUNT:
        return empty
    if len(raw_with_trailer) < REFERENCE_RAW_SIZE + 32:
        return empty

    header = bytearray(raw_with_trailer[REFERENCE_RAW_SIZE : REFERENCE_RAW_SIZE + 32])
    if fault is RuntimeLoaderFault.SHORT_HEADER_READ:
        header = header[:-1]
    elif fault is RuntimeLoaderFault.BAD_MAGIC:
        header[0] ^= 0xFF
    elif fault is RuntimeLoaderFault.BAD_VERSION:
        header[4] ^= 0x01
    elif fault is RuntimeLoaderFault.BAD_GEOMETRY:
        header[6] ^= 0x01
    elif fault is RuntimeLoaderFault.BAD_HEADER_CRC:
        header[24] ^= 0x01
    if bytes(header) != approved_runtime_header():
        return empty
    if fault is RuntimeLoaderFault.RECORD_SEEK_FAILURE:
        return empty

    record_offset = REFERENCE_RAW_SIZE + 32 + (selected_id - 1) * GATE_RECORD_SIZE
    record_data = bytearray(raw_with_trailer[record_offset : record_offset + GATE_RECORD_SIZE])
    if fault is RuntimeLoaderFault.SHORT_RECORD_READ:
        record_data = record_data[:-1]
    elif fault is RuntimeLoaderFault.SELECTED_RECORD_MISMATCH and record_data:
        record_data[0] = 1 if selected_id != 1 else 2
    elif fault is RuntimeLoaderFault.UNSUPPORTED_SEMANTICS and len(record_data) > 1:
        record_data[1] = 2
    if len(record_data) != GATE_RECORD_SIZE:
        return empty
    try:
        record = parse_record(bytes(record_data))
    except WorkspaceError:
        return empty
    if record.card_id != selected_id or not runtime_record_is_supported(record):
        return empty
    if fault is RuntimeLoaderFault.CLOSE_FAILURE:
        return empty
    return build_cache(record, arena_entry=arena_entry)
