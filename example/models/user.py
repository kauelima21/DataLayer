from datalayer import DataLayer


class User(DataLayer):
    def __init__(self) -> None:
        super().__init__("users", ["first_name", "last_name"])
