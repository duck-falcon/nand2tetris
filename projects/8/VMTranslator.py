#!/usr/bin/env python3
"""Hack VM Translator — .vm ファイルを Hack アセンブリ (.asm) に変換する。

Usage:
    python VMTranslator.py <file.vm>        # 単一ファイル（ブートストラップなし）
    python VMTranslator.py <directory>      # ディレクトリ（ブートストラップあり）
"""

import glob
import os
import sys

from Parser import Parser
from CodeWriter import CodeWriter


def translate_file(parser: Parser, writer: CodeWriter) -> None:
    while parser.has_more_commands():
        parser.advance()
        cmd_type = parser.command_type()

        if cmd_type == "C_ARITHMETIC":
            writer.write_arithmetic(parser.arg1())
        elif cmd_type in ("C_PUSH", "C_POP"):
            writer.write_push_pop(cmd_type, parser.arg1(), parser.arg2())
        elif cmd_type == "C_LABEL":
            writer.write_label(parser.arg1())
        elif cmd_type == "C_GOTO":
            writer.write_goto(parser.arg1())
        elif cmd_type == "C_IF":
            writer.write_if_goto(parser.arg1())
        elif cmd_type == "C_FUNCTION":
            writer.write_function(parser.arg1(), parser.arg2())
        elif cmd_type == "C_CALL":
            writer.write_call(parser.arg1(), parser.arg2())
        elif cmd_type == "C_RETURN":
            writer.write_return()


def translate(path: str) -> None:
    if os.path.isdir(path):
        dir_path = path.rstrip("/").rstrip("\\")
        dir_name = os.path.basename(dir_path)
        asm_path = os.path.join(dir_path, dir_name + ".asm")

        writer = CodeWriter(asm_path)
        writer.write_init()

        for vm_path in sorted(glob.glob(os.path.join(dir_path, "*.vm"))):
            filename = os.path.basename(vm_path).replace(".vm", "")
            writer.set_filename(filename)
            translate_file(Parser(vm_path), writer)

        writer.close()
        print(f"Translated {path} -> {asm_path}")
    else:
        dir_, base = os.path.split(path)
        filename = base.replace(".vm", "")
        asm_path = os.path.join(dir_, filename + ".asm")

        writer = CodeWriter(asm_path)
        writer.set_filename(filename)
        translate_file(Parser(path), writer)
        writer.close()
        print(f"Translated {path} -> {asm_path}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python VMTranslator.py <file.vm|directory>")
        sys.exit(1)
    translate(sys.argv[1])
