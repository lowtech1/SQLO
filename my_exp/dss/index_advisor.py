"""
my_exp/dss/index_advisor.py
============================
Analyzes EXPLAIN ANALYZE plans to detect sequential scans on large tables
and recommends appropriate indexes.

Key insight: Even if we cannot automatically create indexes (requires DDL),
we can analyze the plan and provide actionable index recommendations
with rationale from the actual execution statistics.
"""

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class IndexRecommendation:
    """A single index recommendation."""
    table_name: str
    column_name: str
    index_type: str  # "btree" (default), "hash", "gist", etc.
    estimated_size: int  # approximate rows in table
    seq_scan_rows: int  # rows scanned in the seq scan
    cost_before: float  # cost of the seq scan
    cost_estimate_after: float  # estimated cost after index
    improvement_pct: float
    rationale: str  # Why this index helps
    sql: str  # Full CREATE INDEX statement


class IndexAdvisor:
    """
    Analyzes PostgreSQL EXPLAIN plans to recommend indexes.

    Detects:
    - Sequential scans on large tables
    - Filter conditions that could use indexes
    - Join columns that lack indexes

    Limitations:
    - Cannot auto-create indexes (requires DDL)
    - Recommendations are suggestions, not guarantees
    - User must verify and create indexes manually
    """

    def __init__(self):
        # Known large TPC-H table thresholds
        self.table_row_counts = {
            "lineitem": 6_000_000,
            "orders": 1_500_000,
            "customer": 150_000,
            "partsupp": 800_000,
            "part": 200_000,
            "supplier": 10_000,
            "nation": 25,
            "region": 5,
        }

    def analyze_plan(self, plan_data: dict) -> list[IndexRecommendation]:
        """
        Analyze an EXPLAIN JSON plan and return index recommendations.

        Args:
            plan_data: Parsed EXPLAIN (ANALYZE, FORMAT JSON) output

        Returns:
            List of IndexRecommendation objects
        """
        if not plan_data:
            return []

        plan = plan_data.get("Plan", {})
        recommendations = []

        # Scan for Seq Scan nodes
        for node in self._flatten_plan(plan):
            node_type = node.get("Node Type", "")
            rel_name = node.get("Relation Name", "")

            if node_type in ("Seq Scan", "Parallel Seq Scan") and rel_name:
                rec = self._analyze_seq_scan(node, rel_name)
                if rec:
                    recommendations.append(rec)

        # Scan for indexable join columns
        for node in self._flatten_plan(plan):
            self._analyze_join_for_index(node, recommendations)

        # Deduplicate by (table, column)
        seen = {}
        for rec in recommendations:
            key = (rec.table_name, rec.column_name)
            if key not in seen or rec.cost_before > seen[key].cost_before:
                seen[key] = rec

        return sorted(seen.values(), key=lambda x: x.cost_before, reverse=True)

    def _flatten_plan(self, node: dict):
        """Recursively yield all nodes in a plan tree."""
        yield node
        for key in ("Plans", "Outer", "Inner", "Child", "Parent Relationship"):
            child = node.get(key)
            if isinstance(child, dict):
                yield from self._flatten_plan(child)
            elif isinstance(child, list):
                for c in child:
                    if isinstance(c, dict):
                        yield from self._flatten_plan(c)

    def _analyze_seq_scan(self, node: dict, table_name: str) -> Optional[IndexRecommendation]:
        """
        Analyze a Seq Scan node and determine if an index would help.
        """
        rows = node.get("Plan Rows", 0)
        cost = node.get("Total Cost", 0)
        filter_cond = node.get("Filter", "")
        actual_time = node.get("Actual Total Time", 0)

        if not filter_cond and rows < 1000:
            return None  # Small table scan without filter — index won't help

        # Determine the column(s) used in the filter
        columns = self._extract_filter_columns(filter_cond)

        if not columns:
            # Seq scan without filter on large table
            est_count = self.table_row_counts.get(table_name.lower(), rows)
            if est_count > 10_000 and not filter_cond:
                return IndexRecommendation(
                    table_name=table_name,
                    column_name="(primary key)",
                    index_type="btree",
                    estimated_size=est_count,
                    seq_scan_rows=rows,
                    cost_before=cost,
                    cost_estimate_after=cost * 0.1,
                    improvement_pct=90.0,
                    rationale=f"Sequential scan on large table ({est_count:,} rows) without filter. "
                              f"Primary key lookup would be faster.",
                    sql=f"-- Consider partitioning or caching for {table_name}\n"
                        f"-- No obvious single-column index for unfiltered scan",
                )
            return None

        # Create index recommendation for filter columns
        col = columns[0]
        est_count = self.table_row_counts.get(table_name.lower(), rows)
        selectivity = self._estimate_selectivity(filter_cond)

        # Estimate cost after index: random I/O instead of sequential
        # B-tree index on selective column: ~5-10% of seq scan cost
        if selectivity < 0.1:  # selective filter (<10% rows)
            cost_after = cost * 0.05
            improvement = 95.0
            rationale = (
                f"Highly selective filter ({selectivity*100:.1f}% selectivity). "
                f"Index scan would reduce rows from {rows:,} to ~{int(rows * selectivity):,} "
                f"before applying remaining filters."
            )
        elif selectivity < 0.5:  # moderately selective
            cost_after = cost * 0.3
            improvement = 70.0
            rationale = (
                f"Moderately selective filter ({selectivity*100:.1f}% selectivity). "
                f"Index scan would reduce I/O by scanning only matching pages."
            )
        else:  # non-selective
            cost_after = cost * 0.8
            improvement = 20.0
            rationale = (
                f"Low selectivity filter ({selectivity*100:.1f}% — most rows pass). "
                f"Index may not help much. Consider composite index with other filter columns."
            )

        return IndexRecommendation(
            table_name=table_name,
            column_name=col,
            index_type="btree",
            estimated_size=est_count,
            seq_scan_rows=rows,
            cost_before=cost,
            cost_estimate_after=cost_after,
            improvement_pct=improvement,
            rationale=rationale,
            sql=f"CREATE INDEX idx_{table_name}_{col} ON {table_name}({col});",
        )

    def _analyze_join_for_index(self, node: dict, recommendations: list):
        """Detect join columns that could benefit from indexes."""
        node_type = node.get("Node Type", "")

        if node_type in ("Hash Join", "Merge Join", "Nested Loop"):
            rel_name = node.get("Relation Name", "")
            if not rel_name:
                return

            # Look for join conditions
            join_filter = node.get("Join Filter", "") or node.get("Hash Cond", "") or node.get("Merge Cond", "")

            if join_filter:
                cols = self._extract_filter_columns(join_filter)
                for col in cols:
                    # Skip if already recommended
                    if any(r.table_name == rel_name and r.column_name == col for r in recommendations):
                        continue

                    cost = node.get("Total Cost", 0)
                    rows = node.get("Plan Rows", 0)
                    est_count = self.table_row_counts.get(rel_name.lower(), rows)

                    recommendations.append(IndexRecommendation(
                        table_name=rel_name,
                        column_name=col,
                        index_type="btree",
                        estimated_size=est_count,
                        seq_scan_rows=rows,
                        cost_before=cost,
                        cost_estimate_after=cost * 0.4,
                        improvement_pct=60.0,
                        rationale=(
                            f"Join on {rel_name}.{col} used in {node_type}. "
                            f"Index would speed up hash/build phase of the join."
                        ),
                        sql=f"CREATE INDEX idx_{rel_name}_{col} ON {rel_name}({col});",
                    ))

    def _extract_filter_columns(self, filter_cond: str) -> list:
        """Extract column names from a filter condition."""
        if not filter_cond:
            return []

        columns = []

        # Match patterns like: column_name = value, column_name > value, etc.
        # Also handle function calls like date_trunc, etc.
        patterns = [
            r'([a-zA-Z_][a-zA-Z0-9_]*)\s*[=<>!]+\s*',  # column OP value
            r'[a-zA-Z_][a-zA-Z0-9_]*\s*BETWEEN\s+',     # column BETWEEN
            r'[a-zA-Z_][a-zA-Z0-9_]*\s+LIKE\s+',       # column LIKE
            r'[a-zA-Z_][a-zA-Z0-9_]*\s+IN\s*\(',       # column IN
            r'[a-zA-Z_][a-zA-Z0-9_]*\s+IS\s+',         # column IS
        ]

        for pattern in patterns:
            for match in re.finditer(pattern, filter_cond):
                col = match.group(1)
                # Filter out SQL keywords and functions
                if col.upper() not in ("AND", "OR", "NOT", "DATE", "EXTRACT", "SUBSTRING",
                                       "LOWER", "UPPER", "TRIM", "COALESCE", "NULL",
                                       "TRUE", "FALSE", "CURRENT_DATE", "COUNT", "SUM",
                                       "AVG", "MIN", "MAX", "CASE", "WHEN", "THEN", "ELSE",
                                       "BETWEEN", "LIKE", "IN", "IS", "AND", "OR", "NOT"):
                    if col not in columns:
                        columns.append(col)

        return columns

    def _estimate_selectivity(self, filter_cond: str) -> float:
        """
        Heuristic selectivity estimation from filter condition.
        Returns float between 0 and 1 (fraction of rows returned).
        """
        if not filter_cond:
            return 1.0

        # Very selective patterns
        if ">=" in filter_cond and "<=" in filter_cond:
            return 0.2  # Range scan — moderate selectivity
        if ">=" in filter_cond or "<=" in filter_cond or ">" in filter_cond or "<" in filter_cond:
            return 0.15  # Comparison — selective
        if "=" in filter_cond:
            return 0.05  # Equality — highly selective
        if "IN" in filter_cond.upper():
            return 0.1  # IN list — selective
        if "LIKE" in filter_cond.upper():
            return 0.3  # LIKE — varies
        if "BETWEEN" in filter_cond.upper():
            return 0.2  # BETWEEN — range

        return 0.5  # Default
