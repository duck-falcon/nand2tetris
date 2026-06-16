#!/usr/bin/env python3
"""Hack VM Translator — .vm ファイルを Hack アセンブリ (.asm) に変換する。

Usage:
    python VMTranslator.py <file.vm>
"""

import os
import sys

from Parser import Parser
from CodeWriter import CodeWriter


def translate(vm_path: str) -> None:
    dir_, base = os.path.split(vm_path)
    filename = base.replace(".vm", "")
    asm_path = os.path.join(dir_, filename + ".asm")

    parser = Parser(vm_path)
    writer = CodeWriter(asm_path)
    writer.set_filename(filename)

    while parser.has_more_commands():
        parser.advance()
        cmd_type = parser.command_type()

        if cmd_type == "C_ARITHMETIC":
            writer.write_arithmetic(parser.arg1())
        elif cmd_type in ("C_PUSH", "C_POP"):
            writer.write_push_pop(cmd_type, parser.arg1(), parser.arg2())

    writer.close()
    print(f"Translated {vm_path} -> {asm_path}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python VMTranslator.py <file.vm>")
        sys.exit(1)
    translate(sys.argv[1])
