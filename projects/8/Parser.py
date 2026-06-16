"""VM Parser — .vm ファイルの1行を解析する。"""


class Parser:
    def __init__(self, path: str) -> None:
        with open(path) as f:
            raw = f.readlines()
        # コメント・空行を除去
        self._commands = [
            line.split("//")[0].strip()
            for line in raw
        ]
        self._commands = [l for l in self._commands if l]
        self._index = -1
        self._current: str = ""

    def has_more_commands(self) -> bool:
        return self._index < len(self._commands) - 1

    def advance(self) -> None:
        self._index += 1
        self._current = self._commands[self._index]

    def command_type(self) -> str:
        first = self._current.split()[0]
        if first == "push":
            return "C_PUSH"
        if first == "pop":
            return "C_POP"
        return "C_ARITHMETIC"

    def arg1(self) -> str:
        """算術命令ならコマンド自身、push/pop ならセグメント名を返す。"""
        parts = self._current.split()
        if self.command_type() == "C_ARITHMETIC":
            return parts[0]
        return parts[1]

    def arg2(self) -> int:
        """push/pop のインデックスを返す。"""
        return int(self._current.split()[2])
