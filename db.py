"""Camada de acesso ao banco SQLite que guarda os disparos agendados."""
import sqlite3
from contextlib import closing
from datetime import datetime

from config import DB_PATH


def _connect():
    conn = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Cria a tabela de disparos caso ainda nao exista."""
    with closing(_connect()) as conn, conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS dispatches (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id      TEXT NOT NULL,          -- id numerico ou @usuario do grupo/canal
                chat_label   TEXT,                   -- nome amigavel so para exibir
                msg_type     TEXT NOT NULL,          -- text | photo | video
                text         TEXT,                   -- corpo do texto ou legenda da midia
                media_path   TEXT,                   -- caminho do arquivo enviado (foto/video)
                scheduled_at TEXT NOT NULL,          -- ISO local: 2026-07-13T18:30:00
                repeat       TEXT NOT NULL DEFAULT 'once',   -- once | daily | weekly
                status       TEXT NOT NULL DEFAULT 'pending',-- pending | active | sent | error | canceled
                formatar     INTEGER NOT NULL DEFAULT 0,      -- 0 = texto puro | 1 = negrito/italico/links
                created_by   TEXT,                   -- usuario que agendou o disparo
                error        TEXT,
                created_at   TEXT NOT NULL,
                sent_at      TEXT
            )
            """
        )
        # Migracoes: adiciona colunas novas se o banco for de uma versao antiga.
        cols = [r[1] for r in conn.execute("PRAGMA table_info(dispatches)").fetchall()]
        if "formatar" not in cols:
            conn.execute(
                "ALTER TABLE dispatches ADD COLUMN formatar INTEGER NOT NULL DEFAULT 0"
            )
        if "created_by" not in cols:
            conn.execute("ALTER TABLE dispatches ADD COLUMN created_by TEXT")

        # Tabela de usuarios do painel.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                username      TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                is_admin      INTEGER NOT NULL DEFAULT 0,
                created_at    TEXT NOT NULL
            )
            """
        )


def create_dispatch(**data):
    data.setdefault("created_at", datetime.now().isoformat(timespec="seconds"))
    cols = ", ".join(data.keys())
    placeholders = ", ".join(["?"] * len(data))
    with closing(_connect()) as conn, conn:
        cur = conn.execute(
            f"INSERT INTO dispatches ({cols}) VALUES ({placeholders})",
            list(data.values()),
        )
        return cur.lastrowid


def get_dispatch(dispatch_id):
    with closing(_connect()) as conn, conn:
        row = conn.execute(
            "SELECT * FROM dispatches WHERE id = ?", (dispatch_id,)
        ).fetchone()
        return dict(row) if row else None


def list_dispatches():
    with closing(_connect()) as conn, conn:
        rows = conn.execute(
            "SELECT * FROM dispatches ORDER BY scheduled_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]


def update_dispatch(dispatch_id, **fields):
    if not fields:
        return
    assignments = ", ".join(f"{k} = ?" for k in fields)
    with closing(_connect()) as conn, conn:
        conn.execute(
            f"UPDATE dispatches SET {assignments} WHERE id = ?",
            [*fields.values(), dispatch_id],
        )


def delete_dispatch(dispatch_id):
    with closing(_connect()) as conn, conn:
        conn.execute("DELETE FROM dispatches WHERE id = ?", (dispatch_id,))


# ---------------------------------------------------------------- usuarios ----

def create_user(username, password_hash, is_admin=False):
    with closing(_connect()) as conn, conn:
        conn.execute(
            "INSERT INTO users (username, password_hash, is_admin, created_at) "
            "VALUES (?, ?, ?, ?)",
            (username, password_hash, 1 if is_admin else 0,
             datetime.now().isoformat(timespec="seconds")),
        )


def get_user(username):
    with closing(_connect()) as conn, conn:
        row = conn.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()
        return dict(row) if row else None


def list_users():
    with closing(_connect()) as conn, conn:
        rows = conn.execute(
            "SELECT * FROM users ORDER BY is_admin DESC, username"
        ).fetchall()
        return [dict(r) for r in rows]


def delete_user(user_id):
    with closing(_connect()) as conn, conn:
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))


def count_users():
    with closing(_connect()) as conn, conn:
        return conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
