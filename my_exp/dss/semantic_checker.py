"""
my_exp.dss.semantic_checker
==========================
Semantic equivalence verification for SQL rewrites.
Verifies that rewritten SQL produces the same results as the original.
"""

import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Optional, Tuple

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from dotenv import load_dotenv
_root_env = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../.env'))
load_dotenv(_root_env)


def get_db_connection(dbname: str = None, host: str = None, port: int = None,
                       user: str = None, password: str = None):
    """Create PostgreSQL connection with env var fallbacks."""
    import psycopg2

    dbname = dbname or os.getenv("POSTGRES_DB", "postgres")
    host = host or os.getenv("POSTGRES_HOST", "localhost")
    port = port or int(os.getenv("POSTGRES_PORT", "5432"))
    user = user or os.getenv("POSTGRES_USER", "postgres")
    password = password or os.getenv("POSTGRES_PASSWORD", "")

    return psycopg2.connect(
        host=host, port=port, dbname=dbname, user=user, password=password
    )


def execute_query(conn, sql: str, timeout_sec: int = 30) -> Tuple[Optional[list], Optional[str]]:
    """
    Execute a SQL query and return results.

    Returns:
        (rows, error_message)
    """
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(f"SET statement_timeout = '{timeout_sec}s'")
        cur.execute(sql)
        rows = cur.fetchall()
        # Convert to list of dicts
        result = [dict(row) for row in rows]
        cur.close()
        return result, None
    except psycopg2.errors.lookup('57000'):  # StatementTimeout / QueryCanceled
        return None, "Query timeout"
    except psycopg2.errors.CardinalityViolation:
        return None, "Cardinality violation"
    except psycopg2.errors.UndefinedTable:
        return None, "Table does not exist"
    except psycopg2.errors.SyntaxError:
        return None, "SQL syntax error"
    except psycopg2.Error as e:
        return None, str(e)
    except Exception as e:
        return None, f"Error: {str(e)}"


def check_equivalence(
    original_sql: str,
    rewritten_sql: str,
    dbname: str = None,
    sample_limit: int = 1000,
    timeout_sec: int = 30,
) -> dict:
    """
    Check if rewritten SQL is semantically equivalent to original SQL.

    Strategy:
    1. Run both queries on sample data
    2. Compare row counts
    3. Compare result sets (row-by-row if small)
    4. Check for errors

    Returns:
        dict with keys: equivalent, confidence, row_count_original, row_count_rewritten,
                       errors, comparison_method
    """
    try:
        conn = get_db_connection(dbname=dbname)
    except psycopg2.Error as e:
        return {
            "equivalent": None,
            "confidence": 0.0,
            "error": f"Cannot connect to database: {e}",
            "row_count_original": None,
            "row_count_rewritten": None,
        }

    try:
        # Execute original
        orig_rows, orig_err = execute_query(conn, original_sql, timeout_sec)
        if orig_err:
            return {
                "equivalent": False,
                "confidence": 0.0,
                "error": f"Original query error: {orig_err}",
                "row_count_original": None,
                "row_count_rewritten": None,
            }

        # Execute rewritten
        rew_rows, rew_err = execute_query(conn, rewritten_sql, timeout_sec)
        if rew_err:
            return {
                "equivalent": False,
                "confidence": 0.0,
                "error": f"Rewritten query error: {rew_err}",
                "row_count_original": len(orig_rows),
                "row_count_rewritten": None,
            }

        n_orig = len(orig_rows)
        n_rew = len(rew_rows)

        if n_orig != n_rew:
            return {
                "equivalent": False,
                "confidence": 0.95,
                "error": f"Row count mismatch: {n_orig} vs {n_rew}",
                "row_count_original": n_orig,
                "row_count_rewritten": n_rew,
                "comparison_method": "row_count",
            }

        # Both empty — equivalent
        if n_orig == 0:
            return {
                "equivalent": True,
                "confidence": 1.0,
                "row_count_original": 0,
                "row_count_rewritten": 0,
                "comparison_method": "empty_result",
            }

        # Compare results
        # Sort both for order-independent comparison
        orig_sorted = sorted(orig_rows, key=lambda r: tuple(sorted(str(v) for v in r.values())))
        rew_sorted = sorted(rew_rows, key=lambda r: tuple(sorted(str(v) for v in r.values())))

        if orig_sorted == rew_sorted:
            confidence = 1.0
            return {
                "equivalent": True,
                "confidence": confidence,
                "row_count_original": n_orig,
                "row_count_rewritten": n_rew,
                "comparison_method": "row_by_row",
            }
        else:
            return {
                "equivalent": False,
                "confidence": 0.98,
                "error": "Result sets differ",
                "row_count_original": n_orig,
                "row_count_rewritten": n_rew,
                "comparison_method": "row_by_row",
            }

    finally:
        conn.close()


class SemanticChecker:
    """
    High-level semantic equivalence checker.
    """

    def __init__(self, dbname: str = None):
        self.dbname = dbname

    def check(self, original_sql: str, rewritten_sql: str, timeout_sec: int = 30) -> dict:
        """Check semantic equivalence of two SQL queries."""
        return check_equivalence(original_sql, rewritten_sql, self.dbname, timeout_sec=timeout_sec)

    def check_candidates(self, original_sql: str, candidates: list) -> list:
        """
        Check semantic equivalence for all candidates.

        Args:
            original_sql: The original SQL query
            candidates: List of candidate dicts (with 'sql' key)

        Returns:
            List of candidates with semantic_check field added
        """
        results = []
        for c in candidates:
            result = self.check(original_sql, c["sql"])
            c["semantic_check"] = result
            results.append(c)
        return results
