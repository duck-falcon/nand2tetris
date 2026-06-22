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
        self._filename = ""          # static セグメント用
        self._label_cnt = 0          # eq/gt/lt のユニークラベル用
        self._call_cnt = 0           # call のリターンアドレスラベル用
        self._current_function = ""  # 現在処理中の関数名（label スコープ用）

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

    # ── プログラムフロー命令 ─────────────────────────────────

    def _scoped_label(self, label: str) -> str:
        """現在の関数スコープを付けたラベルを返す。"""
        if self._current_function:
            return f"{self._current_function}${label}"
        return label

    def write_label(self, label: str) -> None:
        self._write([f"// label {label}", f"({self._scoped_label(label)})"])

    def write_goto(self, label: str) -> None:
        self._write([f"// goto {label}", f"@{self._scoped_label(label)}", "0;JMP"])

    def write_if_goto(self, label: str) -> None:
        # スタックのトップをポップして、0 でなければジャンプ
        self._write([f"// if-goto {label}"] + self._pop_d() + [f"@{self._scoped_label(label)}", "D;JNE"])

    # ── 関数命令 ─────────────────────────────────────────────

    # function の変換。実質初期化。
    def write_function(self, name: str, n_locals: int) -> None:
        self._current_function = name
        lines: list[str] = [f"// function {name} {n_locals}", f"({name})"]
        # ローカル変数を 0 で初期化
        for _ in range(n_locals):
            lines += ["D=0"] + self._push_d()
        self._write(lines)

    def write_call(self, name: str, n_args: int) -> None:
        # リターンアドレスラベルを生成
        prefix = self._current_function if self._current_function else "bootstrap"
        ret_label = f"{prefix}$ret.{self._call_cnt}"
        self._call_cnt += 1

        lines: list[str] = [f"// call {name} {n_args}"]

        # リターンアドレスをプッシュ
        lines += [f"@{ret_label}", "D=A"] + self._push_d()
        # 呼び出し元のフレームポインタをプッシュ
        lines += ["@LCL",  "D=M"] + self._push_d()
        lines += ["@ARG",  "D=M"] + self._push_d()
        lines += ["@THIS", "D=M"] + self._push_d()
        lines += ["@THAT", "D=M"] + self._push_d()

        # ARG = SP - 5 - nArgs
        lines += [
            "@SP", "D=M",
            f"@{5 + n_args}", "D=D-A",
            "@ARG", "M=D",
        ]
        # LCL = SP
        lines += ["@SP", "D=M", "@LCL", "M=D"]
        # 関数へジャンプ
        lines += [f"@{name}", "0;JMP"]
        # リターンアドレスラベルを配置
        lines += [f"({ret_label})"]

        self._write(lines)

    def write_return(self) -> None:
        lines: list[str] = ["// return"]

        # R14 = LCL
        lines += ["@LCL", "D=M", "@R14", "M=D"]
        # R15 = RET = *(LCL-5)（RET をR15に待避）
        lines += ["@5", "A=D-A", "D=M", "@R15", "M=D"]
        # *ARG = pop()（戻り値を呼び出し元の arg 0 の位置に配置、ここが天辺となる）
        lines += self._pop_d() + ["@ARG", "A=M", "M=D"]
        # SP = ARG + 1（呼び出し元の SP を復元、上記の天辺が確定）
        lines += ["@ARG", "D=M+1", "@SP", "M=D"]
        # THAT/THIS/ARG/LCL を順に復元する。（R14 を LCL-1, -2, -3, -4 と順次デクリメント）
        lines += ["@R14", "AM=M-1", "D=M", "@THAT", "M=D"]
        lines += ["@R14", "AM=M-1", "D=M", "@THIS", "M=D"]
        lines += ["@R14", "AM=M-1", "D=M", "@ARG",  "M=D"]
        lines += ["@R14", "AM=M-1", "D=M", "@LCL",  "M=D"]
        # リターンアドレスへジャンプ
        lines += ["@R15", "A=M", "0;JMP"]

        self._write(lines)

    # ── ブートストラップ ─────────────────────────────────────

    def write_init(self) -> None:
        """SP=256 に初期化して Sys.init を呼び出すブートストラップコードを出力する。"""
        self._write(["// bootstrap", "@256", "D=A", "@SP", "M=D"])
        self.write_call("Sys.init", 0)

    # ── 出力 ─────────────────────────────────────────────────

    def _write(self, lines: list[str]) -> None:
        self._file.write("\n".join(lines) + "\n")

    def close(self) -> None:
        self._file.close()
