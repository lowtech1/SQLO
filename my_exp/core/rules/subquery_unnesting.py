"""
my_exp.core.rules.subquery_unnesting
====================================
Luật 4: Chuyển Subquery Thành JOIN (Subquery Unnesting).
"""

import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from my_exp.ast_rewriter.ast_subquery_unnesting import ASTSubqueryUnnesting
import re


class SubqueryUnnestingRule:
    """
    Mục đích: Chuyển IN/EXISTS subquery thành JOIN để PostgreSQL
    optimizer có thể dùng Hash Join thay vì Nested Loop.

    Công thức:
        Nested Loop: O(n × m) thời gian
        Hash Join:   O(n + m) thời gian
    """

    METADATA = {
        "id": 4, "name": "Subquery Unnesting", "name_vi": "Chuyển Subquery Thành JOIN",
        "category": "join_optimization", "expected_benefit": "high", "risk_level": "medium",
        "trigger_keywords": ["IN (SELECT)", "EXISTS (SELECT)"],
        "not_trigger_keywords": ["NOT IN", "Correlated", "HAVING inside subquery"],
    }

    def __init__(self):
        self.ast_rule = ASTSubqueryUnnesting()

    def apply(self, sql: str) -> str:
        return self.ast_rule.apply(sql)

    def can_apply(self, sql: str):
        has_in = bool(re.search(r'\bIN\s*\(\s*SELECT\b', sql, re.IGNORECASE))
        if has_in:
            return True, "IN subquery — co the chuyen thanh JOIN"
        return False, "Khong co IN/EXISTS subquery"

    def explain(self, sql: str):
        can, reason = self.can_apply(sql)
        return {
            "rule": "Subquery Unnesting", "can_apply": can, "reason": reason,
            "mechanism": "Chuyển IN subquery thành LEFT JOIN với subquery được đặt tên",
            "benefit": "Nested Loop O(n×m) → Hash Join O(n+m), giảm đáng kể thời gian",
            "safety_checks": [
                "Subquery không correlated (không tham chiếu cột ngoài)",
                "Subquery chỉ có 1 bảng",
                "Không phải NOT IN"
            ],
            "example": {
                "input": "SELECT c_name FROM customer WHERE c_custkey IN (SELECT o_custkey FROM orders WHERE o_totalprice > 100000)",
                "output": "SELECT DISTINCT customer.c_name FROM customer JOIN (SELECT DISTINCT o_custkey FROM orders WHERE o_totalprice > 100000) _sq ON customer.c_custkey = _sq.o_custkey",
                "why": "Hash Join thay vì Nested Loop"
            }
        }


if __name__ == "__main__":
    rule = SubqueryUnnestingRule()
    tests = [
        ("IN subquery", "SELECT c_name FROM customer WHERE c_custkey IN (SELECT o_custkey FROM orders);"),
        ("NOT IN", "SELECT * FROM a WHERE a.id NOT IN (SELECT b.id FROM b);"),
    ]
    for name, sql in tests:
        can, reason = rule.can_apply(sql)
        out = rule.apply(sql)
        changed = "CHANGED" if out.strip() != sql.strip() else "same"
        print(f"[{name}] can_apply={can} | {changed}")
        if changed == "CHANGED":
            print(f"  → {out}")
        print()
