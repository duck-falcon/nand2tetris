#!/usr/bin/env python3
"""Hack assembler — symbol-less (basic) version."""

import os
import sys

# Destination bits: dest -> [d1, d2, d3]
DEST = {
    None:  "000",
    "M":   "001",
    "D":   "010",
    "DM":  "011",
    "A":   "100",
    "AM":  "101",
    "AD":  "110",
    "ADM": "111",
}

# Jump bits
JUMP = {
    None:  "000",
    "JGT": "001",
    "JEQ": "010",
    "JGE": "011",
    "JLT": "100",
    "JNE": "101",
    "JLE": "110",
    "JMP": "111",
}

# Computation bits: comp -> (a-bit, c1..c6)
COMP = {
    "0":   ("0", "101010"),
    "1":   ("0", "111111"),
    "-1":  ("0", "111010"),
    "D":   ("0", "001100"),
    "A":   ("0", "110000"),
    "M":   ("1", "110000"),
    "!D":  ("0", "001101"),
    "!A":  ("0", "110001"),
    "!M":  ("1", "110001"),
    "-D":  ("0", "001111"),
    "-A":  ("0", "110011"),
    "-M":  ("1", "110011"),
    "D+1": ("0", "011111"),
    "A+1": ("0", "110111"),
    "M+1": ("1", "110111"),
    "D-1": ("0", "001110"),
    "A-1": ("0", "110010"),
    "M-1": ("1", "110010"),
    "D+A": ("0", "000010"),
    "D+M": ("1", "000010"),
    "D-A": ("0", "010011"),
    "D-M": ("1", "010011"),
    "A-D": ("0", "000111"),
    "M-D": ("1", "000111"),
    "D&A": ("0", "000000"),
    "D&M": ("1", "000000"),
    "D|A": ("0", "010101"),
    "D|M": ("1", "010101"),
}


def strip_line(line: str) -> str:
    """Remove comments and whitespace."""
    return line.split("//")[0].strip()


def parse_a(instruction: str) -> str:
    """@value -> 16-bit binary string."""
    value = int(instruction[1:])
    return format(value, "016b")


def parse_c(instruction: str) -> str:
    """dest=comp;jump -> 16-bit binary string."""
    if "=" in instruction:
        dest_str, rest = instruction.split("=", 1)
    else:
        dest_str, rest = None, instruction

    if ";" in rest:
        comp_str, jump_str = rest.split(";", 1)
    else:
        comp_str, jump_str = rest, None

    a_bit, c_bits = COMP[comp_str]
    d_bits = DEST[dest_str]
    j_bits = JUMP[jump_str]

    return "111" + a_bit + c_bits + d_bits + j_bits


def assemble(src_path: str) -> None:
    dir_, base = os.path.split(src_path)
    dst_path = os.path.join(dir_, "my" + base.replace(".asm", ".hack"))

    with open(src_path) as f:
        lines = f.readlines()

    output = []
    for line in lines:
        clean = strip_line(line)
        if not clean:
            continue
        if clean.startswith("@"):
            output.append(parse_a(clean))
        else:
            output.append(parse_c(clean))

    with open(dst_path, "w") as f:
        f.write("\n".join(output) + "\n")

    print(f"Assembled {src_path} -> {dst_path} ({len(output)} instructions)")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python asm.py <file.asm>")
        sys.exit(1)
    assemble(sys.argv[1])
