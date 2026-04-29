# aiodatalayer

ORM mínimo no estilo **ActiveRecord**, totalmente assíncrono, inspirado no [DataLayer (PHP)](https://github.com/robsonvleite/datalayer) do **Robson V. Leite / CoffeeCode**. Suporte nativo a **MariaDB/MySQL** (`asyncmy`) e **PostgreSQL** (`asyncpg`), zero configuração no código — tudo via variáveis de ambiente.

> **Pacote PyPI:** `aiodatalayer` · **Import:** `from datalayer import DataLayer`

###### O DataLayer é uma camada de persistência que abstrai o CRUD do seu banco. Você modela uma tabela em poucas linhas e ganha leitura, escrita, atualização e remoção encadeáveis e seguras.

---

## Highlights

- API encadeável e enxuta (`find().order().limit().fetch()`)
- INSERT/UPDATE automático no `save()`
- Validação de campos obrigatórios
- Timestamps automáticos (`created_at` / `updated_at`)
- Conversão de `datetime`/`date`/`time` para ISO 8601 na leitura
- Timezone configurável (default `America/Sao_Paulo`)
- Suporte multi-driver (MariaDB + Postgres) via mesma interface
- Exceções tipadas (`ValidationError`, `ConnectionError`, `QueryError`)
- 100% async/await
- Cobertura de testes com driver fake (sem precisar de banco real)

---

## Instalação

```bash
pip install aiodatalayer
```

Ou com [uv](https://github.com/astral-sh/uv):

```bash
uv add aiodatalayer
```

Para desenvolvimento local:

```bash
uv pip install -e ".[dev]"
```

### Dependências

| Pacote | Finalidade |
|--------|-----------|
| `asyncmy` | Driver async MariaDB/MySQL |
| `asyncpg` | Driver async PostgreSQL |

---

## Configuração

Crie um `.env` na raiz do projeto:

```dotenv
DATA_LAYER_DRIVER=mariadb          # "mariadb" ou "postgres"
DATA_LAYER_HOST=localhost
DATA_LAYER_PORT=3306               # 3306 mariadb | 5432 postgres
DATA_LAYER_DATABASE=meu_banco
DATA_LAYER_USER=app
DATA_LAYER_PASSWORD=secret

DATA_LAYER_POOL_MIN=1              # opcional, default 1
DATA_LAYER_POOL_MAX=10             # opcional, default 10

DATA_LAYER_TIMEZONE=America/Sao_Paulo  # opcional, default America/Sao_Paulo
```

A lib lê as variáveis de ambiente diretamente e gerencia o pool internamente — não há `connect()` ou `disconnect()` explícito. Você carrega o `.env` da forma que preferir (`python-dotenv`, `os.environ`, Docker, shell `export`, etc.):

```python
from dotenv import load_dotenv
load_dotenv()  # antes de importar datalayer

from datalayer import DataLayer
```

### Subindo um MariaDB local com Docker

```bash
docker run -d \
  --name datalayer-mariadb \
  -p 3306:3306 \
  -e MARIADB_ROOT_PASSWORD=root_password \
  -e MARIADB_DATABASE=local_db \
  -e MARIADB_USER=local_user \
  -e MARIADB_PASSWORD=local_password \
  -v datalayer-mariadb-data:/var/lib/mysql \
  --restart unless-stopped \
  mariadb:11
```

---

## Definindo um Model

Você pode declarar via **atributos de classe** ou via **`super().__init__()`** — ambos funcionam.

```python
from datalayer import DataLayer

class User(DataLayer):
    table = "users"
    required = ["first_name", "last_name", "email"]
    primary_key = "id"     # default: "id"
    timestamps = True       # default: True
```

ou

```python
class User(DataLayer):
    def __init__(self):
        # table, required, primary_key, timestamps
        super().__init__("users", ["first_name", "last_name"], "id", True)
```

### Timestamps automáticos

Quando `timestamps = True`, a lib espera as colunas `created_at` e `updated_at` na tabela:

| Coluna | Tipo SQL | Comportamento |
|--------|----------|---------------|
| `created_at` | `TIMESTAMP` | Preenchido no INSERT, nunca alterado |
| `updated_at` | `TIMESTAMP` | Preenchido no INSERT, atualizado a cada UPDATE |

O valor é gerado em `datetime.now(<timezone>)` segundo a TZ configurada.

---

## API

### `find(condition?, **params)`

Monta a cláusula `WHERE`. Retorna `self` para encadeamento.

```python
# todos os registros
await User().find().fetch(True)

# com filtro e named params
await User().find("id = :id", id=5).fetch()
await User().find("role = :role AND active = :active", role="admin", active=True).fetch(True)
```

Os placeholders `:nome` são traduzidos internamente para `$1, $2…` (Postgres) ou `%s` (MariaDB).

---

### `find_by_id(id)`

Atalho para `find("id = :id", id=id)` **já com fetch automático**. Retorna o registro hidratado (ou `None`).

```python
user = await User().find_by_id(2)
print(user.first_name)
```

---

### `fetch(all=False)`

Executa o SELECT após `find()`.

```python
# um registro
user = await User().find("id = :id", id=5).fetch()

# todos os registros
users = await User().find().fetch(all=True)

# encadeamento completo
users = (
    await User()
    .find("role = :role", role="admin")
    .order("name ASC")
    .limit(10)
    .fetch(all=True)
)
```

- `fetch()` → instância do model (ou `None`)
- `fetch(True)` → `list[dict]` (lista vazia se nada bater)

---

### `limit(n)` / `offset(n)` / `order(clause)`

```python
await User().find().order("name ASC").limit(10).offset(20).fetch(True)
await User().find().order("created_at DESC").fetch(True)
```

---

### `in_(column, values)`

Cláusula `IN`. Nome com underscore para não conflitar com a keyword `in` do Python.

```python
await User().find().in_("id", [1, 2, 3]).fetch(True)

# combinado com find
await User().find("role = :role", role="admin").in_("id", [1, 2, 3]).fetch(True)
```

---

### `count()`

Total de registros da query atual.

```python
total = await User().find().count()
admins = await User().find("role = :role", role="admin").count()
```

---

### `save()`

INSERT ou UPDATE — decidido automaticamente pela presença do `primary_key` nos dados.

```python
# CREATE
user = User()
user.first_name = "Robson"
user.last_name = "Leite"
user.email = "robson@exemplo.com"
saved = await user.save()
print(saved.id)

# UPDATE
user = await User().find_by_id(1)
user.first_name = "Robson V."
await user.save()
```

**Comportamento:**
- Valida `required` antes da execução — lança `ValidationError`
- INSERT popula `created_at` e `updated_at`
- UPDATE atualiza apenas `updated_at`
- Re-busca o registro após a operação e retorna o model hidratado

---

### `destroy()`

Remove o(s) registro(s) da query atual.

```python
# por id
user = await User().find_by_id(5)
await user.destroy()

# em lote
await User().find("active = :active", active=False).destroy()
```

- Retorna `True` se ao menos um registro foi removido, `False` caso contrário.

---

### `data()`

Retorna um `dict` (cópia) com os dados da instância — útil para serialização.

```python
user = await User().find_by_id(1)
print(user.data())
# {"id": 1, "first_name": "Robson", "created_at": "2026-04-29T09:00:00", ...}
```

Datas (`datetime`/`date`/`time`) são automaticamente convertidas para ISO 8601 na timezone configurada.

---

### Métodos customizados no model

```python
class User(DataLayer):
    table = "users"
    required = ["first_name", "last_name"]

    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"
```

```python
user = await User().find_by_id(1)
print(user.full_name())
```

---

## Encadeamento completo

Modificadores podem ser combinados em qualquer ordem antes de `fetch()`:

```python
users = (
    await User()
    .find("role = :role", role="admin")
    .in_("id", [1, 2, 3, 4, 5])
    .order("name ASC")
    .limit(10)
    .offset(0)
    .fetch(all=True)
)
```

---

## Timezone

Por padrão a lib opera em **`America/Sao_Paulo`**. Mude via `.env`:

```dotenv
DATA_LAYER_TIMEZONE=UTC
```

ou programaticamente:

```python
from datalayer import Connection
Connection.set_timezone("Europe/Lisbon")
```

Aceita qualquer TZ válida no [IANA tz database](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones).

`datetime` aware retornado pelo driver é convertido para a TZ configurada antes do `isoformat()`. `datetime` naive é tratado como já estando na TZ configurada.

---

## Tratamento de erros

```python
from datalayer import (
    DataLayerError,
    ValidationError,
    ConnectionError,
    QueryError,
)

try:
    await user.save()
except ValidationError as e:
    print(e)  # "Campo 'email' e obrigatorio"
except QueryError as e:
    print(e)  # erro do driver / SQL invalido
except DataLayerError as e:
    print(e)  # qualquer erro da lib
```

| Exception | Quando ocorre |
|-----------|--------------|
| `ValidationError` | Campo obrigatório ausente no `save()` |
| `ConnectionError` | Falha ao conectar / pool indisponível |
| `QueryError` | Erro de SQL retornado pelo driver |

Todas herdam de `DataLayerError`.

---

## Testes

```bash
uv pip install -e ".[dev]"
uv run pytest
```

Os testes usam um driver em memória (`tests/fake_driver.py`) — não precisam de banco real.

```
50 passed in 0.07s
```

---

## Arquitetura

```
datalayer/
├── __init__.py            # carrega .env, expõe DataLayer + exceções
├── connection.py          # singleton de pool, TZ, env vars
├── model.py               # ActiveRecord base
├── exceptions.py
├── grammar/
│   ├── base.py            # SQL builder + tradução de :name
│   ├── postgres.py        # placeholder $1..$N
│   └── mariadb.py         # placeholder %s
└── drivers/
    ├── base.py            # AsyncDriver ABC
    ├── postgres.py        # wrapper asyncpg
    └── mariadb.py         # wrapper asyncmy
```

### Fluxo de uma query

```
User().find("role = :role", role="admin").order("name ASC").limit(10).fetch(True)
  │
  ├─ find()       → armazena condition + params
  ├─ order()      → armazena ORDER BY
  ├─ limit()      → armazena LIMIT
  ├─ fetch(True)  → grammar.compile_select(...)
  ├─ grammar      → traduz :role → $1 / %s, monta SQL
  ├─ driver       → executa via pool, retorna rows
  └─ fetch        → normaliza datetime/date/time → ISO string
```

---

## Fora do escopo (v1)

- JOINs e eager loading
- Migrations / schema builder
- Soft delete
- Hooks / eventos (`before_save`, `after_save`)
- Suporte a SQLite

---

## Créditos

- Implementação Python: **Kauê Leal**
- Inspirado no [DataLayer PHP](https://github.com/robsonvleite/datalayer) de [Robson V. Leite](https://github.com/robsonvleite) e [UpInside Treinamentos](https://github.com/upinside)

---

## Licença

MIT.
