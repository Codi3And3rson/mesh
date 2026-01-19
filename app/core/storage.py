"""Persistence layer for task history storage."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class TaskHistoryRecord:
    """Represents a stored Meshy task history entry."""

    task_id: str
    created_at: str
    status: str
    progress: Optional[float]
    thumbnail_url: Optional[str]
    model_urls: Dict[str, object]
    options: Dict[str, object]
    local_glb_path: Optional[str]


class TaskStorage:
    """Stores Meshy task history in SQLite."""

    def __init__(self, database_path: str) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def initialize(self) -> None:
        """Initialize the persistence backend."""
        with sqlite3.connect(self.database_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    created_at TEXT,
                    status TEXT,
                    progress REAL,
                    thumbnail_url TEXT,
                    model_urls_json TEXT,
                    options_json TEXT,
                    local_glb_path TEXT
                )
                """
            )

    def upsert(self, record: TaskHistoryRecord) -> None:
        """Insert or update a task history record."""
        with sqlite3.connect(self.database_path) as conn:
            conn.execute(
                """
                INSERT INTO tasks (
                    task_id,
                    created_at,
                    status,
                    progress,
                    thumbnail_url,
                    model_urls_json,
                    options_json,
                    local_glb_path
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(task_id) DO UPDATE SET
                    created_at=excluded.created_at,
                    status=excluded.status,
                    progress=excluded.progress,
                    thumbnail_url=excluded.thumbnail_url,
                    model_urls_json=excluded.model_urls_json,
                    options_json=excluded.options_json,
                    local_glb_path=excluded.local_glb_path
                """,
                (
                    record.task_id,
                    record.created_at,
                    record.status,
                    record.progress,
                    record.thumbnail_url,
                    json.dumps(record.model_urls),
                    json.dumps(record.options),
                    record.local_glb_path,
                ),
            )

    def list_all(self) -> List[TaskHistoryRecord]:
        """Return all stored task history records."""
        with sqlite3.connect(self.database_path) as conn:
            rows = conn.execute(
                """
                SELECT task_id, created_at, status, progress, thumbnail_url,
                       model_urls_json, options_json, local_glb_path
                FROM tasks
                ORDER BY created_at DESC
                """
            ).fetchall()
        return [self._row_to_record(row) for row in rows]

    def fetch_by_id(self, task_id: str) -> Optional[TaskHistoryRecord]:
        """Fetch a task record by id."""
        with sqlite3.connect(self.database_path) as conn:
            row = conn.execute(
                """
                SELECT task_id, created_at, status, progress, thumbnail_url,
                       model_urls_json, options_json, local_glb_path
                FROM tasks
                WHERE task_id = ?
                """,
                (task_id,),
            ).fetchone()
        if not row:
            return None
        return self._row_to_record(row)

    def _row_to_record(self, row: tuple) -> TaskHistoryRecord:
        return TaskHistoryRecord(
            task_id=row[0],
            created_at=row[1],
            status=row[2],
            progress=row[3],
            thumbnail_url=row[4],
            model_urls=json.loads(row[5]) if row[5] else {},
            options=json.loads(row[6]) if row[6] else {},
            local_glb_path=row[7],
        )


def init_db(database_path: str) -> None:
    """Initialize the task history database at the given path."""
    TaskStorage(database_path)


def upsert_task(
    database_path: str,
    task_id: str,
    created_at: str,
    status: str,
    progress: Optional[float],
    thumbnail_url: Optional[str],
    model_urls_json: str,
    options_json: str,
    local_glb_path: Optional[str],
) -> None:
    """Insert or update a task record in the database."""
    storage = TaskStorage(database_path)
    record = TaskHistoryRecord(
        task_id=task_id,
        created_at=created_at,
        status=status,
        progress=progress,
        thumbnail_url=thumbnail_url,
        model_urls=json.loads(model_urls_json) if model_urls_json else {},
        options=json.loads(options_json) if options_json else {},
        local_glb_path=local_glb_path,
    )
    storage.upsert(record)


def list_tasks(database_path: str, limit: int = 200) -> List[TaskHistoryRecord]:
    """Return stored tasks ordered by most recent."""
    with sqlite3.connect(database_path) as conn:
        rows = conn.execute(
            """
            SELECT task_id, created_at, status, progress, thumbnail_url,
                   model_urls_json, options_json, local_glb_path
            FROM tasks
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [TaskStorage(database_path)._row_to_record(row) for row in rows]


def get_task(database_path: str, task_id: str) -> Optional[TaskHistoryRecord]:
    """Fetch a task record by id."""
    return TaskStorage(database_path).fetch_by_id(task_id)
