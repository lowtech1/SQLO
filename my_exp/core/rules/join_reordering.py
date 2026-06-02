"""
my_exp.core.rules.join_reordering
=================================
Luật 3: Thay Đổi Thứ Tự JOIN (Join Reordering).
"""

import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from my_exp.ast_rewriter.ast_join_reordering import ASTJoinReordering
import re


class JoinReorderingRule:
    """
    Mục đích: Sắp xếp lại thứ tự JOIN để đặt bảng nhỏ hoặc bảng
    có filter nhiều lên trước, giảm intermediate row explosion.

    Công thức:
        Intermediate_rows = Tích(kích thước bảng giữa 2 JOIN)

    Điều kiện: Chỉ INNER JOIN (không LEFT/RIGHT/FULL/CROSS).
    """

    METADATA = {
        "id": 3, "name": "Join Reordering", "name_vi": "Thay Đổi Thứ Tự JOIN",
        "category": "join_optimization", "expected_benefit": "high", "risk_level": "medium",
        "trigger_keywords": ["multiple joins", "join chain", "3+ tables"],
        "not_trigger_keywords": ["LEFT JOIN", "RIGHT JOIN", "FULL JOIN"],
    }

    def __init__(self):
        self.ast_rule = ASTJoinReordering()

    def apply(self, sql: str) -> str:
        return self.ast_rule.apply(sql)

    def can_apply(self, sql: str):
        join_count = len(re.findall(r'\bJOIN\b', sql, re.IGNORECASE))
        has_outer = bool(re.search(r'\b(LEFT|RIGHT|FULL|CROSS)\s+JOIN\b', sql, re.IGNORECASE))
        if join_count >= 2 and not has_outer:
            return True, f"Query có {join_count} INNER JOINs"
        elif join_count >= 2 and has_outer:
            return False, "Query có OUTER JOIN — không an toàn để reorder"
        return False, "Ít hơn 2 JOIN"

    def explain(self, sql: str):
        can, reason = self.can_apply(sql)
        return {
            "rule": "Join Reordering", "can_apply": can, "reason": reason,
            "mechanism": "Sắp xếp lại thứ tự JOIN theo kích thước bảng + filter selectivity",
            "benefit": "Giảm intermediate rows: đặt bảng nhỏ/lọc nhiều lên trước",
            "safety_checks": ["Chỉ INNER JOIN được reorder", "JOIN condition không thay đổi"],
            "example": {
                "input": "SELECT * FROM orders o JOIN lineitem l ON o.id=l.o_id JOIN nation n ON o.n_id=n.id",
                "output": "(reordered based on table sizes)",
                "why": "nation (25 rows) → orders → lineitem (triệu rows) giảm intermediate rows"
            }
        }


if __name__ == "__main__":
    rule = JoinReorderingRule()
    tests = [
        ("Đủ JOIN", "SELECT * FROM a JOIN b ON a.id=b.id JOIN c ON b.id=c.id"),
        ("OUTER JOIN", "SELECT * FROM a LEFT JOIN b ON a.id=b.id JOIN c ON b.id=c.id"),
    ]
    for name, sql in tests:
        can, reason = rule.can_apply(sql)
        out = rule.apply(sql)
        changed = "CHANGED" if out.strip() != sql.strip() else "same"
        print(f"[{name}] can_apply={can} | {changed}")
        if changed == "CHANGED":
            print(f"  → {out}")
        print()
