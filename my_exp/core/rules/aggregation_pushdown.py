"""
my_exp.core.rules.aggregation_pushdown
=====================================
Luật 5: Đẩy Phép Tổng Hợp Xuống (Aggregation Pushdown).
"""

import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from my_exp.ast_rewriter.ast_aggregation_pushdown import ASTAggregationPushdown
import re


class AggregationPushdownRule:
    """
    Mục đích: Đẩy GROUP BY/aggregate từ query ngoài vào subquery,
    giảm số dòng trước khi aggregate.

    Công thức:
        Rows_trước = N × M (cross product trước khi aggregate)
        Rows_sau = N / cardinality(GROUP BY keys) × M
    """

    METADATA = {
        "id": 5, "name": "Aggregation Pushdown", "name_vi": "Đẩy Phép Tổng Hợp Xuống",
        "category": "aggregation_optimization", "expected_benefit": "high", "risk_level": "medium",
        "trigger_keywords": ["GROUP BY over subquery", "aggregate over subquery"],
        "not_trigger_keywords": ["HAVING", "DISTINCT aggregate"],
    }

    def __init__(self):
        self.ast_rule = ASTAggregationPushdown()

    def apply(self, sql: str) -> str:
        return self.ast_rule.apply(sql)

    def can_apply(self, sql: str):
        has_group = bool(re.search(r'\bGROUP\s+BY\b', sql, re.IGNORECASE))
        has_subquery = bool(re.search(r'\)\s+AS\s+\w+\s', sql, re.IGNORECASE))
        if has_group and has_subquery:
            return True, "GROUP BY tren subquery — co the day xuong"
        return False, "Khong co GROUP BY tren subquery"

    def explain(self, sql: str):
        can, reason = self.can_apply(sql)
        return {
            "rule": "Aggregation Pushdown", "can_apply": can, "reason": reason,
            "mechanism": "Đẩy GROUP BY/aggregate từ query ngoài vào subquery",
            "benefit": "Giảm số dòng trước khi aggregate",
            "safety_checks": ["Outer không có HAVING", "Outer không có DISTINCT aggregate"],
            "example": {
                "input": "SELECT sub.o_custkey, SUM(sub.o_totalprice) FROM (SELECT o_custkey, o_totalprice FROM orders) AS sub GROUP BY sub.o_custkey",
                "output": "SELECT sub.o_custkey, sub.sum_price FROM (SELECT o_custkey, SUM(o_totalprice) AS sum_price FROM orders GROUP BY o_custkey) AS sub",
                "why": "Aggregate chạy trên bảng orders trước thay vì cross product"
            }
        }


if __name__ == "__main__":
    rule = AggregationPushdownRule()
    tests = [
        ("An toàn", "SELECT sub.a, SUM(sub.b) FROM (SELECT a, b FROM t) AS sub GROUP BY sub.a"),
        ("Có HAVING", "SELECT sub.a, SUM(sub.b) FROM (SELECT a, b FROM t) AS sub GROUP BY sub.a HAVING SUM(sub.b) > 100"),
    ]
    for name, sql in tests:
        can, reason = rule.can_apply(sql)
        out = rule.apply(sql)
        changed = "CHANGED" if out.strip() != sql.strip() else "same"
        print(f"[{name}] can_apply={can} | {changed}")
        if changed == "CHANGED":
            print(f"  → {out}")
        print()
