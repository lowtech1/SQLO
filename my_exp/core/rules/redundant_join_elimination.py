"""
my_exp.core.rules.redundant_join_elimination
===========================================
Luật 6: Loại Bỏ JOIN Dư Thừa (Redundant Join Elimination).
"""

import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from my_exp.ast_rewriter.ast_redundant_join_elimination import ASTRedundantJoinElimination
import re


class RedundantJoinEliminationRule:
    """
    Mục đích: Loại bỏ JOIN mà bảng được JOIN không được sử dụng
    trong SELECT, WHERE, GROUP BY, ORDER BY.

    Công thức:
        Loại bỏ JOIN nếu: col(joined_table) ∉ (SELECT ∪ WHERE ∪ GROUP ∪ ORDER)
    """

    METADATA = {
        "id": 6, "name": "Redundant Join Elimination", "name_vi": "Loại Bỏ JOIN Dư Thừa",
        "category": "join_optimization", "expected_benefit": "medium", "risk_level": "low",
        "trigger_keywords": ["unused table", "redundant join", "join not referenced"],
        "not_trigger_keywords": ["OUTER JOIN", "LEFT JOIN", "Aggregate", "HAVING"],
    }

    def __init__(self):
        self.ast_rule = ASTRedundantJoinElimination()

    def apply(self, sql: str) -> str:
        return self.ast_rule.apply(sql)

    def can_apply(self, sql: str):
        has_join = bool(re.search(r'\bJOIN\b', sql, re.IGNORECASE))
        if has_join:
            return True, "Co JOIN — kiem tra xem co du thua khong"
        return False, "Khong co JOIN"

    def explain(self, sql: str):
        can, reason = self.can_apply(sql)
        return {
            "rule": "Redundant Join Elimination", "can_apply": can, "reason": reason,
            "mechanism": "Loại bỏ JOIN nếu bảng được JOIN không được tham chiếu",
            "benefit": "Loại bỏ hoàn toàn JOIN cost: hash build + probe",
            "safety_checks": [
                "Không phải OUTER/LEFT/RIGHT/FULL JOIN",
                "Không có aggregate",
                "Bảng JOIN thực sự không được dùng"
            ],
            "example": {
                "input": "SELECT a.id, a.name FROM a JOIN b ON a.b_id = b.id WHERE a.status = 1",
                "output": "SELECT a.id, a.name FROM a WHERE a.status = 1",
                "why": "Bảng b không được dùng trong SELECT/WHERE/GROUP/ORDER"
            }
        }


if __name__ == "__main__":
    rule = RedundantJoinEliminationRule()
    tests = [
        ("Có thể loại bỏ", "SELECT a.id FROM a JOIN b ON a.b_id = b.id WHERE a.status = 1"),
        ("OUTER JOIN", "SELECT a.id FROM a LEFT JOIN b ON a.id = b.id"),
        ("Có aggregate", "SELECT a.name, COUNT(a.id) FROM a JOIN b ON a.id = b.id GROUP BY a.name"),
    ]
    for name, sql in tests:
        out = rule.apply(sql)
        changed = "CHANGED" if out.strip() != sql.strip() else "same"
        print(f"[{name}] {changed}")
        if changed == "CHANGED":
            print(f"  → {out}")
        print()
