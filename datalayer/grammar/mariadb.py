from .base import Grammar


class MariaDBGrammar(Grammar):
    def placeholder(self, index: int) -> str:
        # asyncmy usa paramstyle "pyformat" — espera %s, nao ?
        return "%s"

    def quote_ident(self, name: str) -> str:
        return f"`{name}`" if "`" not in name else name
