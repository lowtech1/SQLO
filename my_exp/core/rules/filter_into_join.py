"""
my_exp.core.rules.filter_into_join
==================================
Luật 7: Đẩy Filter Vào JOIN (Filter Into Join).
"""

import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from my_exp.ast_rewriter.ast_filter_into_join import ASTFilterIntoJoin
import re


class FilterIntoJoinRule:
    """
    Mục đích: Di chuyển điều kiện WHERE từ WHERE clause chung
    vào JOIN ON clause để filter chạy cùng với JOIN operation.

    Công thức:
        Rows_join = Rows × selectivity(filter)
    """

    METADATA = {
        "id": 7, "name": "Filter Into Join", "name_vi": "Đẩy Filter Vào JOIN",
        "category": "filter_optimization", "expected_benefit": "high", "risk_level": "medium",
        "trigger_keywords": ["WHERE on join table", "filter before join"],
        "not_trigger_keywords": ["LEFT JOIN filter", "subquery filter"],
    }

    def __init__(self):
        self.ast_rule = ASTFilterIntoJoin()

    def apply(self, sql: str) -> str:
        return self.ast_rule.apply(sql)

    def can_apply(self, sql: str):
        has_join = bool(re.search(r'\bJOIN\b', sql, re.IGNORECASE))
        has_where = bool(re.search(r'\bWHERE\b', sql, re.IGNORECASE))
        if has_join and has_where:
            return True, "JOIN voi WHERE filter — co the day vao ON clause"
        return False, "Khong co JOIN voi WHERE"

    def explain(self, sql: str):
        can, reason = self.can_apply(sql)
        return {
            "rule": "Filter Into Join", "can_apply": can, "reason": reason,
            "mechanism": "Di chuyển WHERE filter vào JOIN ON clause",
            "benefit": "Filter chạy song song với JOIN: Rows_join = Rows × selectivity",
            "safety_checks": [
                "Chỉ INNER JOIN",
                "Filter không chứa subquery",
                "Filter không chứa OR phức tạp"
            ],
            "example": {
                "input": "SELECT * FROM a JOIN b ON a.id = b.a_id WHERE b.status = 'ACTIVE'",
                "output": "SELECT * FROM a JOIN b ON a.id = b.a_id AND b.status = 'ACTIVE'",
                "why": "Filter b.status chạy trong JOIN thay vì sau khi JOIN xong"
            }
        }


if __name__ == "__main__":
    rule = FilterIntoJoinRule()
    tests = [
        ("INNER JOIN", "SELECT * FROM a JOIN b ON a.id = b.a_id WHERE b.status = 'ACTIVE'"),
        ("LEFT JOIN", "SELECT * FROM a LEFT JOIN b ON a.id = b.id WHERE b.status = 'ACTIVE'"),
    ]
    for name, sql in tests:
        out = rule.apply(sql)
        changed = "CHANGED" if out.strip() != sql.strip() else "same"
        print(f"[{name}] {changed}")
        if changed == "CHANGED":
            print(f"  → {out}")
        print()
