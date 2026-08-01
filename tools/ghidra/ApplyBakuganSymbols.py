# Apply Bakugan DS overlay metadata and candidate symbols to the current Ghidra program.
# @category BakuganDS

from ghidra.program.model.symbol import SourceType
import csv

OVERLAY_BASE = 0x02219440
OVERLAY_SIZE = 467360
BSS_START = 0x0228B5E0
BSS_SIZE = 1600


def parse_address(value):
    return int(value.strip(), 0)


def ensure_layout():
    base = toAddr(OVERLAY_BASE)
    if currentProgram.getImageBase() != base:
        currentProgram.setImageBase(base, True)

    memory = currentProgram.getMemory()
    bss_address = toAddr(BSS_START)
    block = memory.getBlock(bss_address)
    if block is None:
        memory.createUninitializedBlock("BSS", bss_address, BSS_SIZE, False)
    elif block.getStart() != bss_address or block.getSize() != BSS_SIZE:
        printerr("Existing block overlaps the expected BSS range; leaving it unchanged")


def apply_symbols(csv_path):
    handle = open(csv_path, "rb")
    try:
        reader = csv.DictReader(handle)
        for row in reader:
            address = toAddr(parse_address(row["address"]))
            name = row["name"].strip()
            disassemble(address)
            function = getFunctionAt(address)
            if function is None:
                function = createFunction(address, name)
            elif function.getName().startswith("FUN_"):
                function.setName(name, SourceType.USER_DEFINED)
            createLabel(address, name, True)
            evidence = row.get("evidence", "").strip()
            if evidence:
                setPlateComment(address, evidence)
    finally:
        handle.close()


def main():
    arguments = getScriptArgs()
    if len(arguments) != 1:
        printerr("Usage: ApplyBakuganSymbols.py <analysis/symbols/overlay_0007.csv>")
        return
    ensure_layout()
    apply_symbols(arguments[0])
    println("Applied Bakugan DS overlay 7 layout and candidate symbols")


main()
