#!/usr/bin/env python3
"""Hack assembler — full 2-pass version with symbol table."""

import os
import sys

# ── コード表 ────────────────────────────────────────────────

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

# 事前定義シンボル
PREDEFINED = {
    "SP": 0, "LCL": 1, "ARG": 2, "THIS": 3, "THAT": 4,
    "SCREEN": 16384, "KBD": 24576,
    **{f"R{i}": i for i in range(16)},
}

# ── ユーティリティ ────────────────────────────────────────

def strip_line(line: str) -> str:
    return line.split("//")[0].strip()


def parse_c(instruction: str) -> str:
    dest_str, rest = instruction.split("=", 1) if "=" in instruction else (None, instruction)
    comp_str, jump_str = rest.split(";", 1) if ";" in rest else (rest, None)
    a_bit, c_bits = COMP[comp_str]
    return "111" + a_bit + c_bits + DEST[dest_str] + JUMP[jump_str]


# ── 2パスアセンブル ───────────────────────────────────────

def assemble(src_path: str) -> None:
    with open(src_path) as f:
        raw_lines = f.readlines()

    clean_lines = [strip_line(l) for l in raw_lines]
    clean_lines = [l for l in clean_lines if l]

    # ── パス1: ラベル (LABEL) を ROM アドレスに登録 ──
    symbol_table = dict(PREDEFINED)
    rom_addr = 0
    for line in clean_lines:
        if line.startswith("(") and line.endswith(")"):
            symbol_table[line[1:-1]] = rom_addr
        else:
            rom_addr += 1

    # ── パス2: 命令を機械語に変換 ──
    next_var_addr = 16
    output = []

    for line in clean_lines:
        if line.startswith("("):
            continue

        if line.startswith("@"):
            symbol = line[1:]
            if symbol.isdigit():
                value = int(symbol)
            elif symbol in symbol_table:
                value = symbol_table[symbol]
            else:
                # 変数
                symbol_table[symbol] = next_var_addr
                value = next_var_addr
                next_var_addr += 1
            output.append(format(value, "016b"))
        else:
            output.append(parse_c(line))

    dir_, base = os.path.split(src_path)
    dst_path = os.path.join(dir_, "my" + base.replace(".asm", ".hack"))
    with open(dst_path, "w") as f:
        f.write("\n".join(output) + "\n")

    print(f"Assembled {src_path} -> {dst_path} ({len(output)} instructions)")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python assembler.py <file.asm>")
        sys.exit(1)
    assemble(sys.argv[1])
