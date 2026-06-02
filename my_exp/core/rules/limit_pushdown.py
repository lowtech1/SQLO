"""
my_exp.core.rules.limit_pushdown
================================
Luật 8: Đẩy LIMIT Xuống (Limit Pushdown).
"""

import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from my_exp.ast_rewriter.ast_limit_pushdown import ASTLimitPushdown
import re


class LimitPushdownRule:
    """
    Mục đích: Đẩy LIMIT/OFFSET từ query ngoài vào subquery,
    tránh sort toàn bộ dữ liệu khi chỉ cần top-K results.

    Công thức:
        Sort_trước = N (sort toàn bộ N dòng)
        Sort_sau = min(LIMIT, N) (chỉ sort LIMIT dòng đầu)
        → Tiết kiệm O(N log N) - O(LIMIT log LIMIT)
    """

    METADATA = {
        "id": 8, "name": "Limit Pushdown", "name_vi": "Đẩy LIMIT Xuống",
        "category": "sort_optimization", "expected_benefit": "high", "risk_level": "low",
        "trigger_keywords": ["LIMIT over subquery", "LIMIT + ORDER BY"],
        "not_trigger_keywords": ["LIMIT in subquery", "UNION subquery"],
    }

    def __init__(self):
        self.ast_rule = ASTLimitPushdown()

    def apply(self, sql: str) -> str:
        return self.ast_rule.apply(sql)

    def can_apply(self, sql: str):
        has_limit = bool(re.search(r'\bLIMIT\b', sql, re.IGNORECASE))
        has_subquery = bool(re.search(r'\)\s+AS\s+\w+', sql, re.IGNORECASE))
        if has_limit and has_subquery:
            return True, "LIMIT tren subquery — co the day xuong"
        return False, "Khong co LIMIT tren subquery"

    def explain(self, sql: str):
        can, reason = self.can_apply(sql)
        return {
            "rule": "Limit Pushdown", "can_apply": can, "reason": reason,
            "mechanism": "Di chuyển LIMIT từ query ngoài vào subquery",
            "benefit": "Tránh sort toàn bộ: O(N log N) → O(LIMIT log LIMIT)",
            "safety_checks": [
                "Subquery không có LIMIT sẵn",
                "Subquery không phải UNION/INTERSECT/EXCEPT"
            ],
            "example": {
                "input": "SELECT * FROM (SELECT * FROM orders ORDER BY o_totalprice DESC) AS sub LIMIT 10",
                "output": "SELECT * FROM (SELECT * FROM orders ORDER BY o_totalprice DESC LIMIT 10) AS sub",
                "why": "Chỉ sort 10 dòng thay vì sort toàn bộ orders"
            }
        }


if __name__ == "__main__":
    rule = LimitPushdownRule()
    tests = [
        ("Có LIMIT", "SELECT * FROM (SELECT * FROM orders ORDER BY o_totalprice DESC) AS sub LIMIT 10"),
        ("LIMIT sẵn", "SELECT * FROM (SELECT * FROM orders LIMIT 5) AS sub LIMIT 10"),
    ]
    for name, sql in tests:
        out = rule.apply(sql)
        changed = "CHANGED" if out.strip() != sql.strip() else "same"
        print(f"[{name}] {changed}")
        if changed == "CHANGED":
            print(f"  → {out}")
        print()
