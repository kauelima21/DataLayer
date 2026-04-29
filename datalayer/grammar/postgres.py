from .base import Grammar


class PostgresGrammar(Grammar):
    def placeholder(self, index: int) -> str:
        return f"${index}"

    def compile_insert(self, table, data, primary_key="id"):
        cols = list(data.keys())
        keys = [f":{c}" for c in cols]
        sql = (
            f"INSERT INTO {table} ({', '.join(cols)}) "
            f"VALUES ({', '.join(keys)}) RETURNING *"
        )
        sql, ordered = self.translate(sql, data)
        return sql, ordered, True
