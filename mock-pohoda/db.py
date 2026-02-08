"""SQLite storage for received Pohoda XML documents."""

import sqlite3
import threading
from datetime import datetime


class DocumentStore:
    """Thread-safe SQLite storage for Pohoda documents."""

    def __init__(self, db_path: str = "/data/pohoda.db"):
        self.db_path = db_path
        self._local = threading.local()
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(self.db_path)
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn

    def _init_db(self) -> None:
        conn = self._get_conn()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                doc_type TEXT,
                doc_number TEXT,
                pohoda_id INTEGER,
                company_name TEXT,
                ico TEXT,
                xml_request TEXT,
                xml_response TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS id_counter (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                next_id INTEGER DEFAULT 10001
            )
        """)
        conn.execute("INSERT OR IGNORE INTO id_counter (id, next_id) VALUES (1, 10001)")
        conn.commit()

    def get_next_pohoda_id(self) -> int:
        conn = self._get_conn()
        cursor = conn.execute("UPDATE id_counter SET next_id = next_id + 1 WHERE id = 1 RETURNING next_id - 1")
        row = cursor.fetchone()
        conn.commit()
        return row[0]

    def save_document(
        self,
        doc_type: str,
        doc_number: str,
        company_name: str,
        ico: str,
        xml_request: str,
        xml_response: str,
        pohoda_id: int,
    ) -> int:
        conn = self._get_conn()
        cursor = conn.execute(
            """
            INSERT INTO documents (doc_type, doc_number, company_name, ico, xml_request, xml_response, pohoda_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (doc_type, doc_number, company_name, ico, xml_request, xml_response, pohoda_id, datetime.now().isoformat()),
        )
        conn.commit()
        return cursor.lastrowid or 0

    def get_all_documents(self, limit: int = 100) -> list[dict]:
        conn = self._get_conn()
        cursor = conn.execute(
            "SELECT * FROM documents ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_document(self, doc_id: int) -> dict | None:
        conn = self._get_conn()
        cursor = conn.execute("SELECT * FROM documents WHERE id = ?", (doc_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_stats(self) -> dict:
        conn = self._get_conn()
        total = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
        by_type = {}
        for row in conn.execute("SELECT doc_type, COUNT(*) as cnt FROM documents GROUP BY doc_type"):
            by_type[row[0]] = row[1]
        return {"total": total, "by_type": by_type}
