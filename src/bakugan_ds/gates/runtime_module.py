from __future__ import annotations

import hashlib
import itertools
import struct
from dataclasses import dataclass

from bakugan_ds.errors import WorkspaceError
from bakugan_ds.gates.arm32 import (
    Condition,
    DataOpcode,
    Register,
    ShiftType,
    encode_branch,
    encode_bx,
    encode_data_processing_immediate,
    encode_data_processing_register,
    encode_data_processing_shifted_register,
    encode_halfword_transfer,
    encode_literal_load,
    encode_load_store,
    encode_mul,
    encode_pop,
    encode_push,
)
from bakugan_ds.gates.authoring import approved_juggernoid_record
from bakugan_ds.gates.history import WEIGHTED_SELECTOR_ADDRESS
from bakugan_ds.gates.hooks import (
    HookPurpose,
    validate_hook_source_bytes,
)
from bakugan_ds.gates.loader import (
    CACHE_ADDRESS,
    FS_CLOSE_FILE_ADDRESS,
    FS_INIT_FILE_ADDRESS,
    FS_OPEN_FILE_FAST_ADDRESS,
    FS_READ_FILE_ADDRESS,
    FS_SEEK_FILE_ADDRESS,
    GATE_CLEAR_EXPECTED_BYTES,
    GATE_CLEAR_EXPECTED_SHA256,
    GATE_CLEAR_HOOK_ADDRESS,
    GATE_CLEAR_RETURN_ADDRESS,
    GATE_LOADER_EXPECTED_BYTES,
    GATE_LOADER_EXPECTED_SHA256,
    GATE_LOADER_HOOK_ADDRESS,
    GATE_LOADER_RETURN_ADDRESS,
    REFERENCE_FILE_ID,
    REFERENCE_RAW_SIZE,
    ROM_ARCHIVE_ADDRESS,
    SYSTEM2_MODULE_SIZE,
    approved_runtime_header,
)
from bakugan_ds.gates.record import (
    GATE_RECORD_BATTLE_WEIGHTS_OFFSET,
    GateConditionId,
    GateEffectId,
    GateTargetMode,
    serialize_record,
)
from bakugan_ds.gates.system2 import (
    CORE_G_COMPRESSION_BASE,
    CORE_G_COMPRESSION_THRESHOLD,
    Q8_8_DENOMINATOR,
)

MODULE_BASE = 0x0228BC20
MODULE_END = MODULE_BASE + SYSTEM2_MODULE_SIZE
OVERLAY_BASE = 0x02219440
NOP = 0xE1A00000


@dataclass(frozen=True)
class RuntimeSymbol:
    name: str
    address: int
    size: int
    code_size: int
    branch_targets: tuple[int, ...]
    purpose: str

    def validate(self) -> None:
        if not self.name.strip() or not self.purpose.strip():
            raise WorkspaceError("runtime symbol name and purpose must be nonempty")
        if self.address < MODULE_BASE or self.address + self.size > MODULE_END:
            raise WorkspaceError(f"runtime symbol {self.name} is outside module")
        if self.address & 3 or self.size <= 0 or self.size & 3:
            raise WorkspaceError(f"runtime symbol {self.name} must be word aligned")
        if self.code_size <= 0 or self.code_size > self.size or self.code_size & 3:
            raise WorkspaceError(f"runtime symbol {self.name} has invalid executable-code size")
        for target in self.branch_targets:
            if target & 3:
                raise WorkspaceError(f"runtime symbol {self.name} has an unaligned branch target")
            if CACHE_ADDRESS <= target < 0x02293C60 or target >= 0x023E0000:
                raise WorkspaceError(
                    f"runtime symbol {self.name} branches into cache or arena space"
                )


@dataclass(frozen=True)
class RuntimeHookReplacement:
    name: str
    address: int
    component_offset: int
    return_address: int
    expected: bytes
    expected_sha256: str
    replacement: bytes
    target_symbol: str
    rollback: str

    def validate(self, symbols: dict[str, RuntimeSymbol]) -> None:
        if not self.name.strip() or not self.rollback.strip():
            raise WorkspaceError("runtime hook name and rollback must be nonempty")
        if self.address - OVERLAY_BASE != self.component_offset:
            raise WorkspaceError(f"runtime hook {self.name} offset does not match address")
        if not self.expected or len(self.expected) != len(self.replacement):
            raise WorkspaceError(f"runtime hook {self.name} has invalid byte geometry")
        if hashlib.sha256(self.expected).hexdigest() != self.expected_sha256:
            raise WorkspaceError(f"runtime hook {self.name} expected hash mismatch")
        target = symbols.get(self.target_symbol)
        if target is None:
            raise WorkspaceError(f"runtime hook {self.name} target symbol is missing")
        instruction = struct.unpack_from("<I", self.replacement)[0]
        from bakugan_ds.gates.arm32 import decode_branch_target

        if decode_branch_target(self.address, instruction) != target.address:
            raise WorkspaceError(f"runtime hook {self.name} branch target mismatch")


@dataclass(frozen=True)
class RuntimeModule:
    image: bytes
    symbols: dict[str, RuntimeSymbol]
    hook_replacements: tuple[RuntimeHookReplacement, ...]
    sha256: str

    def validate(self) -> None:
        if len(self.image) != SYSTEM2_MODULE_SIZE:
            raise WorkspaceError("runtime module must be exactly 0x8000 bytes")
        if hashlib.sha256(self.image).hexdigest() != self.sha256:
            raise WorkspaceError("runtime module SHA-256 mismatch")
        ordered = sorted(self.symbols.values(), key=lambda item: item.address)
        for symbol in ordered:
            symbol.validate()
        for left, right in itertools.pairwise(ordered):
            if left.address + left.size > right.address:
                raise WorkspaceError(f"runtime symbols overlap: {left.name} and {right.name}")
        for hook in self.hook_replacements:
            hook.validate(self.symbols)


@dataclass(frozen=True)
class _RoutineImage:
    words: tuple[int, ...]
    instruction_word_count: int
    branch_targets: tuple[int, ...]


@dataclass(frozen=True)
class _RoutineDefinition:
    name: str
    offset: int
    image: _RoutineImage
    purpose: str


_OFFSETS = {
    "g2_clear_cache": 0x000,
    "g2_validate_cache": 0x040,
    "g2_crc32_update": 0x0A0,
    "g2_load_selected_record": 0x100,
    "g2_validate_selected_record": 0x500,
    "g2_legacy_gate_bonus": 0x700,
    "g2_calculate_gate_bonus": 0x740,
    "g2_gate_bonus_hook": 0xB00,
    "g2_context_store_hook": 0xB40,
    "g2_select_battle_type": 0xB80,
    "g2_selector_hook": 0xD00,
    "g2_loader_trampoline": 0xD40,
    "g2_clear_hook": 0xDC0,
}


def _address(name: str) -> int:
    return MODULE_BASE + _OFFSETS[name]


def _branch(source: int, target: int, *, link: bool = False) -> int:
    return encode_branch(source, target, link=link)


class _RoutineAssembler:
    def __init__(self, start_address: int) -> None:
        self.start_address = start_address
        self.words: list[int] = []
        self.labels: dict[str, int] = {}
        self.branches: list[tuple[int, str | int, bool, Condition]] = []
        self.literal_loads: list[tuple[int, Register, str]] = []
        self.literals: dict[str, int] = {}

    @property
    def address(self) -> int:
        return self.start_address + len(self.words) * 4

    def emit(self, instruction: int) -> None:
        self.words.append(instruction)

    def label(self, name: str) -> None:
        if name in self.labels or name in self.literals:
            raise WorkspaceError(f"duplicate routine symbol: {name}")
        self.labels[name] = self.address

    def branch(
        self,
        target: str | int,
        *,
        link: bool = False,
        condition: Condition = Condition.AL,
    ) -> None:
        index = len(self.words)
        self.words.append(0)
        self.branches.append((index, target, link, condition))

    def load_constant(self, register: Register, name: str, value: int) -> None:
        if name in self.literals and self.literals[name] != value:
            raise WorkspaceError(f"literal {name} has conflicting values")
        self.literals[name] = value
        index = len(self.words)
        self.words.append(0)
        self.literal_loads.append((index, register, name))

    def finish(self) -> _RoutineImage:
        instruction_word_count = len(self.words)
        literal_addresses: dict[str, int] = {}
        for name, value in self.literals.items():
            literal_addresses[name] = self.start_address + len(self.words) * 4
            self.words.append(value)
        resolved_targets: list[int] = []
        for index, target, link, condition in self.branches:
            if isinstance(target, str):
                target_address = self.labels.get(target)
                if target_address is None:
                    raise WorkspaceError(f"unresolved routine label: {target}")
            else:
                target_address = target
            resolved_targets.append(target_address)
            self.words[index] = encode_branch(
                self.start_address + index * 4,
                target_address,
                link=link,
                condition=condition,
            )
        for index, register, name in self.literal_loads:
            target_address = literal_addresses[name]
            self.words[index] = encode_literal_load(
                self.start_address + index * 4,
                target_address,
                register,
            )
        return _RoutineImage(
            words=tuple(self.words),
            instruction_word_count=instruction_word_count,
            branch_targets=tuple(resolved_targets),
        )


def _static_routine(
    start_address: int,
    words: tuple[int, ...],
    branch_word_indices: tuple[int, ...] = (),
) -> _RoutineImage:
    from bakugan_ds.gates.arm32 import decode_branch_target

    return _RoutineImage(
        words=words,
        instruction_word_count=len(words),
        branch_targets=tuple(
            decode_branch_target(start_address + index * 4, words[index])
            for index in branch_word_indices
        ),
    )


def _mov_register(rd: Register, rm: Register) -> int:
    return encode_data_processing_register(DataOpcode.MOV, rd=rd, rm=rm)


def _add_register(rd: Register, rn: Register, rm: Register) -> int:
    return encode_data_processing_register(DataOpcode.ADD, rd=rd, rn=rn, rm=rm)


def _xor_register(
    rd: Register,
    rn: Register,
    rm: Register,
    *,
    condition: Condition = Condition.AL,
) -> int:
    return encode_data_processing_register(DataOpcode.EOR, rd=rd, rn=rn, rm=rm, condition=condition)


def _compare_register(rn: Register, rm: Register) -> int:
    return encode_data_processing_register(DataOpcode.CMP, rn=rn, rm=rm, set_flags=True)


def _compare_immediate(rn: Register, immediate: int) -> int:
    return encode_data_processing_immediate(
        DataOpcode.CMP, rn=rn, immediate=immediate, set_flags=True
    )


def _with_condition(instruction: int, condition: Condition) -> int:
    return (instruction & 0x0FFFFFFF) | (int(condition) << 28)


def _shift_register(
    rd: Register,
    rm: Register,
    shift_type: ShiftType,
    shift_amount: int,
    *,
    condition: Condition = Condition.AL,
) -> int:
    return encode_data_processing_shifted_register(
        DataOpcode.MOV,
        rd=rd,
        rm=rm,
        shift_type=shift_type,
        shift_amount=shift_amount,
        condition=condition,
    )


def _build_clear_cache() -> _RoutineImage:
    asm = _RoutineAssembler(_address("g2_clear_cache"))
    asm.load_constant(Register.R0, "cache", CACHE_ADDRESS)
    asm.emit(encode_data_processing_immediate(DataOpcode.MOV, rd=Register.R1, immediate=0))
    asm.emit(encode_data_processing_immediate(DataOpcode.MOV, rd=Register.R2, immediate=16))
    asm.label("loop")
    asm.emit(
        encode_load_store(
            Register.R1,
            Register.R0,
            offset=4,
            load=False,
            pre_index=False,
        )
    )
    asm.emit(
        encode_data_processing_immediate(
            DataOpcode.SUB,
            rd=Register.R2,
            rn=Register.R2,
            immediate=1,
            set_flags=True,
        )
    )
    asm.branch("loop", condition=Condition.NE)
    asm.emit(encode_bx(Register.LR))
    return asm.finish()


def _build_validate_cache() -> _RoutineImage:
    asm = _RoutineAssembler(_address("g2_validate_cache"))
    asm.load_constant(Register.R1, "cache", CACHE_ADDRESS)
    for offset, expected in ((0x2A, 1), (0x29, 1)):
        asm.emit(encode_load_store(Register.R2, Register.R1, offset=offset, load=True, byte=True))
        asm.emit(_compare_immediate(Register.R2, expected))
        asm.branch("invalid", condition=Condition.NE)
    for offset in (0x28, 0x00):
        asm.emit(encode_load_store(Register.R2, Register.R1, offset=offset, load=True, byte=True))
        asm.emit(_compare_register(Register.R2, Register.R0))
        asm.branch("invalid", condition=Condition.NE)
    asm.emit(encode_data_processing_immediate(DataOpcode.MOV, rd=Register.R0, immediate=1))
    asm.emit(encode_bx(Register.LR))
    asm.label("invalid")
    asm.emit(encode_data_processing_immediate(DataOpcode.MOV, rd=Register.R0, immediate=0))
    asm.emit(encode_bx(Register.LR))
    return asm.finish()


def _emit_compare_stack_word(
    asm: _RoutineAssembler,
    *,
    stack_offset: int,
    literal_name: str,
    expected: int,
    failure_label: str,
) -> None:
    asm.emit(encode_load_store(Register.R0, Register.SP, offset=stack_offset, load=True))
    asm.load_constant(Register.R1, literal_name, expected)
    asm.emit(_compare_register(Register.R0, Register.R1))
    asm.branch(failure_label, condition=Condition.NE)


def _build_crc32_update() -> _RoutineImage:
    asm = _RoutineAssembler(_address("g2_crc32_update"))
    asm.emit(
        encode_push(
            (
                Register.R4,
                Register.R5,
                Register.R6,
                Register.R7,
                Register.LR,
            )
        )
    )
    asm.emit(_compare_immediate(Register.R2, 0))
    asm.branch("done", condition=Condition.EQ)
    asm.load_constant(Register.R3, "crc_polynomial", 0xEDB88320)

    asm.label("byte_loop")
    asm.emit(
        encode_load_store(
            Register.R4,
            Register.R1,
            offset=1,
            load=True,
            byte=True,
            pre_index=False,
        )
    )
    asm.emit(_xor_register(Register.R0, Register.R0, Register.R4))
    asm.emit(encode_data_processing_immediate(DataOpcode.MOV, rd=Register.R5, immediate=8))

    asm.label("bit_loop")
    asm.emit(
        encode_data_processing_immediate(
            DataOpcode.AND,
            rd=Register.R6,
            rn=Register.R0,
            immediate=1,
        )
    )
    asm.emit(_shift_register(Register.R0, Register.R0, ShiftType.LSR, 1))
    asm.emit(_compare_immediate(Register.R6, 0))
    asm.emit(
        _xor_register(
            Register.R0,
            Register.R0,
            Register.R3,
            condition=Condition.NE,
        )
    )
    asm.emit(
        encode_data_processing_immediate(
            DataOpcode.SUB,
            rd=Register.R5,
            rn=Register.R5,
            immediate=1,
            set_flags=True,
        )
    )
    asm.branch("bit_loop", condition=Condition.NE)
    asm.emit(
        encode_data_processing_immediate(
            DataOpcode.SUB,
            rd=Register.R2,
            rn=Register.R2,
            immediate=1,
            set_flags=True,
        )
    )
    asm.branch("byte_loop", condition=Condition.NE)

    asm.label("done")
    asm.emit(
        encode_pop(
            (
                Register.R4,
                Register.R5,
                Register.R6,
                Register.R7,
                Register.PC,
            )
        )
    )
    return asm.finish()


def _build_validate_selected_record() -> _RoutineImage:
    asm = _RoutineAssembler(_address("g2_validate_selected_record"))
    asm.emit(
        encode_push(
            (
                Register.R4,
                Register.R5,
                Register.R6,
                Register.R7,
                Register.LR,
            )
        )
    )
    asm.emit(_mov_register(Register.R4, Register.R0))
    asm.emit(_compare_immediate(Register.R4, 1))
    asm.branch("invalid", condition=Condition.LO)
    asm.emit(_compare_immediate(Register.R4, 103))
    asm.branch("invalid", condition=Condition.HI)
    asm.load_constant(Register.R5, "cache", CACHE_ADDRESS)
    asm.emit(encode_load_store(Register.R0, Register.R5, offset=0, load=True, byte=True))
    asm.emit(_compare_register(Register.R0, Register.R4))
    asm.branch("invalid", condition=Condition.NE)
    asm.emit(_compare_immediate(Register.R4, 19))
    asm.branch("prototype", condition=Condition.EQ)

    asm.emit(encode_load_store(Register.R0, Register.R5, offset=0, load=True))
    asm.emit(_compare_register(Register.R0, Register.R4))
    asm.branch("invalid", condition=Condition.NE)
    asm.emit(encode_data_processing_immediate(DataOpcode.MOV, rd=Register.R6, immediate=0))
    for offset in (4, 8, 12, 16):
        asm.emit(encode_load_store(Register.R0, Register.R5, offset=offset, load=True))
        asm.emit(_compare_register(Register.R0, Register.R6))
        asm.branch("invalid", condition=Condition.NE)
    asm.emit(encode_load_store(Register.R0, Register.R5, offset=20, load=True))
    asm.emit(_compare_immediate(Register.R0, 0xFF))
    asm.branch("invalid", condition=Condition.NE)
    for offset in (24, 28, 32, 36):
        asm.emit(encode_load_store(Register.R0, Register.R5, offset=offset, load=True))
        asm.emit(_compare_register(Register.R0, Register.R6))
        asm.branch("invalid", condition=Condition.NE)
    asm.branch("valid")

    asm.label("prototype")
    prototype_words = struct.unpack("<10I", serialize_record(approved_juggernoid_record()))
    for index, expected in enumerate(prototype_words):
        asm.emit(encode_load_store(Register.R0, Register.R5, offset=index * 4, load=True))
        asm.load_constant(Register.R1, f"prototype_{index}", expected)
        asm.emit(_compare_register(Register.R0, Register.R1))
        asm.branch("invalid", condition=Condition.NE)

    asm.label("valid")
    asm.emit(encode_data_processing_immediate(DataOpcode.MOV, rd=Register.R0, immediate=1))
    asm.branch("return")
    asm.label("invalid")
    asm.emit(encode_data_processing_immediate(DataOpcode.MOV, rd=Register.R0, immediate=0))
    asm.label("return")
    asm.emit(
        encode_pop(
            (
                Register.R4,
                Register.R5,
                Register.R6,
                Register.R7,
                Register.PC,
            )
        )
    )
    return asm.finish()


def _build_load_selected_record() -> _RoutineImage:
    start = _address("g2_load_selected_record")
    asm = _RoutineAssembler(start)
    # Public hook entry: replay the displaced store, then enter the callable core.
    asm.emit(encode_halfword_transfer(Register.R0, Register.R6, offset=4, load=False))
    asm.branch("core")
    asm.label("core")
    saved = (*tuple(Register(value) for value in range(4, 13)), Register.LR)
    asm.emit(encode_push(saved))
    asm.emit(
        encode_data_processing_immediate(
            DataOpcode.SUB,
            rd=Register.SP,
            rn=Register.SP,
            immediate=144,
        )
    )
    asm.emit(_mov_register(Register.R4, Register.R0))
    asm.branch(_address("g2_clear_cache"), link=True)

    asm.emit(_mov_register(Register.R0, Register.SP))
    asm.branch(FS_INIT_FILE_ADDRESS, link=True)
    asm.emit(_mov_register(Register.R0, Register.SP))
    asm.load_constant(Register.R1, "rom_archive", ROM_ARCHIVE_ADDRESS)
    asm.load_constant(Register.R2, "file_id", REFERENCE_FILE_ID)
    asm.branch(FS_OPEN_FILE_FAST_ADDRESS, link=True)
    asm.emit(_compare_immediate(Register.R0, 0))
    asm.branch("fail_no_open", condition=Condition.EQ)

    asm.emit(_mov_register(Register.R0, Register.SP))
    asm.load_constant(Register.R1, "header_offset", REFERENCE_RAW_SIZE)
    asm.emit(encode_data_processing_immediate(DataOpcode.MOV, rd=Register.R2, immediate=0))
    asm.branch(FS_SEEK_FILE_ADDRESS, link=True)
    asm.emit(_compare_immediate(Register.R0, 0))
    asm.branch("fail_close", condition=Condition.EQ)

    asm.emit(_mov_register(Register.R0, Register.SP))
    asm.emit(
        encode_data_processing_immediate(
            DataOpcode.ADD,
            rd=Register.R1,
            rn=Register.SP,
            immediate=72,
        )
    )
    asm.emit(encode_data_processing_immediate(DataOpcode.MOV, rd=Register.R2, immediate=32))
    asm.branch(FS_READ_FILE_ADDRESS, link=True)
    asm.emit(_compare_immediate(Register.R0, 32))
    asm.branch("fail_close", condition=Condition.NE)

    header_words = struct.unpack("<8I", approved_runtime_header())
    for index, expected in enumerate(header_words):
        _emit_compare_stack_word(
            asm,
            stack_offset=72 + index * 4,
            literal_name=f"header_{index}",
            expected=expected,
            failure_label="fail_close",
        )

    asm.emit(_compare_immediate(Register.R4, 1))
    asm.branch("fail_close", condition=Condition.LO)
    asm.emit(_compare_immediate(Register.R4, 103))
    asm.branch("fail_close", condition=Condition.HI)

    asm.load_constant(Register.R7, "cache", CACHE_ADDRESS)
    asm.load_constant(Register.R8, "crc_initial", 0xFFFFFFFF)
    asm.emit(encode_data_processing_immediate(DataOpcode.MOV, rd=Register.R5, immediate=1))
    asm.emit(encode_data_processing_immediate(DataOpcode.MOV, rd=Register.R6, immediate=103))

    asm.label("record_loop")
    asm.emit(_mov_register(Register.R0, Register.SP))
    asm.emit(
        encode_data_processing_immediate(
            DataOpcode.ADD,
            rd=Register.R1,
            rn=Register.SP,
            immediate=104,
        )
    )
    asm.emit(encode_data_processing_immediate(DataOpcode.MOV, rd=Register.R2, immediate=40))
    asm.branch(FS_READ_FILE_ADDRESS, link=True)
    asm.emit(_compare_immediate(Register.R0, 40))
    asm.branch("fail_close", condition=Condition.NE)

    asm.emit(encode_load_store(Register.R0, Register.SP, offset=104, load=True, byte=True))
    asm.emit(_compare_register(Register.R0, Register.R5))
    asm.branch("fail_close", condition=Condition.NE)

    asm.emit(_mov_register(Register.R0, Register.R8))
    asm.emit(
        encode_data_processing_immediate(
            DataOpcode.ADD,
            rd=Register.R1,
            rn=Register.SP,
            immediate=104,
        )
    )
    asm.emit(encode_data_processing_immediate(DataOpcode.MOV, rd=Register.R2, immediate=40))
    asm.branch(_address("g2_crc32_update"), link=True)
    asm.emit(_mov_register(Register.R8, Register.R0))

    asm.emit(_compare_register(Register.R5, Register.R4))
    asm.branch("skip_copy", condition=Condition.NE)
    for index in range(10):
        asm.emit(
            encode_load_store(
                Register.R0,
                Register.SP,
                offset=104 + index * 4,
                load=True,
            )
        )
        asm.emit(
            encode_load_store(
                Register.R0,
                Register.R7,
                offset=index * 4,
                load=False,
            )
        )
    asm.label("skip_copy")
    asm.emit(
        encode_data_processing_immediate(
            DataOpcode.ADD,
            rd=Register.R5,
            rn=Register.R5,
            immediate=1,
        )
    )
    asm.emit(
        encode_data_processing_immediate(
            DataOpcode.SUB,
            rd=Register.R6,
            rn=Register.R6,
            immediate=1,
            set_flags=True,
        )
    )
    asm.branch("record_loop", condition=Condition.NE)

    asm.load_constant(Register.R0, "crc_xor_out", 0xFFFFFFFF)
    asm.emit(_xor_register(Register.R8, Register.R8, Register.R0))
    asm.emit(encode_load_store(Register.R0, Register.SP, offset=92, load=True))
    asm.emit(_compare_register(Register.R8, Register.R0))
    asm.branch("fail_close", condition=Condition.NE)

    asm.emit(_mov_register(Register.R0, Register.R4))
    asm.branch(_address("g2_validate_selected_record"), link=True)
    asm.emit(_compare_immediate(Register.R0, 1))
    asm.branch("fail_close", condition=Condition.NE)

    asm.emit(_mov_register(Register.R0, Register.SP))
    asm.branch(FS_CLOSE_FILE_ADDRESS, link=True)
    asm.emit(_compare_immediate(Register.R0, 0))
    asm.branch("fail_clear", condition=Condition.EQ)

    asm.load_constant(Register.R1, "cache_metadata", CACHE_ADDRESS)
    asm.emit(_mov_register(Register.R0, Register.R4))
    asm.emit(encode_load_store(Register.R0, Register.R1, offset=0x28, load=False, byte=True))
    asm.emit(encode_data_processing_immediate(DataOpcode.MOV, rd=Register.R0, immediate=1))
    for offset in (0x29, 0x2A):
        asm.emit(encode_load_store(Register.R0, Register.R1, offset=offset, load=False, byte=True))
    asm.emit(encode_data_processing_immediate(DataOpcode.MOV, rd=Register.R0, immediate=0))
    asm.emit(encode_load_store(Register.R0, Register.R1, offset=0x2B, load=False, byte=True))
    asm.emit(encode_data_processing_immediate(DataOpcode.MOV, rd=Register.R0, immediate=1))
    asm.branch("cleanup")

    asm.label("fail_close")
    asm.emit(_mov_register(Register.R0, Register.SP))
    asm.branch(FS_CLOSE_FILE_ADDRESS, link=True)
    asm.label("fail_clear")
    asm.branch(_address("g2_clear_cache"), link=True)
    asm.label("fail_no_open")
    asm.emit(encode_data_processing_immediate(DataOpcode.MOV, rd=Register.R0, immediate=0))
    asm.label("cleanup")
    asm.emit(
        encode_data_processing_immediate(
            DataOpcode.ADD,
            rd=Register.SP,
            rn=Register.SP,
            immediate=144,
        )
    )
    asm.emit(encode_pop((*tuple(Register(value) for value in range(4, 13)), Register.PC)))
    return asm.finish()


def _emit_participant_pointer(
    asm: _RoutineAssembler,
    *,
    session: Register,
    participant_index: Register,
    destination: Register,
    scratch: Register,
    failure_label: str,
) -> None:
    asm.emit(_shift_register(scratch, participant_index, ShiftType.LSL, 2))
    asm.emit(_add_register(scratch, session, scratch))
    asm.emit(encode_load_store(destination, scratch, offset=0x0C, load=True))
    asm.emit(_compare_immediate(destination, 0))
    asm.branch(failure_label, condition=Condition.EQ)


def _build_calculate_gate_bonus() -> _RoutineImage:
    asm = _RoutineAssembler(_address("g2_calculate_gate_bonus"))
    saved = (*tuple(Register(value) for value in range(4, 13)), Register.LR)
    asm.emit(encode_push(saved))
    asm.emit(_mov_register(Register.R11, Register.R4))

    asm.emit(encode_data_processing_immediate(DataOpcode.MOV, rd=Register.R0, immediate=19))
    asm.branch(_address("g2_validate_cache"), link=True)
    asm.emit(_compare_immediate(Register.R0, 1))
    asm.branch("fallback", condition=Condition.NE)

    asm.load_constant(Register.R7, "cache", CACHE_ADDRESS)
    prototype_words = struct.unpack("<10I", serialize_record(approved_juggernoid_record()))
    for index, expected in enumerate(prototype_words):
        asm.emit(encode_load_store(Register.R0, Register.R7, offset=index * 4, load=True))
        asm.load_constant(Register.R1, f"prototype_{index}", expected)
        asm.emit(_compare_register(Register.R0, Register.R1))
        asm.branch("fallback", condition=Condition.NE)

    asm.emit(encode_halfword_transfer(Register.R0, Register.R6, offset=4, load=True))
    asm.emit(_compare_immediate(Register.R0, 19))
    asm.branch("fallback", condition=Condition.NE)
    asm.emit(encode_load_store(Register.R4, Register.R6, offset=6, load=True, byte=True))
    asm.emit(_compare_immediate(Register.R4, 16))
    asm.branch("fallback", condition=Condition.HS)

    asm.emit(encode_load_store(Register.R0, Register.R5, offset=0x19, load=True, byte=True))
    asm.emit(
        encode_data_processing_immediate(
            DataOpcode.AND,
            rd=Register.R7,
            rn=Register.R0,
            immediate=0x0F,
        )
    )
    asm.emit(_compare_immediate(Register.R7, 6))
    asm.branch("fallback", condition=Condition.HS)
    asm.emit(_shift_register(Register.R8, Register.R0, ShiftType.LSR, 4))
    asm.emit(_compare_immediate(Register.R8, 16))
    asm.branch("fallback", condition=Condition.HS)

    asm.load_constant(Register.R9, "global_config", 0x020D433C)
    asm.emit(encode_load_store(Register.R10, Register.R9, load=True))
    asm.emit(_compare_immediate(Register.R10, 0))
    asm.branch("fallback", condition=Condition.EQ)

    asm.emit(_compare_immediate(Register.R11, 0))
    asm.emit(
        encode_load_store(
            Register.R0,
            Register.R10,
            offset=0x28D,
            load=True,
            byte=True,
            condition=Condition.EQ,
        )
    )
    asm.emit(
        encode_load_store(
            Register.R0,
            Register.R10,
            offset=0x28E,
            load=True,
            byte=True,
            condition=Condition.NE,
        )
    )
    asm.emit(_compare_immediate(Register.R0, 26))
    asm.branch("fallback", condition=Condition.HS)
    asm.emit(_shift_register(Register.R1, Register.R0, ShiftType.LSL, 2))
    asm.emit(_add_register(Register.R1, Register.R1, Register.R0))
    asm.emit(_shift_register(Register.R1, Register.R1, ShiftType.LSL, 2))
    asm.emit(_add_register(Register.R12, Register.R10, Register.R1))
    asm.emit(
        encode_data_processing_immediate(
            DataOpcode.ADD,
            rd=Register.R12,
            rn=Register.R12,
            immediate=0x7C,
        )
    )
    asm.emit(encode_load_store(Register.R1, Register.R12, offset=0x0F, load=True, byte=True))
    asm.emit(
        encode_data_processing_immediate(
            DataOpcode.AND,
            rd=Register.R1,
            rn=Register.R1,
            immediate=0x0F,
        )
    )
    asm.emit(_compare_register(Register.R1, Register.R8))
    asm.branch("fallback", condition=Condition.NE)
    asm.emit(encode_load_store(Register.R0, Register.R12, offset=0x0E, load=True, byte=True))
    asm.emit(_compare_immediate(Register.R0, 3))
    asm.branch("fallback", condition=Condition.HS)

    _emit_participant_pointer(
        asm,
        session=Register.R10,
        participant_index=Register.R8,
        destination=Register.R1,
        scratch=Register.R2,
        failure_label="fallback",
    )
    asm.emit(encode_data_processing_immediate(DataOpcode.MOV, rd=Register.R2, immediate=12))
    asm.emit(encode_mul(Register.R0, Register.R0, Register.R2))
    asm.emit(_add_register(Register.R12, Register.R1, Register.R0))
    asm.emit(
        encode_data_processing_immediate(
            DataOpcode.ADD,
            rd=Register.R12,
            rn=Register.R12,
            immediate=12,
        )
    )
    asm.emit(_mov_register(Register.R11, Register.R7))
    asm.emit(encode_halfword_transfer(Register.R0, Register.R12, offset=4, load=True))
    asm.emit(_compare_immediate(Register.R0, CORE_G_COMPRESSION_THRESHOLD))
    asm.emit(
        _shift_register(
            Register.R0,
            Register.R0,
            ShiftType.LSR,
            1,
            condition=Condition.HI,
        )
    )
    asm.emit(
        encode_data_processing_immediate(
            DataOpcode.ADD,
            rd=Register.R0,
            rn=Register.R0,
            immediate=CORE_G_COMPRESSION_BASE,
            condition=Condition.HI,
        )
    )
    asm.emit(encode_data_processing_immediate(DataOpcode.MOV, rd=Register.R1, immediate=20))
    asm.emit(encode_mul(Register.R0, Register.R0, Register.R1))
    asm.emit(
        _shift_register(
            Register.R0,
            Register.R0,
            ShiftType.LSR,
            Q8_8_DENOMINATOR.bit_length() - 1,
        )
    )
    asm.emit(
        encode_data_processing_immediate(
            DataOpcode.ADD,
            rd=Register.R7,
            rn=Register.R0,
            immediate=60,
        )
    )
    asm.emit(_compare_immediate(Register.R11, 1))
    asm.emit(
        encode_data_processing_immediate(
            DataOpcode.ADD,
            rd=Register.R7,
            rn=Register.R7,
            immediate=30,
            condition=Condition.EQ,
        )
    )

    asm.emit(encode_load_store(Register.R0, Register.R6, offset=0x19, load=True, byte=True))
    asm.emit(_shift_register(Register.R0, Register.R0, ShiftType.LSR, 4))
    asm.emit(_compare_immediate(Register.R0, 16))
    asm.branch("fallback", condition=Condition.HS)
    asm.emit(encode_load_store(Register.R1, Register.R6, offset=0x2D, load=True, byte=True))
    asm.emit(_shift_register(Register.R1, Register.R1, ShiftType.LSR, 4))
    asm.emit(_compare_immediate(Register.R1, 16))
    asm.branch("fallback", condition=Condition.HS)
    asm.emit(_compare_register(Register.R0, Register.R1))
    asm.branch("fallback", condition=Condition.EQ)
    asm.emit(_compare_register(Register.R4, Register.R0))
    asm.emit(_with_condition(_mov_register(Register.R12, Register.R1), Condition.EQ))
    asm.branch("owner_resolved", condition=Condition.EQ)
    asm.emit(_compare_register(Register.R4, Register.R1))
    asm.emit(_with_condition(_mov_register(Register.R12, Register.R0), Condition.EQ))
    asm.branch("fallback", condition=Condition.NE)
    asm.label("owner_resolved")

    _emit_participant_pointer(
        asm,
        session=Register.R10,
        participant_index=Register.R4,
        destination=Register.R1,
        scratch=Register.R11,
        failure_label="fallback",
    )
    _emit_participant_pointer(
        asm,
        session=Register.R10,
        participant_index=Register.R12,
        destination=Register.R0,
        scratch=Register.R11,
        failure_label="fallback",
    )
    asm.emit(encode_load_store(Register.R2, Register.R1, offset=0xEE, load=True, byte=True))
    asm.emit(encode_load_store(Register.R3, Register.R0, offset=0xEE, load=True, byte=True))
    asm.emit(encode_load_store(Register.R6, Register.R9, offset=0x98, load=True, byte=True))
    asm.emit(_compare_immediate(Register.R6, 0))
    asm.branch("scores_ready", condition=Condition.EQ)

    asm.emit(encode_load_store(Register.R11, Register.R1, offset=0xF2, load=True, byte=True))
    asm.emit(_compare_immediate(Register.R11, 16))
    asm.branch("fallback", condition=Condition.HS)
    asm.emit(_compare_register(Register.R11, Register.R4))
    asm.branch("fallback", condition=Condition.EQ)
    asm.emit(_compare_register(Register.R11, Register.R12))
    asm.branch("fallback", condition=Condition.EQ)
    _emit_participant_pointer(
        asm,
        session=Register.R10,
        participant_index=Register.R11,
        destination=Register.R9,
        scratch=Register.R6,
        failure_label="fallback",
    )
    asm.emit(encode_load_store(Register.R6, Register.R9, offset=0xF2, load=True, byte=True))
    asm.emit(_compare_register(Register.R6, Register.R4))
    asm.branch("fallback", condition=Condition.NE)
    asm.emit(encode_load_store(Register.R6, Register.R9, offset=0xEE, load=True, byte=True))
    asm.emit(_add_register(Register.R2, Register.R2, Register.R6))

    asm.emit(encode_load_store(Register.R11, Register.R0, offset=0xF2, load=True, byte=True))
    asm.emit(_compare_immediate(Register.R11, 16))
    asm.branch("fallback", condition=Condition.HS)
    asm.emit(_compare_register(Register.R11, Register.R12))
    asm.branch("fallback", condition=Condition.EQ)
    asm.emit(_compare_register(Register.R11, Register.R4))
    asm.branch("fallback", condition=Condition.EQ)
    _emit_participant_pointer(
        asm,
        session=Register.R10,
        participant_index=Register.R11,
        destination=Register.R9,
        scratch=Register.R6,
        failure_label="fallback",
    )
    asm.emit(encode_load_store(Register.R6, Register.R9, offset=0xF2, load=True, byte=True))
    asm.emit(_compare_register(Register.R6, Register.R12))
    asm.branch("fallback", condition=Condition.NE)
    asm.emit(encode_load_store(Register.R6, Register.R9, offset=0xEE, load=True, byte=True))
    asm.emit(_add_register(Register.R3, Register.R3, Register.R6))

    asm.label("scores_ready")
    asm.emit(_compare_register(Register.R8, Register.R4))
    asm.branch("store", condition=Condition.NE)
    asm.emit(_compare_register(Register.R2, Register.R3))
    asm.emit(
        encode_data_processing_immediate(
            DataOpcode.ADD,
            rd=Register.R7,
            rn=Register.R7,
            immediate=40,
            condition=Condition.LO,
        )
    )
    asm.label("store")
    asm.load_constant(Register.R0, "i16_max", 0x7FFF)
    asm.emit(_compare_register(Register.R7, Register.R0))
    asm.emit(_with_condition(_mov_register(Register.R7, Register.R0), Condition.HI))
    asm.emit(encode_halfword_transfer(Register.R7, Register.R5, offset=0x12, load=False))
    asm.emit(encode_pop(saved))
    asm.emit(encode_data_processing_immediate(DataOpcode.MOV, rd=Register.R3, immediate=1))
    asm.branch(0x0223D278)

    asm.label("fallback")
    asm.emit(encode_pop(saved))
    asm.branch(_address("g2_legacy_gate_bonus"))
    return asm.finish()


def _build_context_store_hook() -> _RoutineImage:
    asm = _RoutineAssembler(_address("g2_context_store_hook"))
    asm.emit(_compare_immediate(Register.R3, 1))
    asm.branch("legacy", condition=Condition.NE)
    asm.emit(_add_register(Register.R0, Register.R2, Register.R1))
    asm.load_constant(Register.R12, "u16_max", 0xFFFF)
    asm.emit(_compare_register(Register.R0, Register.R12))
    asm.emit(_with_condition(_mov_register(Register.R0, Register.R12), Condition.HI))
    asm.emit(encode_halfword_transfer(Register.R0, Register.R5, offset=0x0E, load=False))
    asm.branch(0x0223D290)
    asm.label("legacy")
    asm.emit(_add_register(Register.R0, Register.R2, Register.R1))
    asm.emit(encode_halfword_transfer(Register.R0, Register.R5, offset=0x0E, load=False))
    asm.branch(0x0223D290)
    return asm.finish()


def _build_select_battle_type() -> _RoutineImage:
    asm = _RoutineAssembler(_address("g2_select_battle_type"))
    asm.emit(encode_push((Register.R4, Register.LR)))
    asm.emit(_mov_register(Register.R4, Register.R0))
    asm.emit(encode_halfword_transfer(Register.R0, Register.R4, offset=4, load=True))
    asm.emit(_compare_immediate(Register.R0, 19))
    asm.branch("legacy", condition=Condition.NE)
    asm.branch(_address("g2_validate_cache"), link=True)
    asm.emit(_compare_immediate(Register.R0, 1))
    asm.branch("legacy", condition=Condition.NE)
    asm.emit(encode_data_processing_immediate(DataOpcode.MOV, rd=Register.R0, immediate=6))
    asm.load_constant(
        Register.R1,
        "battle_weights",
        CACHE_ADDRESS + GATE_RECORD_BATTLE_WEIGHTS_OFFSET,
    )
    asm.branch(WEIGHTED_SELECTOR_ADDRESS, link=True)
    asm.emit(_compare_immediate(Register.R0, 5))
    asm.branch("done", condition=Condition.LS)
    asm.label("legacy")
    asm.emit(_mov_register(Register.R0, Register.R4))
    asm.branch(0x022433AC, link=True)
    asm.label("done")
    asm.emit(encode_pop((Register.R4, Register.PC)))
    return asm.finish()


def _build_loader_trampoline() -> _RoutineImage:
    asm = _RoutineAssembler(_address("g2_loader_trampoline"))
    asm.emit(0xE92D4008)  # exact displaced push {r3, lr}
    extra = (
        Register.R0,
        Register.R1,
        Register.R2,
        *tuple(Register(value) for value in range(4, 13)),
    )
    asm.emit(encode_push(extra))
    asm.emit(encode_load_store(Register.R1, Register.R0, offset=0x38, load=True))
    asm.emit(encode_halfword_transfer(Register.R4, Register.R1, offset=4, load=True))
    asm.emit(_mov_register(Register.R0, Register.R4))
    asm.branch(_address("g2_validate_cache"), link=True)
    asm.emit(_compare_immediate(Register.R0, 1))
    asm.branch("restore", condition=Condition.EQ)
    asm.emit(_mov_register(Register.R0, Register.R4))
    asm.branch(_address("g2_load_selected_record") + 8, link=True)
    asm.label("restore")
    asm.emit(encode_pop(extra))
    asm.branch(0x022433B0)
    return asm.finish()


def _build_clear_hook() -> _RoutineImage:
    asm = _RoutineAssembler(_address("g2_clear_hook"))
    saved = (
        Register.R1,
        Register.R2,
        Register.R3,
        Register.R4,
        Register.R12,
        Register.LR,
    )
    asm.emit(encode_push(saved))
    asm.branch(_address("g2_clear_cache"), link=True)
    asm.load_constant(Register.R12, "legacy_load_address", 0x02241B0C)
    asm.emit(encode_load_store(Register.R0, Register.R12, offset=0, load=True))
    asm.emit(
        encode_pop(
            (
                Register.R1,
                Register.R2,
                Register.R3,
                Register.R4,
                Register.R12,
                Register.PC,
            )
        )
    )
    return asm.finish()


def _routine_definitions() -> tuple[_RoutineDefinition, ...]:
    legacy = _address("g2_legacy_gate_bonus")
    return (
        _RoutineDefinition(
            "g2_clear_cache",
            _OFFSETS["g2_clear_cache"],
            _build_clear_cache(),
            "Clear exactly sixteen cache words and return.",
        ),
        _RoutineDefinition(
            "g2_validate_cache",
            _OFFSETS["g2_validate_cache"],
            _build_validate_cache(),
            "Validate cache flag, version, metadata ID, and record ID.",
        ),
        _RoutineDefinition(
            "g2_crc32_update",
            _OFFSETS["g2_crc32_update"],
            _build_crc32_update(),
            "Update a reflected IEEE CRC32 over a bounded byte buffer.",
        ),
        _RoutineDefinition(
            "g2_load_selected_record",
            _OFFSETS["g2_load_selected_record"],
            _build_load_selected_record(),
            (
                "Read all 103 ordered records, recompute payload CRC32, and stage "
                "the selected record through confirmed NitroFS calls."
            ),
        ),
        _RoutineDefinition(
            "g2_validate_selected_record",
            _OFFSETS["g2_validate_selected_record"],
            _build_validate_selected_record(),
            "Validate canonical passthrough bytes or the exact approved Gate 19 record.",
        ),
        _RoutineDefinition(
            "g2_legacy_gate_bonus",
            _OFFSETS["g2_legacy_gate_bonus"],
            _static_routine(
                legacy,
                (
                    0xE5D51019,
                    0xE1D600B4,
                    0xE1A01E01,
                    0xE1A01E21,
                    _branch(legacy + 16, 0x02065BF4, link=True),
                    0xE3A0100A,
                    0xE0010190,
                    0xE1C511B2,
                    0xE3A03000,
                    _branch(legacy + 36, 0x0223D278),
                ),
                (4, 9),
            ),
            "Relocated exact original Gate lookup, scale, and store block.",
        ),
        _RoutineDefinition(
            "g2_calculate_gate_bonus",
            _OFFSETS["g2_calculate_gate_bonus"],
            _build_calculate_gate_bonus(),
            "Validate live context and calculate the approved Juggernoid Gate bonus.",
        ),
        _RoutineDefinition(
            "g2_gate_bonus_hook",
            _OFFSETS["g2_gate_bonus_hook"],
            _static_routine(
                _address("g2_gate_bonus_hook"),
                (_branch(_address("g2_gate_bonus_hook"), _address("g2_calculate_gate_bonus")),),
                (0,),
            ),
            "Stable Gate hook entry routed through the approved Juggernoid calculation.",
        ),
        _RoutineDefinition(
            "g2_context_store_hook",
            _OFFSETS["g2_context_store_hook"],
            _build_context_store_hook(),
            "Clamp successful System 2.0 target totals and replay legacy add/store.",
        ),
        _RoutineDefinition(
            "g2_select_battle_type",
            _OFFSETS["g2_select_battle_type"],
            _build_select_battle_type(),
            (
                "Use approved Gate 19 weights for the normal fallback and call "
                "the original fixed metadata selector on phase-local failure."
            ),
        ),
        _RoutineDefinition(
            "g2_selector_hook",
            _OFFSETS["g2_selector_hook"],
            _static_routine(
                _address("g2_selector_hook"),
                (_branch(_address("g2_selector_hook"), _address("g2_select_battle_type")),),
                (0,),
            ),
            "Stable selector hook entry; Task 8 uses legacy fixed metadata.",
        ),
        _RoutineDefinition(
            "g2_loader_trampoline",
            _OFFSETS["g2_loader_trampoline"],
            _build_loader_trampoline(),
            "Validate selected cache identity, reload on mismatch, then continue selector.",
        ),
        _RoutineDefinition(
            "g2_clear_hook",
            _OFFSETS["g2_clear_hook"],
            _build_clear_hook(),
            "Clear cache, replay displaced result-path load, and return.",
        ),
    )


_HOOK_HASHES = {
    HookPurpose.GATE_BONUS: ("ea818916339a9e9050f32020781f80611e88065b6c9adc6a324fcbb43f79a6d5"),
    HookPurpose.CONTEXT_ACCESS: (
        "8caaf927c5702aa9c1041697d0c2f8000ca0c64f9cc9c9a810ce36a08783ac38"
    ),
    HookPurpose.BATTLE_TYPE_SELECTOR: (
        "c250ec6758f4cb49cd6c3467aa8c39647cf33446a35413341b715ad61133f54d"
    ),
    HookPurpose.EXPANDED_DATA_LOOKUP: (
        "fe8d65ae913df24877f27645b6abefd01c7d55d06183491a9a5cb0579724f022"
    ),
}


def _replacement(
    *,
    name: str,
    address: int,
    return_address: int,
    expected: bytes,
    expected_sha256: str,
    target_symbol: str,
    symbols: dict[str, RuntimeSymbol],
    link: bool = False,
    rollback: str,
) -> RuntimeHookReplacement:
    target = symbols[target_symbol].address
    first = struct.pack("<I", encode_branch(address, target, link=link))
    padding = struct.pack("<I", NOP) * ((len(expected) - 4) // 4)
    result = RuntimeHookReplacement(
        name=name,
        address=address,
        component_offset=address - OVERLAY_BASE,
        return_address=return_address,
        expected=expected,
        expected_sha256=expected_sha256,
        replacement=first + padding,
        target_symbol=target_symbol,
        rollback=rollback,
    )
    result.validate(symbols)
    return result


def _hook_replacements(
    symbols: dict[str, RuntimeSymbol],
) -> tuple[RuntimeHookReplacement, ...]:
    return (
        _replacement(
            name="gate_bonus",
            address=0x0223D258,
            return_address=0x0223D278,
            expected=validate_hook_source_bytes(
                HookPurpose.GATE_BONUS, _HOOK_HASHES[HookPurpose.GATE_BONUS]
            ),
            expected_sha256=_HOOK_HASHES[HookPurpose.GATE_BONUS],
            target_symbol="g2_gate_bonus_hook",
            symbols=symbols,
            rollback="Restore the exact 32-byte legacy Gate bonus block.",
        ),
        _replacement(
            name="context_access",
            address=0x0223D288,
            return_address=0x0223D290,
            expected=validate_hook_source_bytes(
                HookPurpose.CONTEXT_ACCESS,
                _HOOK_HASHES[HookPurpose.CONTEXT_ACCESS],
            ),
            expected_sha256=_HOOK_HASHES[HookPurpose.CONTEXT_ACCESS],
            target_symbol="g2_context_store_hook",
            symbols=symbols,
            rollback="Restore the exact add and target-total halfword store.",
        ),
        _replacement(
            name="battle_type_selector",
            address=0x0223E350,
            return_address=0x0223E354,
            expected=validate_hook_source_bytes(
                HookPurpose.BATTLE_TYPE_SELECTOR,
                _HOOK_HASHES[HookPurpose.BATTLE_TYPE_SELECTOR],
            ),
            expected_sha256=_HOOK_HASHES[HookPurpose.BATTLE_TYPE_SELECTOR],
            target_symbol="g2_selector_hook",
            symbols=symbols,
            link=True,
            rollback="Restore the original BL to the fixed metadata selector.",
        ),
        _replacement(
            name="expanded_data_lookup",
            address=0x022433AC,
            return_address=0x022433B0,
            expected=validate_hook_source_bytes(
                HookPurpose.EXPANDED_DATA_LOOKUP,
                _HOOK_HASHES[HookPurpose.EXPANDED_DATA_LOOKUP],
            ),
            expected_sha256=_HOOK_HASHES[HookPurpose.EXPANDED_DATA_LOOKUP],
            target_symbol="g2_loader_trampoline",
            symbols=symbols,
            rollback="Restore the original selector prologue push instruction.",
        ),
        _replacement(
            name="cache_load",
            address=GATE_LOADER_HOOK_ADDRESS,
            return_address=GATE_LOADER_RETURN_ADDRESS,
            expected=GATE_LOADER_EXPECTED_BYTES,
            expected_sha256=GATE_LOADER_EXPECTED_SHA256,
            target_symbol="g2_load_selected_record",
            symbols=symbols,
            link=True,
            rollback="Restore the original selected Gate halfword store.",
        ),
        _replacement(
            name="cache_clear",
            address=GATE_CLEAR_HOOK_ADDRESS,
            return_address=GATE_CLEAR_RETURN_ADDRESS,
            expected=GATE_CLEAR_EXPECTED_BYTES,
            expected_sha256=GATE_CLEAR_EXPECTED_SHA256,
            target_symbol="g2_clear_hook",
            symbols=symbols,
            link=True,
            rollback="Restore the original PC-relative result-path load.",
        ),
    )


def build_milestone_6c_module() -> RuntimeModule:
    image = bytearray(SYSTEM2_MODULE_SIZE)
    symbols: dict[str, RuntimeSymbol] = {}
    for definition in _routine_definitions():
        address = MODULE_BASE + definition.offset
        data = struct.pack(f"<{len(definition.image.words)}I", *definition.image.words)
        end = definition.offset + len(data)
        if end > SYSTEM2_MODULE_SIZE:
            raise WorkspaceError(f"runtime routine {definition.name} exceeds module")
        if any(image[definition.offset : end]):
            raise WorkspaceError(f"runtime routine {definition.name} overlaps another")
        image[definition.offset : end] = data
        symbol = RuntimeSymbol(
            name=definition.name,
            address=address,
            size=len(data),
            code_size=definition.image.instruction_word_count * 4,
            branch_targets=definition.image.branch_targets,
            purpose=definition.purpose,
        )
        symbol.validate()
        symbols[definition.name] = symbol
    ordered_symbols = dict(sorted(symbols.items(), key=lambda item: item[1].address))
    module = RuntimeModule(
        image=bytes(image),
        symbols=ordered_symbols,
        hook_replacements=_hook_replacements(ordered_symbols),
        sha256=hashlib.sha256(image).hexdigest(),
    )
    module.validate()
    return module
