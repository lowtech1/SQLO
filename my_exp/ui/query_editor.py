"""
my_exp.ui.query_editor
==================
Interactive SQL Query Editor component with:
- SQL text input with syntax-aware display
- Execute button (runs against live PostgreSQL)
- Sample data preview
- Query execution metrics
- History dropdown
"""

import streamlit as st
import pandas as pd
import time
from typing import Optional


def render_query_editor(
    key: str = "editor",
    default_sql: str = "",
    schema: Optional[dict] = None,
    on_execute_callback=None,
    on_optimize_callback=None,
) -> str:
    """
    Render the query editor component.

    Returns the current SQL text.
    """

    # Toolbar
    col_run, col_opt, col_clear, col_exp, col_hist = st.columns([1, 1, 1, 1, 1])

    sql = st.text_area(
        "SQL Query:",
        value=default_sql,
        height=200,
        placeholder="SELECT * FROM orders WHERE o_totalprice > 100000",
        key=f"{key}_textarea",
    )

    with col_run:
        run = st.button("▶ Run", type="primary", use_container_width=True)
    with col_opt:
        optimize = st.button("💡 Optimize", use_container_width=True)
    with col_clear:
        clear = st.button("🗑 Clear", use_container_width=True)
    with col_exp:
        st.download_button(
            "⬇ Export",
            data=sql,
            file_name="query.sql",
            mime="text/sql",
            use_container_width=True,
        )
    with col_hist:
        history = st.selectbox(
            "Lich su",
            ["(Hien tai)"] + st.session_state.get(f"{key}_history", []),
            key=f"{key}_hist",
        )

    # Handle history selection
    if history != "(Hien tai)" and history:
        st.session_state[f"{key}_textarea"] = history
        st.rerun()

    # Handle clear
    if clear:
        st.session_state[f"{key}_textarea"] = ""
        st.rerun()

    # Add to history
    if sql and sql not in st.session_state.get(f"{key}_history", []):
        history_list = st.session_state.get(f"{key}_history", [])
        history_list.insert(0, sql)
        st.session_state[f"{key}_history"] = history_list[:20]

    return sql


def render_results_table(result: dict, max_display: int = 100):
    """Render query results as a scrollable table."""

    if not result.get("success"):
        st.error(f"Loi: {result.get('error', 'Unknown error')}")
        return

    cols = result.get("columns", [])
    rows = result.get("rows", [])

    if not cols:
        st.info("Query chay thanh cong nhung khong co ket qua tra ve")
        return

    # Stats bar
    m1, m2, m3 = st.columns(3)
    with m1:
        st.metric("Cot", len(cols))
    with m2:
        st.metric("Dong (total)", f"{result.get('total_rows', 0):,}")
    with m3:
        rd = result.get("row_count_displayed", 0)
        if result.get("has_more"):
            st.metric("Hien thi", f"{rd:,} (tren {result.get('total_rows', 0):,})")
        else:
            st.metric("Hien thi", f"{rd:,}")

    # Data table
    df = pd.DataFrame(rows, columns=cols)
    st.dataframe(
        df.head(max_display),
        use_container_width=True,
        hide_index=True,
        height=400,
    )

    # Export
    csv = df.to_csv(index=False)
    st.download_button(
        f"⬇ Tai CSV ({len(df)} dong)",
        data=csv,
        file_name="query_results.csv",
        mime="text/csv",
        use_container_width=True,
    )


def render_execute_button(sql: str, conn, key: str = "exec") -> dict:
    """Render execute button and return execution result."""

    col_run, col_time = st.columns([1, 1])

    with col_run:
        run = st.button("▶ Run Query", type="primary", use_container_width=True)

    if run and sql.strip():
        with st.spinner("Dang thuc thi..."):
            start = time.time()
            result = _execute_query(conn, sql)
            elapsed = time.time() - start
            result["elapsed_sec"] = round(elapsed, 3)
            return result

    return {}


def _execute_query(conn, sql: str, timeout_sec: int = 30, limit: int = 100) -> dict:
    """Execute SQL and return structured results."""
    import psycopg2

    try:
        cur = conn.cursor()
        cur.execute(f"SET statement_timeout = '{timeout_sec}s'")
        cur.execute(sql)
        rows = cur.fetchall()
        cols = [desc[0] for desc in cur.description] if cur.description else []
        total = len(rows)
        display_rows = rows[:limit]

        cur.close()
        return {
            "success": True,
            "columns": cols,
            "rows": display_rows,
            "total_rows": total,
            "has_more": total > limit,
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


def get_schema_autocomplete(schema_data) -> dict:
    """Build autocomplete data from schema for the editor."""

    if not schema_data:
        return {}

    tables = {}
    all_columns = []

    for table in schema_data.get("tables", []):
        table_name = table.get("name", "")
        cols = []
        for col in table.get("columns", []):
            col_name = col.get("name", "")
            cols.append(col_name)
            all_columns.append(f"{table_name}.{col_name}")
        tables[table_name] = cols

    return {
        "tables": tables,
        "all_columns": all_columns,
    }


def render_sql_with_highlighting(sql: str) -> str:
    """Return SQL with basic HTML highlighting."""
    import re

    keywords = [
        "SELECT", "FROM", "WHERE", "JOIN", "LEFT", "RIGHT", "INNER", "OUTER",
        "ON", "AND", "OR", "NOT", "IN", "EXISTS", "GROUP", "BY", "HAVING",
        "ORDER", "LIMIT", "OFFSET", "AS", "DISTINCT", "UNION", "INTERSECT",
        "EXCEPT", "WITH", "INSERT", "UPDATE", "DELETE", "CREATE", "DROP",
        "ALTER", "SET", "VALUES", "NULL", "TRUE", "FALSE", "LIKE", "BETWEEN",
        "CASE", "WHEN", "THEN", "ELSE", "END", "IS", "ASC", "DESC",
        "COUNT", "SUM", "AVG", "MIN", "MAX", "COALESCE", "CAST",
    ]

    # Simple highlighting: wrap keywords in bold
    for kw in keywords:
        pattern = re.compile(rf'\b{kw}\b', re.IGNORECASE)
        sql = pattern.sub(f'**{kw.upper()}**', sql)

    return sql
