from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field

_U32 = 0xFFFFFFFF


class ArmExecutionError(RuntimeError):
    pass


@dataclass
class SparseMemory:
    _bytes: dict[int, int] = field(default_factory=dict)

    def map(self, address: int, data: bytes) -> None:
        for offset, value in enumerate(data):
            self._bytes[address + offset] = value

    def read8(self, address: int) -> int:
        return self._bytes.get(address, 0)

    def read16(self, address: int) -> int:
        return self.read8(address) | (self.read8(address + 1) << 8)

    def read32(self, address: int) -> int:
        return self.read16(address) | (self.read16(address + 2) << 16)

    def write8(self, address: int, value: int) -> None:
        self._bytes[address] = value & 0xFF

    def write16(self, address: int, value: int) -> None:
        self.write8(address, value)
        self.write8(address + 1, value >> 8)

    def write32(self, address: int, value: int) -> None:
        self.write16(address, value)
        self.write16(address + 2, value >> 16)


ExternalCall = Callable[["ArmCpu"], None]


@dataclass
class ArmCpu:
    memory: SparseMemory
    registers: list[int] = field(default_factory=lambda: [0] * 16)
    n: bool = False
    z: bool = False
    c: bool = False
    v: bool = False
    external_calls: dict[int, ExternalCall] = field(default_factory=dict)

    def _condition_passes(self, condition: int) -> bool:
        return {
            0x0: self.z,
            0x1: not self.z,
            0x2: self.c,
            0x3: not self.c,
            0x4: self.n,
            0x5: not self.n,
            0x6: self.v,
            0x7: not self.v,
            0x8: self.c and not self.z,
            0x9: not self.c or self.z,
            0xA: self.n == self.v,
            0xB: self.n != self.v,
            0xC: not self.z and self.n == self.v,
            0xD: self.z or self.n != self.v,
            0xE: True,
        }.get(condition, False)

    @staticmethod
    def _ror(value: int, amount: int) -> int:
        amount &= 31
        value &= _U32
        if amount == 0:
            return value
        return ((value >> amount) | (value << (32 - amount))) & _U32

    @staticmethod
    def _shift(value: int, shift_type: int, amount: int) -> int:
        value &= _U32
        if shift_type == 0:
            return (value << amount) & _U32
        if shift_type == 1:
            if amount == 0:
                amount = 32
            return 0 if amount >= 32 else value >> amount
        if shift_type == 2:
            if amount == 0:
                amount = 32
            signed = value if value < 0x80000000 else value - (1 << 32)
            if amount >= 32:
                return _U32 if signed < 0 else 0
            return (signed >> amount) & _U32
        if shift_type == 3:
            if amount == 0:
                raise ArmExecutionError("RRX is not supported by the fixture")
            return ArmCpu._ror(value, amount)
        raise ArmExecutionError("invalid shift type")

    def _operand2(self, instruction: int) -> int:
        if instruction & (1 << 25):
            immediate = instruction & 0xFF
            rotation = ((instruction >> 8) & 0xF) * 2
            return self._ror(immediate, rotation)
        if instruction & (1 << 4):
            raise ArmExecutionError("register-controlled shifts are unsupported")
        rm = instruction & 0xF
        shift_type = (instruction >> 5) & 0x3
        shift_amount = (instruction >> 7) & 0x1F
        return self._shift(self.registers[rm], shift_type, shift_amount)

    def _set_sub_flags(self, left: int, right: int, result: int) -> None:
        left &= _U32
        right &= _U32
        result &= _U32
        self.n = bool(result & 0x80000000)
        self.z = result == 0
        self.c = left >= right
        self.v = bool(((left ^ right) & (left ^ result)) & 0x80000000)

    def _set_add_flags(self, left: int, right: int, result: int) -> None:
        full = (left & _U32) + (right & _U32)
        result &= _U32
        self.n = bool(result & 0x80000000)
        self.z = result == 0
        self.c = full > _U32
        self.v = bool((~(left ^ right) & (left ^ result)) & 0x80000000)

    def _execute_data_processing(self, instruction: int) -> None:
        opcode = (instruction >> 21) & 0xF
        set_flags = bool(instruction & (1 << 20))
        rn = (instruction >> 16) & 0xF
        rd = (instruction >> 12) & 0xF
        left = self.registers[rn]
        right = self._operand2(instruction)
        if opcode == 0x0:
            result = left & right
        elif opcode == 0x1:
            result = left ^ right
        elif opcode == 0x2:
            result = (left - right) & _U32
        elif opcode == 0x4:
            result = (left + right) & _U32
        elif opcode == 0xA:
            result = (left - right) & _U32
            self._set_sub_flags(left, right, result)
            return
        elif opcode == 0xC:
            result = left | right
        elif opcode == 0xD:
            result = right
        elif opcode == 0xE:
            result = left & ~right
        else:
            raise ArmExecutionError(f"unsupported data-processing opcode {opcode}")
        self.registers[rd] = result
        if set_flags:
            if opcode == 0x2:
                self._set_sub_flags(left, right, result)
            elif opcode == 0x4:
                self._set_add_flags(left, right, result)
            else:
                self.n = bool(result & 0x80000000)
                self.z = result == 0

    def _execute_single_transfer(self, instruction: int) -> None:
        if instruction & (1 << 25):
            raise ArmExecutionError("register-offset transfers are unsupported")
        pre = bool(instruction & (1 << 24))
        up = bool(instruction & (1 << 23))
        byte = bool(instruction & (1 << 22))
        writeback = bool(instruction & (1 << 21))
        load = bool(instruction & (1 << 20))
        rn = (instruction >> 16) & 0xF
        rd = (instruction >> 12) & 0xF
        offset = instruction & 0xFFF
        if not up:
            offset = -offset
        base = (self.registers[rn] + (8 if rn == 15 else 0)) & _U32
        address = (base + offset) & _U32 if pre else base
        if load:
            value = self.memory.read8(address) if byte else self.memory.read32(address)
            self.registers[rd] = value
        elif byte:
            self.memory.write8(address, self.registers[rd])
        else:
            self.memory.write32(address, self.registers[rd])
        if writeback or not pre:
            self.registers[rn] = (base + offset) & _U32

    def _execute_halfword_transfer(self, instruction: int) -> None:
        pre = bool(instruction & (1 << 24))
        up = bool(instruction & (1 << 23))
        immediate = bool(instruction & (1 << 22))
        writeback = bool(instruction & (1 << 21))
        load = bool(instruction & (1 << 20))
        if not immediate:
            raise ArmExecutionError("register-offset halfword transfers are unsupported")
        rn = (instruction >> 16) & 0xF
        rd = (instruction >> 12) & 0xF
        offset = ((instruction >> 4) & 0xF0) | (instruction & 0xF)
        if not up:
            offset = -offset
        base = self.registers[rn]
        address = (base + offset) & _U32 if pre else base
        if load:
            self.registers[rd] = self.memory.read16(address)
        else:
            self.memory.write16(address, self.registers[rd])
        if writeback or not pre:
            self.registers[rn] = (base + offset) & _U32

    def _execute_block_transfer(self, instruction: int) -> int | None:
        pre = bool(instruction & (1 << 24))
        up = bool(instruction & (1 << 23))
        writeback = bool(instruction & (1 << 21))
        load = bool(instruction & (1 << 20))
        rn = (instruction >> 16) & 0xF
        register_list = [index for index in range(16) if instruction & (1 << index)]
        base = self.registers[rn]
        count = len(register_list)
        if up and not pre:
            start = base
            final = base + count * 4
        elif not up and pre:
            start = base - count * 4
            final = start
        else:
            raise ArmExecutionError("unsupported block-transfer addressing mode")
        loaded_pc: int | None = None
        for offset, register in enumerate(register_list):
            address = start + offset * 4
            if load:
                value = self.memory.read32(address)
                if register == 15:
                    loaded_pc = value
                else:
                    self.registers[register] = value
            else:
                self.memory.write32(address, self.registers[register])
        if writeback:
            self.registers[rn] = final if up else start
        return loaded_pc

    def run(
        self,
        start_address: int,
        *,
        stop_addresses: Iterable[int],
        max_steps: int = 10000,
    ) -> int:
        stops = set(stop_addresses)
        self.registers[15] = start_address
        for _ in range(max_steps):
            pc = self.registers[15]
            if pc in stops:
                return pc
            handler = self.external_calls.get(pc)
            if handler is not None:
                handler(self)
                continue
            instruction = self.memory.read32(pc)
            next_pc = (pc + 4) & _U32
            condition = instruction >> 28
            if not self._condition_passes(condition):
                self.registers[15] = next_pc
                continue
            if (instruction & 0x0FFFFFF0) == 0x012FFF10:
                next_pc = self.registers[instruction & 0xF]
            elif (instruction & 0x0E000000) == 0x0A000000:
                displacement = instruction & 0x00FFFFFF
                if displacement & 0x00800000:
                    displacement -= 1 << 24
                if instruction & (1 << 24):
                    self.registers[14] = next_pc
                next_pc = (pc + 8 + displacement * 4) & _U32
            elif (instruction & 0x0E000000) == 0x08000000:
                loaded_pc = self._execute_block_transfer(instruction)
                if loaded_pc is not None:
                    next_pc = loaded_pc
            elif (instruction & 0x0C000000) == 0x04000000:
                self._execute_single_transfer(instruction)
            elif (instruction & 0x0FC000F0) == 0x00000090:
                rd = (instruction >> 16) & 0xF
                rs = (instruction >> 8) & 0xF
                rm = instruction & 0xF
                self.registers[rd] = (self.registers[rm] * self.registers[rs]) & _U32
            elif (instruction & 0x0E000090) == 0x00000090:
                self._execute_halfword_transfer(instruction)
            elif (instruction & 0x0C000000) == 0:
                self._execute_data_processing(instruction)
            else:
                raise ArmExecutionError(
                    f"unsupported ARM instruction 0x{instruction:08X} at 0x{pc:08X}"
                )
            self.registers[15] = next_pc
        raise ArmExecutionError("ARM fixture exceeded step limit")
