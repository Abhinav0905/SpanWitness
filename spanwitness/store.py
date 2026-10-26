"""Local durable records. The directory is excluded from source control."""
from __future__ import annotations

import json
from contextlib import contextmanager
from pathlib import Path
import sqlite3


class Store:
    backend = "local_sqlite"
    def __init__(self, directory: Path):
        self.directory = directory
        self.directory.mkdir(parents=True, exist_ok=True)
        self.images = directory / "images"
        self.images.mkdir(exist_ok=True)
        self.database = directory / "records.sqlite3"
        with self.connection() as connection:
            connection.execute("CREATE TABLE IF NOT EXISTS observations (id TEXT PRIMARY KEY, created TEXT NOT NULL, payload TEXT NOT NULL)")
            connection.execute("CREATE TABLE IF NOT EXISTS tickets (id TEXT PRIMARY KEY, created TEXT NOT NULL, payload TEXT NOT NULL)")
            connection.execute("CREATE TABLE IF NOT EXISTS comparisons (id TEXT PRIMARY KEY, created TEXT NOT NULL, payload TEXT NOT NULL)")

    @contextmanager
    def connection(self):
        connection = sqlite3.connect(self.database, timeout=10)
        connection.row_factory = sqlite3.Row
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def write_image(self, name: str, data: bytes):
        (self.images / name).write_bytes(data)

    def read_image(self, name: str) -> bytes:
        return (self.images / name).read_bytes()

    def save(self, kind: str, record: dict):
        table = self._table(kind)
        with self.connection() as connection:
            connection.execute(f"INSERT INTO {table} (id, created, payload) VALUES (?, ?, ?)",
                               (record["id"], record["created_at"], json.dumps(record)))

    def get(self, kind: str, identifier: str) -> dict | None:
        table = self._table(kind)
        with self.connection() as connection:
            row = connection.execute(f"SELECT payload FROM {table} WHERE id = ?", (identifier,)).fetchone()
        return json.loads(row["payload"]) if row else None

    def list(self, kind: str, limit: int = 100) -> list[dict]:
        table = self._table(kind)
        with self.connection() as connection:
            rows = connection.execute(f"SELECT payload FROM {table} ORDER BY created DESC LIMIT ?", (limit,)).fetchall()
        return [json.loads(row["payload"]) for row in rows]

    @staticmethod
    def _table(kind: str) -> str:
        if kind not in {"observations", "tickets", "comparisons"}:
            raise ValueError("Unsupported record type.")
        return kind
