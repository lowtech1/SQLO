"""
my_exp/core/db_connection.py
============================
Pure PostgreSQL connection utilities — no UI dependencies.
Extracted from my_exp.ui.schema_explorer to decouple from Streamlit.

Functions:
- get_connection()      — create a psycopg2 connection
- execute_query()       — execute SQL, return structured results
- load_schema_data()    — introspect full DB schema (tables, columns, PK/FK)
"""

from __future__ import annotations

import psycopg2
from typing import Optional
from dataclasses import dataclass, field


# ── Dataclasses ────────────────────────────────────────────────────────────────

@dataclass
class ColumnInfo:
    name: str
    data_type: str
    nullable: bool = True
    is_pk: bool = False
    is_fk: bool = False
    fk_ref: str = ""


@dataclass
class TableInfo:
    name: str
    schema: str = "public"
    rows: int = 0
    columns: list[ColumnInfo] = field(default_factory=list)


@dataclass
class SchemaData:
    db_name: str
    tables: list[TableInfo] = field(default_factory=list)
    connected: bool = False
    error: str = ""


# ── Connection ────────────────────────────────────────────────────────────────

def get_connection(
    host: str,
    port: int,
    dbname: str,
    user: str,
    password: str,
    timeout: int = 10,
) -> psycopg2.extensions.connection:
    """
    Create and return a psycopg2 connection.
    Raises psycopg2.Error on failure.
    """
    return psycopg2.connect(
        host=host,
        port=port,
        dbname=dbname,
        user=user,
        password=password,
        connect_timeout=timeout,
    )


# ── Query execution ────────────────────────────────────────────────────────────

def execute_query(
    conn: psycopg2.extensions.connection,
    sql: str,
    timeout_sec: int = 30,
    limit: int = 100,
) -> dict:
    """
    Execute a SQL query and return structured results.

    Returns:
        {
          "success": bool,
          "columns": list[str],
          "rows": list[tuple],
          "total_rows": int,
          "has_more": bool,
          "row_count_displayed": int,
        }
        On error, returns {"success": False, "error": str}
    """
    try:
        cur = conn.cursor()
        cur.execute(f"SET statement_timeout = '{timeout_sec}s'")
        cur.execute(sql)
        rows = cur.fetchall()
        cols = [desc[0] for desc in cur.description] if cur.description else []
        total = len(rows)

        cur.close()
        return {
            "success": True,
            "columns": cols,
            "rows": rows[:limit],
            "total_rows": total,
            "has_more": total > limit,
            "row_count_displayed": min(total, limit),
        }
    except psycopg2.errors.lookup('57000'):  # StatementTimeout / QueryCanceled
        return {"success": False, "error": "Query timeout"}
    except psycopg2.errors.SyntaxError as e:
        return {"success": False, "error": f"Syntax error: {e}"}
    except psycopg2.Error as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        return {"success": False, "error": f"Error: {e}"}


# ── Schema introspection ──────────────────────────────────────────────────────

def load_schema_data(
    host: str,
    port: int,
    dbname: str,
    user: str,
    password: str,
) -> SchemaData:
    """
    Load the full PostgreSQL schema: tables, columns, types, PK/FK, row estimates.
    Returns a SchemaData dataclass.
    """
    try:
        conn = get_connection(host, port, dbname, user, password)
        conn.autocommit = True
        cur = conn.cursor()
        result = SchemaData(db_name=dbname, connected=True)

        # Get tables
        cur.execute("""
            SELECT table_name, table_schema
            FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_type = 'BASE TABLE'
            ORDER BY table_name;
        """)
        table_rows = cur.fetchall()

        # Get row estimates
        cur.execute("""
            SELECT c.relname AS table_name, c.reltuples::bigint AS est_rows
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = 'public'
              AND c.relkind = 'r';
        """)
        row_estimates = {r[0]: r[1] for r in cur.fetchall()}

        # Get columns with types and constraints
        cur.execute("""
            SELECT
                c.table_name, c.column_name, c.data_type,
                c.is_nullable, c.column_default,
                CASE WHEN pk.column_name IS NOT NULL THEN TRUE ELSE FALSE END AS is_pk,
                COALESCE(fk.fk_table, '') AS fk_table,
                COALESCE(fk.fk_column, '') AS fk_column
            FROM information_schema.columns c
            LEFT JOIN (
                SELECT kcu.column_name, kcu.table_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                    ON tc.constraint_name = kcu.constraint_name
                WHERE tc.table_schema = 'public'
                  AND tc.constraint_type = 'PRIMARY KEY'
            ) pk ON pk.column_name = c.column_name AND pk.table_name = c.table_name
            LEFT JOIN (
                SELECT
                    kcu.column_name, kcu.table_name,
                    ccu.table_name AS fk_table,
                    ccu.column_name AS fk_column
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                    ON tc.constraint_name = kcu.constraint_name
                JOIN information_schema.constraint_column_usage ccu
                    ON tc.constraint_name = ccu.constraint_name
                WHERE tc.table_schema = 'public'
                  AND tc.constraint_type = 'FOREIGN KEY'
            ) fk ON fk.column_name = c.column_name AND fk.table_name = c.table_name
            WHERE c.table_schema = 'public'
            ORDER BY c.table_name, c.ordinal_position;
        """)
        col_rows = cur.fetchall()

        # Group columns by table
        cols_by_table: dict[str, list[ColumnInfo]] = {}
        for row in col_rows:
            tbl, col, dtype, nullable, default, is_pk, fk_tbl, fk_col = row
            if tbl not in cols_by_table:
                cols_by_table[tbl] = []
            cols_by_table[tbl].append(ColumnInfo(
                name=col,
                data_type=dtype,
                nullable=(nullable == "YES"),
                is_pk=bool(is_pk),
                is_fk=bool(fk_tbl),
                fk_ref=f"{fk_tbl}.{fk_col}" if fk_tbl else "",
            ))

        for tbl_name, tbl_schema in table_rows:
            est_rows = row_estimates.get(tbl_name, 0)
            cols = cols_by_table.get(tbl_name, [])
            result.tables.append(TableInfo(
                name=tbl_name,
                rows=int(est_rows),
                columns=cols,
            ))

        cur.close()
        conn.close()
        return result

    except psycopg2.Error as e:
        return SchemaData(db_name=dbname, connected=False, error=str(e))
    except Exception as e:
        return SchemaData(db_name=dbname, connected=False, error=str(e))
