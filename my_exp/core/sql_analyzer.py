"""
my_exp.core.sql_analyzer
=======================
SQL feature extraction and pattern detection.
Schema-agnostic: analyzes SQL structure without hardcoding dataset-specific patterns.
"""

import re
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from sqlglot import expressions as exp

from my_exp.core.sql_parser import (
    parse_sql, extract_tables, extract_columns, extract_subqueries,
    extract_joins, extract_where, extract_group_by, extract_having,
    extract_order_by, extract_limit, has_aggregate_functions, has_distinct,
    count_join_operators, count_tables_in_from, get_select_columns
)
from my_exp.core.schema_loader import DatabaseSchema

from typing import Optional


class SQLFeatureExtractor:
    """
    Extracts structural features from SQL query using AST analysis.
    These features are used to determine which optimization rules apply.
    """

    def __init__(self, schema: Optional[DatabaseSchema] = None):
        self.schema = schema

    def extract(self, sql: str) -> dict:
        """
        Full feature extraction pipeline.

        Returns:
            dict with keys: parsing, structural, complexity, optimization_opportunities
        """
        # Parse
        ast = parse_sql(sql)
        if ast is None:
            return {
                "parsing": {"success": False, "error": "Failed to parse SQL"},
                "structural": {},
                "complexity": {},
                "optimization_opportunities": [],
            }

        # Structural features
        features = {
            "parsing": {"success": True},

            # Tables & joins
            "tables": extract_tables(ast),
            "table_count": count_tables_in_from(ast),
            "join_count": count_join_operators(ast),
            "joins": self._analyze_joins(ast),

            # Subqueries
            "subquery_count": len(extract_subqueries(ast)),
            "subqueries": self._analyze_subqueries(ast),
            "has_correlated_subquery": self._has_correlated_subquery(sql, ast),

            # Filtering & projection
            "has_where": extract_where(ast) is not None,
            "has_select_star": self._has_select_star(sql),
            "has_unused_columns": self._has_unused_columns(sql, ast),
            "projection_columns": get_select_columns(ast),

            # Aggregation
            "has_aggregation": has_aggregate_functions(ast),
            "has_group_by": extract_group_by(ast) is not None,
            "has_having": extract_having(ast) is not None,
            "aggregates": self._extract_aggregates(ast),

            # Sorting & limiting
            "has_order_by": extract_order_by(ast) is not None,
            "has_limit": extract_limit(ast) is not None,
            "has_distinct": has_distinct(ast),

            # Set operations
            "has_union": bool(re.search(r'\bUNION\b', sql, re.IGNORECASE)),
            "has_intersect": bool(re.search(r'\bINTERSECT\b', sql, re.IGNORECASE)),
            "has_except": bool(re.search(r'\bEXCEPT\b', sql, re.IGNORECASE)),

            # CTEs
            "has_cte": bool(re.search(r'\bWITH\b', sql, re.IGNORECASE)),
            "cte_count": len(re.findall(r'\)\s+AS\s+\(', sql)),

            # Columns
            "columns_used": extract_columns(ast),
        }

        # Complexity score
        features["complexity"] = self._compute_complexity(features)

        # Optimization opportunities
        features["optimization_opportunities"] = self._detect_opportunities(sql, ast, features)

        return features

    def _analyze_joins(self, ast) -> list:
        """Analyze JOIN types and conditions."""
        joins = []
        for join in extract_joins(ast):
            join_type = "CROSS"
            condition = None
            if hasattr(join, 'side') and join.side:
                join_type = str(join.side).upper()
            if hasattr(join, 'condition') and join.condition:
                condition = str(join.condition)

            joins.append({
                "type": join_type,
                "condition": condition,
                "kind": str(join.kind).upper() if hasattr(join, 'kind') else "INNER",
            })
        return joins

    def _analyze_subqueries(self, ast) -> list:
        """Analyze subquery types and locations."""
        subqueries = []
        for sq in extract_subqueries(ast):
            inner = sq.this
            if isinstance(inner, exp.Select):
                has_agg = has_aggregate_functions(inner)
                has_where = inner.args.get("where") is not None
                has_group = inner.args.get("group") is not None
                has_limit = inner.args.get("limit") is not None
                subqueries.append({
                    "type": "scalar" if not has_agg else "aggregate",
                    "has_where": has_where,
                    "has_group_by": has_group,
                    "has_limit": has_limit,
                })
        return subqueries

    def _has_correlated_subquery(self, sql: str, ast) -> bool:
        """Check if query has correlated subqueries."""
        # Pattern: outer table reference in subquery WHERE
        outer_refs = set(re.findall(r'\b([a-zA-Z_]\w*)\.[a-zA-Z_]\w*', sql.split('WHERE', 1)[0] if 'WHERE' in sql else sql))
        if 'WHERE' in sql.upper():
            where_part = sql.split('WHERE', 1)[1]
            subquery_match = re.search(r'\)\s+AS\s+\w+\s+WHERE\b|\bEXISTS\b|\bIN\s*\(', where_part, re.IGNORECASE)
            if subquery_match:
                return True
        return False

    def _has_select_star(self, sql: str) -> bool:
        """Check if SELECT contains * (wildcard)."""
        sql_upper = sql.upper()
        patterns = [
            r'SELECT\s+\*\s+FROM',
            r'SELECT\s+\*[\s,)]',
            r'SELECT\s+DISTINCT\s+\*\s+',
        ]
        for p in patterns:
            if re.search(p, sql_upper):
                return True
        return False

    def _has_unused_columns(self, sql: str, ast) -> bool:
        """Check if subqueries have columns not used in outer query."""
        # Pattern: SELECT inner.col FROM (SELECT a,b,c FROM t) WHERE inner.col references only a subset
        # Simple heuristic: if there are subqueries with more columns than referenced in outer
        return False  # Conservative - requires semantic analysis

    def _extract_aggregates(self, ast) -> list:
        """Extract aggregate function details."""
        found = []
        for node in ast.walk():
            if isinstance(node, exp.AggFunc):
                found.append(str(node))
        return found

    def _compute_complexity(self, features: dict) -> dict:
        """Compute SQL complexity metrics."""
        score = 0
        factors = []

        # Table complexity
        score += min(features["table_count"], 5)
        if features["table_count"] > 3:
            factors.append(f"{features['table_count']} tables")

        # Join complexity
        score += features["join_count"] * 2
        if features["join_count"] > 0:
            factors.append(f"{features['join_count']} joins")

        # Subquery complexity
        score += features["subquery_count"] * 3
        if features["subquery_count"] > 0:
            factors.append(f"{features['subquery_count']} subqueries")
            if features.get("has_correlated_subquery"):
                score += 5
                factors.append("correlated subquery")

        # Aggregation complexity
        if features["has_group_by"]:
            score += 2
        if features["has_having"]:
            score += 3
        if features["has_aggregation"]:
            factors.append("aggregation")

        # Sorting complexity
        if features["has_order_by"]:
            score += 1
        if features["has_distinct"]:
            score += 2
            factors.append("DISTINCT")

        # CTE complexity
        if features["has_cte"]:
            score += features.get("cte_count", 1) * 2
            factors.append(f"{features.get('cte_count', 0)} CTEs")

        # Set operations
        if features.get("has_union") or features.get("has_intersect") or features.get("has_except"):
            score += 3
            factors.append("set operations")

        # Determine level
        if score <= 3:
            level = "Rất đơn giản"
            level_en = "Very Simple"
        elif score <= 7:
            level = "Đơn giản"
            level_en = "Simple"
        elif score <= 12:
            level = "Trung bình"
            level_en = "Medium"
        elif score <= 20:
            level = "Phức tạp"
            level_en = "Complex"
        else:
            level = "Rất phức tạp"
            level_en = "Very Complex"

        return {
            "score": score,
            "level": level,
            "level_en": level_en,
            "factors": factors,
        }

    def _detect_opportunities(self, sql: str, ast, features: dict) -> list:
        """
        Detect which optimization opportunities exist in the query.
        Each opportunity maps to a specific rewrite rule.
        """
        opportunities = []

        # 1. Predicate Pushdown: WHERE on outer query + subquery
        if self._can_pushdown_predicate(sql, ast):
            opportunities.append({
                "rule": "predicate_pushdown",
                "confidence": "high",
                "location": self._find_predicate_pushdown_location(sql),
                "estimated_benefit": "Cao — giảm số dòng trung gian",
                "formula": "Rows_after = Rows_before × selectivity(filter)",
            })

        # 2. Projection Pruning: SELECT * or unused columns
        if features["has_select_star"]:
            opportunities.append({
                "rule": "projection_pruning",
                "confidence": "medium",
                "location": "subquery SELECT",
                "estimated_benefit": "Trung bình — giảm I/O bandwidth",
                "formula": "I/O reduction = (unused_columns / total_columns) × 100%",
            })

        # 3. Subquery Unnesting: IN/EXISTS subquery with joins
        if self._can_unnest_subquery(sql, ast, features):
            opportunities.append({
                "rule": "subquery_unnesting",
                "confidence": "high",
                "location": self._find_subquery_location(sql),
                "estimated_benefit": "Cao — Nested Loop O(n×m) → Hash Join O(n+m)",
                "formula": "Time: O(n×m) → O(n+m), Space: O(1) → O(m)",
            })

        # 4. Join Reordering: 3+ joins
        if features["join_count"] >= 2:
            opportunities.append({
                "rule": "join_reordering",
                "confidence": "medium",
                "location": "JOIN chain",
                "estimated_benefit": "Cao — giảm dòng trung gian theo cấp số nhân",
                "formula": "Intermediate_rows = Π(size of intermediate tables)",
            })

        # 5. Aggregation Pushdown: GROUP BY over subquery
        if features["has_group_by"] and features["subquery_count"] > 0:
            opportunities.append({
                "rule": "aggregation_pushdown",
                "confidence": "medium",
                "location": "outer GROUP BY over subquery",
                "estimated_benefit": "Trung bình — giảm dòng trước khi GROUP BY",
                "formula": "Rows_reduced = N / cardinality(group_keys)",
            })

        # 6. Redundant Join Elimination: JOIN without using joined columns
        if self._has_redundant_join(sql, ast, features):
            opportunities.append({
                "rule": "redundant_join_elimination",
                "confidence": "medium",
                "location": self._find_redundant_join_location(sql),
                "estimated_benefit": "Trung bình — loại bỏ JOIN không cần thiết",
                "formula": "Remove JOIN if: col(joined_table) ∉ SELECT ∪ WHERE ∪ GROUP",
            })

        # 7. Filter Into Join: WHERE on join table
        if features["join_count"] >= 1 and features["has_where"]:
            if self._can_filter_into_join(sql, ast):
                opportunities.append({
                    "rule": "filter_into_join",
                    "confidence": "high",
                    "location": "WHERE clause",
                    "estimated_benefit": "Cao — filter chạy cùng JOIN, giảm đầu vào",
                    "formula": "Rows_join = Rows × selectivity(filter)",
                })

        # 8. Limit Pushdown: LIMIT over subquery
        if features["has_limit"] and features["subquery_count"] > 0:
            opportunities.append({
                "rule": "limit_pushdown",
                "confidence": "medium",
                "location": "LIMIT clause",
                "estimated_benefit": "Cao — tránh sort toàn bộ dữ liệu",
                "formula": "Sort_rows_after = MIN(LIMIT, N) vs Sort_rows_before = N",
            })

        return opportunities

    def _can_pushdown_predicate(self, sql: str, ast) -> bool:
        """Check if predicate can be pushed down into subquery."""
        # Check for WHERE on outer query + subquery in FROM
        has_outer_where = extract_where(ast) is not None
        has_subquery = len(extract_subqueries(ast)) > 0
        if not (has_outer_where and has_subquery):
            return False

        # Check that subquery doesn't have blocking constructs
        for sq in extract_subqueries(ast):
            inner = sq.this
            if isinstance(inner, exp.Select):
                if has_distinct(inner):
                    return False
                if inner.args.get("group"):
                    return False
                if has_aggregate_functions(inner):
                    return False
        return True

    def _find_predicate_pushdown_location(self, sql: str) -> str:
        """Find WHERE clause location for predicate pushdown."""
        # Find subquery aliases with WHERE after them
        matches = re.findall(r'\)\s+AS\s+(\w+)\s+WHERE', sql, re.IGNORECASE)
        if matches:
            return f"outer WHERE on subquery alias '{matches[0]}'"
        return "outer WHERE clause"

    def _can_unnest_subquery(self, sql: str, ast, features) -> bool:
        """Check if subquery can be unnested (converted to JOIN)."""
        has_in_subquery = bool(re.search(r'\bIN\s*\(\s*SELECT\b', sql, re.IGNORECASE))
        has_exists = bool(re.search(r'\bEXISTS\s*\(\s*SELECT\b', sql, re.IGNORECASE))
        if not (has_in_subquery or has_exists):
            return False

        # Check for blocking conditions
        for sq in extract_subqueries(ast):
            inner = sq.this
            if isinstance(inner, exp.Select):
                # Scalar subquery with aggregates can't always be unnested
                if has_aggregate_functions(inner) and not inner.args.get("group"):
                    return False  # Scalar aggregate - can't unnest safely

        return True

    def _find_subquery_location(self, sql: str) -> str:
        """Find location of IN/EXISTS subquery."""
        if re.search(r'\bWHERE\b.*\bIN\s*\(\s*SELECT\b', sql, re.IGNORECASE | re.DOTALL):
            return "WHERE ... IN (SELECT ...)"
        if re.search(r'\bWHERE\b.*\bEXISTS\s*\(\s*SELECT\b', sql, re.IGNORECASE | re.DOTALL):
            return "WHERE ... EXISTS (SELECT ...)"
        return "subquery in WHERE clause"

    def _has_redundant_join(self, sql: str, ast, features) -> bool:
        """Check if there are JOINs whose tables aren't referenced."""
        # This requires column usage analysis
        # Conservative: only detect when there's a clear pattern
        if features["join_count"] < 1:
            return False

        # Pattern: JOIN followed by no reference to joined table columns
        # Very conservative - may produce false negatives
        return False

    def _find_redundant_join_location(self, sql: str) -> str:
        """Find location of potentially redundant JOIN."""
        return "JOIN clause"

    def _can_filter_into_join(self, sql: str, ast) -> bool:
        """Check if WHERE conditions can be pushed into JOIN."""
        # Check if WHERE references columns from joined tables
        where = extract_where(ast)
        if not where:
            return False

        joins = extract_joins(ast)
        if not joins:
            return False

        # Check if WHERE references join table columns
        for col in ast.find_all(exp.Column):
            for join in joins:
                if hasattr(join, 'this') and isinstance(join.this, exp.Table):
                    table_name = join.this.name
                    if col.table == table_name or col.table == join.this.alias:
                        return True
        return False


class RuleApplicabilityScorer:
    """
    Scores each optimization rule based on detected opportunities.
    Used by the KB to determine rule priority.
    """

    def __init__(self):
        self.extractor = SQLFeatureExtractor()

    def score(self, sql: str, schema: Optional[DatabaseSchema] = None) -> dict:
        """
        Score all rules for a given SQL query.

        Returns:
            dict: {rule_name: {"applicable": bool, "score": float, "reason": str, "benefit": str}}
        """
        if schema:
            self.extractor.schema = schema

        features = self.extractor.extract(sql)
        if not features["parsing"]["success"]:
            return {}

        opportunities = features.get("optimization_opportunities", [])

        # Initialize all rules with default scores
        all_rules = [
            "predicate_pushdown",
            "projection_pruning",
            "join_reordering",
            "subquery_unnesting",
            "aggregation_pushdown",
            "redundant_join_elimination",
            "filter_into_join",
            "limit_pushdown",
        ]

        # Confidence weights for scoring
        confidence_map = {"high": 1.0, "medium": 0.7, "low": 0.4}

        results = {}
        for rule in all_rules:
            # Find opportunity for this rule
            opp = next((o for o in opportunities if o["rule"] == rule), None)
            if opp:
                score = confidence_map.get(opp["confidence"], 0.5)
                results[rule] = {
                    "applicable": True,
                    "score": round(score, 3),
                    "confidence": opp["confidence"],
                    "reason": opp.get("location", ""),
                    "benefit": opp.get("estimated_benefit", ""),
                    "formula": opp.get("formula", ""),
                    "details": opp,
                }
            else:
                results[rule] = {
                    "applicable": False,
                    "score": 0.0,
                    "confidence": None,
                    "reason": "Không phát hiện cơ hội tối ưu",
                    "benefit": None,
                    "formula": None,
                    "details": None,
                }

        # Sort by score
        ranked = sorted(
            [(r, d) for r, d in results.items() if d["applicable"]],
            key=lambda x: x[1]["score"],
            reverse=True
        )

        return results, ranked, features
