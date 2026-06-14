"""VM CodeWriter — VM コマンドを Hack アセンブリに変換して書き出す。"""

# セグメント名 → Hack シンボル（LCL/ARG/THIS/THAT）
SEG_SYMBOL = {
    "local":    "LCL",
    "argument": "ARG",
    "this":     "THIS",
    "that":     "THAT",
}


class CodeWriter:
    def __init__(self, path: str) -> None:
        self._file = open(path, "w")
        self._filename = ""   # static セグメント用
        self._label_cnt = 0   # eq/gt/lt のユニークラベル用

    def set_filename(self, filename: str) -> None:
        """static 変数のプレフィックスに使うファイル名（拡張子なし）を設定する。"""
        self._filename = filename

    # ── スタック操作ヘルパー ─────────────────────────────────

    def _push_d(self) -> list[str]:
        """D レジスタの値をスタックに積む。"""
        return [
            "@SP",
            "A=M",
            "M=D",
            "@SP",
            "M=M+1",
        ]

    def _pop_d(self) -> list[str]:
        """スタックのトップを D レジスタにポップする。"""
        return [
            "@SP",
            "AM=M-1",
            "D=M",
        ]

    # ── 算術・論理命令 ───────────────────────────────────────

    def write_arithmetic(self, command: str) -> None:
        lines: list[str] = [f"// {command}"]

        # AM=M-1 は SP を一つ戻しつつそこにアクセスできるようにしている
        if command == "add":
            lines += ["@SP", "AM=M-1", "D=M", "A=A-1", "M=M+D"]
        elif command == "sub":
            lines += ["@SP", "AM=M-1", "D=M", "A=A-1", "M=M-D"]
        # SP はそのまま
        elif command == "neg":
            lines += ["@SP", "A=M-1", "M=-M"]
        elif command == "not":
            lines += ["@SP", "A=M-1", "M=!M"]
        elif command == "and":
            lines += ["@SP", "AM=M-1", "D=M", "A=A-1", "M=D&M"]
        elif command == "or":
            lines += ["@SP", "AM=M-1", "D=M", "A=A-1", "M=D|M"]
        elif command in ("eq", "gt", "lt"):
            lines += self._write_comparison(command)
        else:
            raise ValueError(f"Unknown arithmetic command: {command}")

        self._write(lines)

    # x, y, (sp) -> true or false, (sp) にする。
    def _write_comparison(self, command: str) -> list[str]:
        jump = {"eq": "JEQ", "gt": "JGT", "lt": "JLT"}[command]
        n = self._label_cnt
        self._label_cnt += 1
        true_label = f"TRUE_{n}"
        end_label  = f"END_{n}"
        return [
            "@SP", "AM=M-1", "D=M",   # D = y
            "A=A-1",                   # A → x のアドレス
            "D=M-D",                   # D = x - y
            f"@{true_label}",
            f"D;{jump}",
            # false
            "@SP", "A=M-1", "M=0",
            f"@{end_label}", "0;JMP",
            # true
            f"({true_label})",
            "@SP", "A=M-1", "M=-1",
            f"({end_label})",
        ]

    # ── push / pop ───────────────────────────────────────────

    def write_push_pop(self, command: str, segment: str, index: int) -> None:
        verb = "push" if command == "C_PUSH" else "pop"
        lines: list[str] = [f"// {verb} {segment} {index}"]

        if command == "C_PUSH":
            lines += self._push(segment, index)
        else:
            lines += self._pop(segment, index)

        self._write(lines)

    def _push(self, segment: str, index: int) -> list[str]:
        if segment == "constant":
            return [f"@{index}", "D=A"] + self._push_d()

        if segment in SEG_SYMBOL:
            sym = SEG_SYMBOL[segment]
            return [
                f"@{index}", "D=A", # base ポインタからの offset
                f"@{sym}", "A=M+D", "D=M", # D = base + インデックスのアドレスの中身
            ] + self._push_d()

        if segment == "temp":
            return [f"@{5 + index}", "D=M"] + self._push_d() # 定数ポインタ？的な感じなので簡単

        if segment == "pointer":
            sym = "THIS" if index == 0 else "THAT"
            return [f"@{sym}", "D=M"] + self._push_d() # temp と変わらん、簡単

        if segment == "static":
            return [f"@{self._filename}.{index}", "D=M"] + self._push_d() # file またぎの static。簡単。

        raise ValueError(f"Unknown segment: {segment}")

    def _pop(self, segment: str, index: int) -> list[str]:
        if segment in SEG_SYMBOL:
            sym = SEG_SYMBOL[segment]
            # アドレスを R13 に退避してからポップ
            return [
                f"@{index}", "D=A",
                f"@{sym}", "D=M+D", # D=base+インデックスのアドレス
                "@R13", "M=D", # R13 に待避
            ] + self._pop_d() + [ # スタックから pop する
                "@R13", "A=M", "M=D", # base+インデックスのアドレスに pop した値を突っ込む
            ]

        if segment == "temp":
            return self._pop_d() + [f"@{5 + index}", "M=D"]

        if segment == "pointer":
            sym = "THIS" if index == 0 else "THAT"
            return self._pop_d() + [f"@{sym}", "M=D"]

        if segment == "static":
            return self._pop_d() + [f"@{self._filename}.{index}", "M=D"]

        raise ValueError(f"Unknown segment: {segment}")

    # ── 出力 ─────────────────────────────────────────────────

    def _write(self, lines: list[str]) -> None:
        self._file.write("\n".join(lines) + "\n")

    def close(self) -> None:
        self._file.close()
