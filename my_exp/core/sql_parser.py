"""
my_exp.core.sql_parser
=====================
SQL parsing utilities using sqlglot.
Provides a stable, dialect-agnostic interface for SQL analysis and rewriting.
"""

import sqlglot
from sqlglot import expressions as exp, parse, transpile, exp
from typing import Optional
import copy


def parse_sql(sql: str, dialect: str = "postgres") -> Optional[exp.Expression]:
    """
    Parse SQL string into sqlglot AST.

    Args:
        sql: SQL query string
        dialect: SQL dialect (postgres, mysql, sqlite, etc.)

    Returns:
        sqlglot Expression AST, or None if parsing fails
    """
    try:
        result = parse(sql, read=dialect)
        if result and len(result) > 0:
            return result[0]
        return None
    except Exception:
        return None


def ast_to_sql(ast: exp.Expression, dialect: str = "postgres") -> str:
    """
    Convert sqlglot AST back to SQL string.

    Args:
        ast: sqlglot Expression AST
        dialect: Target SQL dialect

    Returns:
        SQL string representation
    """
    try:
        return ast.sql(dialect=dialect)
    except Exception:
        return str(ast)


def clone_ast(ast: exp.Expression) -> exp.Expression:
    """
    Deep-clone a sqlglot AST.

    Args:
        ast: sqlglot Expression to clone

    Returns:
        Cloned expression tree
    """
    return copy.deepcopy(ast)


def extract_tables(ast: exp.Expression) -> list:
    """
    Extract all table references from AST.

    Returns:
        List of (table_name, alias_or_none) tuples
    """
    tables = []
    for table in ast.find_all(exp.Table):
        tables.append((table.name, table.alias))
    return tables


def extract_columns(ast: exp.Expression) -> list:
    """
    Extract all column references from AST.

    Returns:
        List of column names
    """
    return [col.name for col in ast.find_all(exp.Column)]


def extract_subqueries(ast: exp.Expression) -> list:
    """
    Extract all subqueries from AST.

    Returns:
        List of subquery expressions
    """
    return list(ast.find_all(exp.Subquery))


def extract_joins(ast: exp.Expression) -> list:
    """
    Extract all JOIN nodes from AST.

    Returns:
        List of Join expressions
    """
    return list(ast.find_all(exp.Join))


def extract_where(ast: exp.Expression) -> Optional[exp.Expression]:
    """
    Extract WHERE clause from AST.

    Returns:
        WHERE expression or None
    """
    for node in ast.walk():
        if isinstance(node, exp.Select):
            return node.args.get("where")
    return None


def extract_group_by(ast: exp.Expression) -> Optional[exp.Expression]:
    """Extract GROUP BY clause."""
    for node in ast.walk():
        if isinstance(node, exp.Select):
            return node.args.get("group")
    return None


def extract_having(ast: exp.Expression) -> Optional[exp.Expression]:
    """Extract HAVING clause."""
    for node in ast.walk():
        if isinstance(node, exp.Select):
            return node.args.get("having")
    return None


def extract_order_by(ast: exp.Expression) -> Optional[exp.Expression]:
    """Extract ORDER BY clause."""
    for node in ast.walk():
        if isinstance(node, exp.Select):
            return node.args.get("order")
    return None


def extract_limit(ast: exp.Expression) -> Optional[exp.Expression]:
    """Extract LIMIT clause."""
    for node in ast.walk():
        if isinstance(node, exp.Select):
            return node.args.get("limit")
    return None


def has_aggregate_functions(ast: exp.Expression) -> bool:
    """Check if query contains aggregate functions."""
    return any(isinstance(node, exp.AggFunc) for node in ast.walk())


def has_distinct(ast: exp.Expression) -> bool:
    """Check if query has DISTINCT keyword."""
    for node in ast.walk():
        if isinstance(node, exp.Select):
            if node.args.get("distinct"):
                return True
    return False


def count_join_operators(ast: exp.Expression) -> int:
    """Count number of JOIN operators in the query."""
    return len(list(ast.find_all(exp.Join)))


def count_tables_in_from(ast: exp.Expression) -> int:
    """Count number of tables referenced in FROM clause."""
    count = 0
    for node in ast.walk():
        if isinstance(node, exp.Table):
            count += 1
    return count


def get_select_columns(ast: exp.Expression) -> list:
    """
    Get list of selected column names (top-level SELECT only).
    """
    for node in ast.walk():
        if isinstance(node, exp.Select):
            return [col.get_name() if hasattr(col, 'get_name') else str(col)
                    for col in node.expressions]
    return []


def is_correlated_subquery(ast: exp.Expression) -> bool:
    """
    Check if a subquery references columns from the outer query.
    """
    outer_cols = set()
    for node in ast.walk():
        if isinstance(node, exp.Column):
            outer_cols.add(node.table)
    for sub in ast.find_all(exp.Subquery):
        for col in sub.find_all(exp.Column):
            if col.table in outer_cols:
                return True
    return False
