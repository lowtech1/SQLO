"""
my_exp/core/query_complexity.py
=============================
Classifies SQL queries by algorithmic complexity (O(n), O(n log n), O(n^2), etc.)
based on structural analysis of the query plan and SQL features.
"""

import re
from dataclasses import dataclass
from enum import Enum


class ComplexityLevel(Enum):
    O_N = "O(n)"
    O_N_LOG_N = "O(n log n)"
    O_N_SQUARED = "O(n^2)"
    O_N_CUBED = "O(n^3)"
    UNKNOWN = "Unknown"


@dataclass
class ComplexityScore:
    level: ComplexityLevel
    score: float
    label: str
    factors: list
    recommended_rules: list
    bottleneck_description: str
    complexity_explanation: str


class QueryComplexityClassifier:
    RULE_RECOMMENDATIONS = {
        ComplexityLevel.O_N: ["predicate_pushdown"],
        ComplexityLevel.O_N_LOG_N: ["predicate_pushdown", "projection_pruning", "filter_into_join"],
        ComplexityLevel.O_N_SQUARED: ["join_reordering", "subquery_unnesting", "predicate_pushdown", "filter_into_join"],
        ComplexityLevel.O_N_CUBED: ["join_reordering", "subquery_unnesting", "redundant_join_elimination"],
        ComplexityLevel.UNKNOWN: [],
    }

    def classify(self, sql: str, features: dict = None, plan_data: dict = None) -> ComplexityScore:
        sql_lower = sql.lower()
        factors = []
        score = 0.0

        # Table count
        table_count = self._count_tables(sql)
        if table_count >= 5:
            score += 25
            factors.append(f"{table_count} tables (multi-way join)")
        elif table_count >= 3:
            score += 15
            factors.append(f"{table_count} tables")
        elif table_count >= 2:
            score += 8

        # Join types
        cross_joins = len(re.findall(r"\bcross\s+join\b", sql_lower))
        outer_joins = len(re.findall(r"\b(left|right|full)\s+outer\s+join\b", sql_lower))
        regular_joins = len(re.findall(r"\bjoin\b", sql_lower)) - cross_joins

        if cross_joins > 0:
            score += 30 * cross_joins
            factors.append(f"{cross_joins}x CROSS JOIN")
        if outer_joins > 0:
            score += 10 * outer_joins
            factors.append(f"{outer_joins}x OUTER JOIN")
        if regular_joins > 2:
            score += 15 * (regular_joins - 2)

        # Subqueries
        correlated = self._count_correlated(sql_lower)
        subquery_count = self._count_subqueries(sql_lower) - correlated

        if correlated > 0:
            score += 30 * correlated
            factors.append(f"{correlated}x CORRELATED subquery")
        elif subquery_count > 0:
            score += 10 * subquery_count

        # Aggregation / sorting complexity
        has_group = "group by" in sql_lower
        has_having = "having" in sql_lower
        has_distinct = "distinct" in sql_lower
        has_window = bool(re.search(r"\b(over|partition by)\b", sql_lower))
        has_order = "order by" in sql_lower
        has_limit = "limit" in sql_lower

        if has_window:
            score += 10
            factors.append("Window function")
        if has_distinct:
            score += 6
            factors.append("DISTINCT")
        if has_group and has_having:
            score += 8
            factors.append("GROUP BY + HAVING")
        elif has_group:
            score += 5
            factors.append("GROUP BY")

        if has_order and not has_limit:
            score += 8
            factors.append("ORDER BY without LIMIT")

        # Plan-based refinement
        if plan_data:
            plan_add = self._analyze_plan(plan_data)
            score += plan_add["score_delta"]
            for f in plan_add["factors"]:
                if f not in factors:
                    factors.append(f)

        score = min(score, 100.0)

        # Classify level
        if correlated >= 2 or cross_joins >= 2:
            level = ComplexityLevel.O_N_CUBED
        elif score >= 60:
            level = ComplexityLevel.O_N_SQUARED
        elif score >= 20:
            level = ComplexityLevel.O_N_LOG_N
        else:
            level = ComplexityLevel.O_N

        # Per-level overrides
        if has_group and not has_having and regular_joins == 0 and correlated == 0:
            level = ComplexityLevel.O_N_LOG_N

        if plan_data:
            level = self._refine_from_plan(level, plan_data)

        return ComplexityScore(
            level=level,
            score=round(score, 1),
            label=self._label(level),
            factors=factors,
            recommended_rules=self.RULE_RECOMMENDATIONS.get(level, []),
            bottleneck_description=self._bottleneck(level),
            complexity_explanation=self._explanation(level, factors, table_count),
        )

    def _count_tables(self, sql: str) -> int:
        tables = set()
        for t in re.findall(r"\bjoin\s+([a-zA-Z_]\w*)", sql, re.IGNORECASE):
            tables.add(t.lower())
        from_m = re.search(r"\bfrom\s+([\w,\s]+?)(?:\bwhere\b|\bjoin\b|\bgroup\b|$)", sql, re.IGNORECASE)
        if from_m:
            for name in re.findall(r"\b([a-zA-Z_]\w*)\b", from_m.group(1)):
                if name.lower() not in ("select", "as", "on", "and", "or", "not"):
                    tables.add(name.lower())
        return len(tables)

    def _count_subqueries(self, sql_lower: str) -> int:
        return len(re.findall(r"\(\s*select\s+", sql_lower))

    def _count_correlated(self, sql_lower: str) -> int:
        count = 0
        for pattern in [r"where\s+\w+\.\w+\s+(?:=|>|<|in|exists)", r"where\s+exists\s*\(\s*select"]:
            count += len(re.findall(pattern, sql_lower))
        return count

    def _analyze_plan(self, plan_data: dict) -> dict:
        score_delta = 0.0
        factors = []
        plan = plan_data.get("Plan", {})

        def walk(node):
            nonlocal score_delta
            node_type = node.get("Node Type", "")
            cost = node.get("Total Cost", 0)
            rows = node.get("Plan Rows", 0)
            if node_type in ("Hash Join", "Merge Join") and cost > 10000 and rows > 100000:
                score_delta += 15
                factors.append(f"High-cost {node_type} ({cost:.0f} cost)")
            if node_type == "Sort" and cost > 5000:
                score_delta += 5
            for child in node.get("Plans", []):
                walk(child)

        walk(plan)
        return {"score_delta": score_delta, "factors": factors}

    def _refine_from_plan(self, level: ComplexityLevel, plan_data: dict) -> ComplexityLevel:
        total_cost = plan_data.get("Plan", {}).get("Total Cost", 0)
        if total_cost > 100000 and level in (ComplexityLevel.O_N, ComplexityLevel.O_N_LOG_N):
            return ComplexityLevel.O_N_SQUARED
        return level

    def _label(self, level: ComplexityLevel) -> str:
        return {
            ComplexityLevel.O_N: "Linear — simple scan with filter",
            ComplexityLevel.O_N_LOG_N: "Log-Linear — indexed with sort/aggregate",
            ComplexityLevel.O_N_SQUARED: "Quadratic — multi-join or correlated subquery",
            ComplexityLevel.O_N_CUBED: "Cubic — complex multi-join with subqueries",
            ComplexityLevel.UNKNOWN: "Unknown",
        }.get(level, "Unknown")

    def _bottleneck(self, level: ComplexityLevel) -> str:
        return {
            ComplexityLevel.O_N: "Linear scan over dataset. Predicate pushdown reduces rows scanned early.",
            ComplexityLevel.O_N_LOG_N: "Sort-based aggregation or indexed access. Projection pruning and predicate pushdown help.",
            ComplexityLevel.O_N_SQUARED: "Quadratic complexity from JOINs or correlated subqueries. Join reordering + subquery unnesting reduce cost.",
            ComplexityLevel.O_N_CUBED: "Cubic complexity from many JOINs + nested subqueries. Aggressive reordering + unnesting critical.",
        }.get(level, "")

    def _explanation(self, _level: ComplexityLevel, factors: list, table_count: int) -> str:
        f_str = "; ".join(factors) if factors else "structural analysis"
        return f"Complexity factors: {f_str}. Tables: {table_count}."
