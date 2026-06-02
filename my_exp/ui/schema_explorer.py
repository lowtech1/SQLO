"""
my_exp.ui.schema_explorer
=======================
Schema Explorer component — connects to PostgreSQL and renders
a visual schema tree in Streamlit.

Features:
- Connect to PostgreSQL via environment variables or manual input
- Load schema: tables, columns, types, PK/FK, row counts
- Render as expandable tree
- Click-to-insert: click table → insert SELECT, click column → insert name
- Search/filter tables and columns
"""

import streamlit as st
import psycopg2
import os
from typing import Optional
from dataclasses import dataclass, field


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
    columns: list = field(default_factory=list)


@dataclass
class SchemaData:
    db_name: str
    tables: list = field(default_factory=list)
    connected: bool = False
    error: str = ""


@st.cache_data(ttl=300)
def load_schema_data(
    host: str, port: int, dbname: str,
    user: str, password: str
) -> SchemaData:
    """Load full database schema from PostgreSQL (cached)."""
    try:
        conn = psycopg2.connect(
            host=host, port=port, dbname=dbname,
            user=user, password=password,
            connect_timeout=10,
        )
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
        cols_by_table = {}
        for row in col_rows:
            tbl, col, dtype, nullable, default, is_pk, fk_tbl, fk_col = row
            if tbl not in cols_by_table:
                cols_by_table[tbl] = []
            nullable_str = (nullable == 'YES')
            is_pk_bool = bool(is_pk)
            is_fk_bool = bool(fk_tbl)
            fk_ref = f"{fk_tbl}.{fk_col}" if fk_tbl else ""
            cols_by_table[tbl].append(ColumnInfo(
                name=col, data_type=dtype,
                nullable=nullable_str, is_pk=is_pk_bool,
                is_fk=is_fk_bool, fk_ref=fk_ref,
            ))

        for tbl_name, tbl_schema in table_rows:
            est_rows = row_estimates.get(tbl_name, 0)
            cols = cols_by_table.get(tbl_name, [])
            result.tables.append(TableInfo(
                name=tbl_name, rows=int(est_rows), columns=cols,
            ))

        cur.close()
        conn.close()
        return result

    except psycopg2.Error as e:
        return SchemaData(db_name=dbname, connected=False, error=str(e))
    except Exception as e:
        return SchemaData(db_name=dbname, connected=False, error=str(e))


def render_schema_panel(schema: SchemaData, key_prefix: str = "schema"):
    """Render the full schema explorer panel."""

    if not schema.connected:
        st.error(f"Loi ket noi: {schema.error}")
        return

    # Header
    st.markdown(f"**Database:** `{schema.db_name}`")
    st.markdown(f"**Tables:** {len(schema.tables)}")

    # Search
    search = st.text_input(
        "Tim kiem table/column:",
        placeholder="VD: customer, cust...",
        key=f"{key_prefix}_search",
    ).strip().lower()

    # Filter tables
    if search:
        filtered_tables = [
            t for t in schema.tables
            if search in t.name.lower()
            or any(search in c.name.lower() for c in t.columns)
        ]
    else:
        filtered_tables = schema.tables

    st.caption(f"Hien thi {len(filtered_tables)}/{len(schema.tables)} tables")

    # Render tree
    for table in filtered_tables:
        render_table_row(table, search, key_prefix)


def render_table_row(table: TableInfo, search: str = "", key_prefix: str = ""):
    """Render a single table as an expandable row."""

    cols = table.columns
    pk_cols = [c for c in cols if c.is_pk]
    fk_cols = [c for c in cols if c.is_fk]

    header = f"**{table.name}**"
    if table.rows > 0:
        header += f" `({table.rows:,} rows)`"
    if pk_cols:
        pk_names = ", ".join([c.name for c in pk_cols])
        header += f" 🔑[{pk_names}]"
    if fk_cols:
        header += " 🔗"

    with st.expander(header, expanded=(search != "")):
        # Click actions
        c1, c2 = st.columns(2)
        with c1:
            if st.button(f"SELECT *", key=f"{key_prefix}_sel_{table.name}", use_container_width=True):
                sql = f"SELECT * FROM {table.name} LIMIT 100;"
                st.session_state[f"{key_prefix}_inserted_sql"] = sql
                st.rerun()
        with c2:
            if st.button(f"COUNT(*)", key=f"{key_prefix}_cnt_{table.name}", use_container_width=True):
                sql = f"SELECT COUNT(*) AS cnt FROM {table.name};"
                st.session_state[f"{key_prefix}_inserted_sql"] = sql
                st.rerun()

        st.markdown("**Columns:**")

        # Filtered columns
        if search:
            filtered_cols = [c for c in cols if search in c.name.lower()]
        else:
            filtered_cols = cols

        for col in filtered_cols:
            type_badge = f"`{col.data_type}`"
            badges = []
            if col.is_pk:
                badges.append(":blue[PK]")
            if col.is_fk:
                badges.append(":orange[FK]")
            if not col.nullable:
                badges.append(":red[NOT NULL]")
            badge_str = " ".join(badges)

            col_c1, col_c2 = st.columns([3, 1])
            with col_c1:
                st.markdown(f"  - {col.name} {type_badge} {badge_str}")
            with col_c2:
                if st.button("Copy", key=f"{key_prefix}_cp_{table.name}_{col.name}", help="Copy column name"):
                    st.code(col.name)
                    st.toast(f"Copied: {col.name}")

        # FK references
        fk_cols = [c for c in cols if c.is_fk and c.fk_ref]
        if fk_cols:
            st.markdown("**References:**")
            for col in fk_cols:
                st.caption(f"  {col.name} → {col.fk_ref}")


def render_connection_form(defaults: dict = None) -> dict:
    """Render DB connection form. Returns connection params."""
    defaults = defaults or {}

    st.markdown("### Ket Noi PostgreSQL")
    host = st.text_input("Host", value=defaults.get("host", os.getenv("POSTGRES_HOST", "localhost")))
    port = st.number_input("Port", value=defaults.get("port", int(os.getenv("POSTGRES_PORT", "5432"))), min_value=1, max_value=65535)
    dbname = st.text_input("Database", value=defaults.get("dbname", os.getenv("POSTGRES_DB", "postgres")))
    user = st.text_input("User", value=defaults.get("user", os.getenv("POSTGRES_USER", "postgres")))
    password = st.text_input("Password", value=defaults.get("password", os.getenv("POSTGRES_PASSWORD", "")), type="password")

    return {
        "host": host, "port": port, "dbname": dbname,
        "user": user, "password": password,
    }


def get_connection(host: str, port: int, dbname: str, user: str, password: str):
    """Create a psycopg2 connection."""
    return psycopg2.connect(
        host=host, port=port, dbname=dbname,
        user=user, password=password,
        connect_timeout=10,
    )


def execute_query(conn, sql: str, timeout_sec: int = 30, limit: int = 100):
    """Execute a query and return results with metadata."""
    import psycopg2
    try:
        cur = conn.cursor()
        cur.execute(f"SET statement_timeout = '{timeout_sec}s'")
        cur.execute(sql)
        rows = cur.fetchall()
        cols = [desc[0] for desc in cur.description] if cur.description else []
        col_count = len(cols)

        # Limit for display
        display_rows = rows[:limit]
        has_more = len(rows) > limit

        cur.close()
        return {
            "success": True,
            "columns": cols,
            "rows": display_rows,
            "total_rows": len(rows),
            "has_more": has_more,
            "row_count_displayed": len(display_rows),
        }
    except psycopg2.errors.StatementTimeout:
        return {"success": False, "error": "Query timeout"}
    except psycopg2.errors.SyntaxError as e:
        return {"success": False, "error": f"Syntax error: {e}"}
    except psycopg2.Error as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        return {"success": False, "error": f"Error: {e}"}
