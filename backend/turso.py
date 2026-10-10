"""Small libsql DB-API adapter; remote SQLite semantics, no local replica."""
import sqlite3
import libsql


class Row:
    def __init__(self, columns, values):
        self.columns, self.values = columns, values

    def keys(self):
        return self.columns

    def __getitem__(self, key):
        return self.values[self.columns.index(key)] if isinstance(key, str) else self.values[key]

    def __iter__(self):
        return iter(self.values)

    def __len__(self):
        return len(self.values)


def call(function, *args, **kwargs):
    try:
        return function(*args, **kwargs)
    except (ValueError, RuntimeError) as error:
        # libsql reports SQL/network failures as built-in exceptions. Keep the
        # application's existing sanitized SQLite error handling, never tokens.
        message = str(error).lower()
        kind = sqlite3.IntegrityError if 'constraint' in message else sqlite3.DatabaseError
        raise kind('Application database operation failed') from None


class Cursor:
    def __init__(self, cursor):
        self.cursor = cursor

    def __iter__(self):
        while True:
            row = self.fetchone()
            if row is None:
                break
            yield row

    @property
    def rowcount(self):
        return self.cursor.rowcount

    def row(self, values):
        if values is None:
            return None
        return Row([column[0] for column in self.cursor.description], values)

    def fetchone(self):
        return self.row(call(self.cursor.fetchone))

    def fetchall(self):
        return [self.row(values) for values in call(self.cursor.fetchall)]


class Connection:
    def __init__(self, url, token):
        self.connection = call(libsql.connect, url, auth_token=token) if token else call(libsql.connect, url)

    def execute(self, sql, parameters=()):
        return Cursor(call(self.connection.execute, sql, parameters))

    def executescript(self, sql):
        return call(self.connection.executescript, sql)

    def commit(self):
        return call(self.connection.commit)

    def rollback(self):
        return call(self.connection.rollback)

    def close(self):
        return call(self.connection.close)

    def __enter__(self):
        return self

    def __exit__(self, kind, value, traceback):
        self.rollback() if kind else self.commit()
        return False
