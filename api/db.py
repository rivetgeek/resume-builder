import json
import os
import sqlite3
from contextlib import contextmanager
from typing import Any, Generator, Optional

import api.config as app_config


SCHEMA = """
CREATE TABLE IF NOT EXISTS submissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    template_name TEXT NOT NULL,
    data_file TEXT NOT NULL,
    pdf_variant TEXT,
    ats_check_run INTEGER NOT NULL,
    ats_errors_count INTEGER,
    ats_warnings_count INTEGER,
    ats_suggestions_count INTEGER,
    output_formats TEXT NOT NULL,
    output_hash TEXT,
    role_id TEXT,
    notes TEXT,
    submission_uuid TEXT UNIQUE
);
CREATE INDEX IF NOT EXISTS idx_submissions_created ON submissions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_submissions_role ON submissions(role_id) WHERE role_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_submissions_uuid ON submissions(submission_uuid);
"""


def init_db() -> None:
    path = app_config.db_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.executescript(SCHEMA)
        _migrate(conn)


def _migrate(conn: sqlite3.Connection) -> None:
    cur = conn.execute("PRAGMA table_info(submissions)")
    cols = {row[1] for row in cur.fetchall()}
    if "submission_uuid" not in cols:
        conn.execute("ALTER TABLE submissions ADD COLUMN submission_uuid TEXT")
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_submissions_uuid ON submissions(submission_uuid)")


@contextmanager
def get_conn() -> Generator[sqlite3.Connection, None, None]:
    conn = sqlite3.connect(app_config.db_path(), timeout=30)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        yield conn
        conn.commit()
    finally:
        conn.close()


def insert_submission(
    *,
    submission_uuid: str,
    template_name: str,
    data_file: str,
    pdf_variant: Optional[str],
    ats_check_run: bool,
    ats_errors: Optional[int],
    ats_warnings: Optional[int],
    ats_suggestions: Optional[int],
    output_formats: list[str],
    output_hash: Optional[str],
    role_id: Optional[str],
    notes: Optional[str],
    created_at_iso: str,
) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO submissions (
                created_at, template_name, data_file, pdf_variant, ats_check_run,
                ats_errors_count, ats_warnings_count, ats_suggestions_count,
                output_formats, output_hash, role_id, notes, submission_uuid
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                created_at_iso,
                template_name,
                data_file,
                pdf_variant,
                1 if ats_check_run else 0,
                ats_errors,
                ats_warnings,
                ats_suggestions,
                json.dumps(output_formats),
                output_hash,
                role_id,
                notes,
                submission_uuid,
            ),
        )
        return int(cur.lastrowid)


def list_submissions(
    limit: int = 25,
    offset: int = 0,
    template_id: Optional[str] = None,
    data_file_id: Optional[str] = None,
) -> tuple[list[dict[str, Any]], int]:
    where: list[str] = []
    params: list[Any] = []
    if template_id:
        where.append("template_name = ?")
        params.append(template_id)
    if data_file_id:
        where.append("data_file = ?")
        params.append(data_file_id)
    wh = (" WHERE " + " AND ".join(where)) if where else ""

    with get_conn() as conn:
        total = conn.execute(f"SELECT COUNT(*) FROM submissions{wh}", params).fetchone()[0]
        rows = conn.execute(
            f"SELECT * FROM submissions{wh} ORDER BY created_at DESC LIMIT ? OFFSET ?",
            [*params, limit, offset],
        ).fetchall()
    items = []
    for r in rows:
        d = dict(r)
        d["output_formats"] = json.loads(d["output_formats"])
        d["ats_check_run"] = bool(d["ats_check_run"])
        items.append(d)
    return items, int(total)


def update_notes(row_id: int, notes: str) -> None:
    with get_conn() as conn:
        conn.execute("UPDATE submissions SET notes = ? WHERE id = ?", (notes, row_id))


def delete_submission(row_id: int) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM submissions WHERE id = ?", (row_id,))


def get_by_uuid(submission_uuid: str) -> Optional[dict[str, Any]]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM submissions WHERE submission_uuid = ?", (submission_uuid,)
        ).fetchone()
    if not row:
        return None
    d = dict(row)
    d["output_formats"] = json.loads(d["output_formats"])
    d["ats_check_run"] = bool(d["ats_check_run"])
    return d
