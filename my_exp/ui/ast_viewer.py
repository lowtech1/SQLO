"""
my_exp.ui.ast_viewer
=================
AST tree visualizer — renders sqlglot AST as an interactive,
color-coded tree in Streamlit.
"""

import streamlit as st
import sqlglot
from sqlglot import expressions as exp


# Color mapping for AST node types
NODE_COLORS = {
    "Select": "#1565c0",       # Blue
    "Subquery": "#6a1b9a",      # Purple
    "Join": "#e65100",          # Orange
    "Where": "#f9a825",         # Yellow
    "Group": "#2e7d32",        # Green
    "Having": "#388e3c",        # Light Green
    "Order": "#c62828",        # Red
    "Limit": "#ad1457",         # Pink
    "From": "#00695c",          # Teal
    "Table": "#37474f",         # Dark Gray
    "Column": "#0277bd",        # Light Blue
    "Alias": "#5d4037",         # Brown
    "AggFunc": "#d32f2f",       # Red
    "And": "#455a64",           # Blue Gray
    "Or": "#546e7a",           # Gray Blue
    "Binary": "#78909c",        # Gray
    "Paren": "#90a4ae",        # Light Gray
    "Order": "#6d4c41",        # Brown
    "Union": "#37474f",         # Dark
    "Cte": "#1b5e20",          # Dark Green
}

DEFAULT_COLOR = "#455a64"


def get_node_color(node_type: str) -> str:
    """Get color for a node type."""
    for key, color in NODE_COLORS.items():
        if key.lower() in node_type.lower():
            return color
    return DEFAULT_COLOR


def get_node_icon(node_type: str) -> str:
    """Get emoji icon for a node type."""
    icons = {
        "select": "🔵", "from": "🟢", "where": "🟡",
        "join": "🟠", "group": "🟣", "having": "🟣",
        "order": "🔴", "limit": "🔴", "table": "📋",
        "column": "📊", "alias": "📝", "subquery": "📦",
        "and": "⚫", "or": "⚫", "union": "🔗",
        "aggfunc": "🔢", "count": "🔢", "sum": "🔢",
    }
    node_lower = node_type.lower()
    for key, icon in icons.items():
        if key in node_lower:
            return icon
    return "▪"


def render_ast_node(node, depth=0, max_depth=6, key_prefix="ast"):
    """Render a single AST node recursively."""

    if depth > max_depth:
        return

    node_type = type(node).__name__
    color = get_node_color(node_type)
    icon = get_node_icon(node_type)

    # Get node display text
    try:
        display_text = str(node)[:80].replace("\n", " ").strip()
    except Exception:
        display_text = node_type

    indent_str = "&nbsp;&nbsp;&nbsp;&nbsp;" * depth

    # Render this node
    col_label, col_content = st.columns([1, 3])

    with col_label:
        st.markdown(
            f"<span style='background:{color};color:#fff;padding:3px 10px;"
            f"border-radius:4px;font-size:12px;display:inline-block'>"
            f"{indent_str}{icon} {node_type}</span>",
            unsafe_allow_html=True,
        )

    with col_content:
        # Show meaningful content
        if node_type == "Column":
            parts = []
            if hasattr(node, 'table') and node.table:
                parts.append(node.table)
            if hasattr(node, 'name'):
                parts.append(node.name)
            st.code(".".join(parts) if parts else display_text, language="sql")
        elif node_type in ("Table",):
            name = getattr(node, 'name', display_text)
            alias = getattr(node, 'alias', None)
            text = name + (f" AS {alias}" if alias else "")
            st.code(text, language="sql")
        elif node_type in ("AggFunc",):
            st.code(display_text, language="sql")
        elif node_type in ("Select",):
            # Show SELECT expressions count
            if hasattr(node, 'expressions'):
                exprs = len(node.expressions)
                st.caption(f"{exprs} columns in SELECT")
        elif display_text and display_text != node_type:
            st.code(display_text, language="sql")
        else:
            st.caption(node_type)

    # Recurse into children
    if hasattr(node, 'args') and node.args:
        args = node.args
        for key, val in args.items():
            if val is None:
                continue

            # Render key label
            if depth < max_depth:
                key_col, val_col = st.columns([1, 3])
                with key_col:
                    st.caption(f"{'&nbsp;' * (depth+1)}**{key}:**")

                # Check if it's a list of nodes or a single node
                if isinstance(val, list):
                    if val:
                        with val_col:
                            for item in val[:3]:  # Limit children shown
                                if hasattr(item, 'args'):
                                    render_ast_node(item, depth=depth+1, max_depth=max_depth, key_prefix=key_prefix)
                            if len(val) > 3:
                                st.caption(f"  ... +{len(val)-3} more")
                elif hasattr(val, 'args'):
                    with val_col:
                        render_ast_node(val, depth=depth+1, max_depth=max_depth, key_prefix=key_prefix)


def render_ast_full(sql: str, max_depth: int = 5):
    """Render full AST tree for a SQL query."""

    try:
        ast = sqlglot.parse(sql)
        if not ast:
            st.error("Khong parse duoc SQL")
            return
        ast = ast[0]
    except Exception as e:
        st.error(f"Loi parse: {e}")
        return

    st.markdown(f"**Cay AST ({type(ast).__name__})**")

    with st.expander("Chi tiet cay AST", expanded=True):
        render_ast_node(ast, depth=0, max_depth=max_depth)


def render_ast_compact(sql: str):
    """Render a compact AST summary."""

    try:
        ast = sqlglot.parse(sql)
        if not ast:
            return
        ast = ast[0]
    except Exception:
        return

    # Count node types
    node_counts = {}
    for node in ast.walk():
        nt = type(node).__name__
        node_counts[nt] = node_counts.get(nt, 0) + 1

    # Sort by count
    sorted_nodes = sorted(node_counts.items(), key=lambda x: -x[1])[:8]

    cols = st.columns(min(len(sorted_nodes), 4))
    for i, (node_type, count) in enumerate(sorted_nodes):
        color = get_node_color(node_type)
        with cols[i % 4]:
            st.markdown(
                f"<span style='background:{color};color:#fff;"
                f"padding:4px 8px;border-radius:4px;font-size:12px'>"
                f"{get_node_icon(node_type)} {node_type}: {count}</span>",
                unsafe_allow_html=True,
            )


def render_ast_with_parse(sql: str, features: dict):
    """Render AST with parsed features summary."""

    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.markdown("### Cay AST")
        ast = sqlglot.parse(sql)
        if ast:
            render_ast_full(sql, max_depth=4)

    with col_right:
        st.markdown("### Cau truc")
        # Show key structural info
        info = [
            ("Table count", features.get("table_count", 0)),
            ("Join count", features.get("join_count", 0)),
            ("Subquery count", features.get("subquery_count", 0)),
            ("Has aggregation", "Co" if features.get("has_aggregation") else "Khong"),
            ("Has GROUP BY", "Co" if features.get("has_group_by") else "Khong"),
            ("Has ORDER BY", "Co" if features.get("has_order_by") else "Khong"),
            ("Has LIMIT", "Co" if features.get("has_limit") else "Khong"),
        ]
        for label, value in info:
            st.markdown(f"- **{label}:** {value}")

        complexity = features.get("complexity", {})
        st.markdown(f"- **Do phuc tap:** {complexity.get('level', '?')} (score={complexity.get('score', 0)})")
        if complexity.get("factors"):
            st.markdown("**Yeu to:**")
            for f in complexity["factors"]:
                st.markdown(f"  - {f}")
