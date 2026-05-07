from peewee import SqliteDatabase


db = SqliteDatabase(None)


def init_database(database_path: str) -> None:
    db.init(database_path, pragmas={"journal_mode": "wal", "foreign_keys": 1})


def connect_database() -> None:
    if db.is_closed():
        db.connect(reuse_if_open=True)


def close_database() -> None:
    if not db.is_closed():
        db.close()
