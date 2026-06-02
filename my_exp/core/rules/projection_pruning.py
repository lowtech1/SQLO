"""
my_exp.core.rules.projection_pruning
====================================
Luật 2: Loại Bỏ Cột Thừa (Projection Pruning).
"""

import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from my_exp.ast_rewriter.ast_projection_pruning import ASTProjectionPruning
import re


class ProjectionPruningRule:
    """
    Mục đích: Loại bỏ các cột không sử dụng trong SELECT của subquery,
    giảm lượng dữ liệu đọc từ database.

    Công thức lợi ích:
        I/O_reduction = (cot_bỏ / tong_cot) × bandwidth_reduction
    """

    METADATA = {
        "id": 2, "name": "Projection Pruning", "name_vi": "Loại Bỏ Cột Thừa",
        "category": "io_optimization", "expected_benefit": "medium", "risk_level": "low",
        "trigger_keywords": ["SELECT *", "unused columns", "subquery projection"],
    }

    def __init__(self):
        self.ast_rule = ASTProjectionPruning()

    def apply(self, sql: str) -> str:
        return self.ast_rule.apply(sql)

    def can_apply(self, sql: str):
        # This rule only handles SELECT * patterns
        has_star = bool(re.search(r'SELECT\s+\*\s', sql, re.IGNORECASE))
        if has_star:
            return True, "Có SELECT * — có thể loại bỏ cột thừa"
        return False, "Khong co SELECT * de prune"

    def explain(self, sql: str):
        can, reason = self.can_apply(sql)
        return {
            "rule": "Projection Pruning", "can_apply": can, "reason": reason,
            "mechanism": "Loại bỏ cột không sử dụng khỏi SELECT của subquery",
            "benefit": "I/O reduction = (unused_columns / total_columns) × 100%",
            "safety_checks": [
                "Cột bỏ không trong WHERE subquery",
                "Cột bỏ không trong GROUP BY subquery",
            ],
            "example": {
                "input": "SELECT c_name FROM (SELECT * FROM customer) AS sub",
                "output": "SELECT c_name FROM (SELECT c_name FROM customer) AS sub",
                "why": "Chỉ cần c_name, các cột khác bị loại bỏ"
            }
        }


if __name__ == "__main__":
    rule = ProjectionPruningRule()
    tests = [
        ("Có SELECT *", "SELECT c_name FROM (SELECT * FROM customer) AS sub"),
        ("Có cột thừa", "SELECT a FROM (SELECT a, b, c FROM t) AS sub"),
    ]
    for name, sql in tests:
        out = rule.apply(sql)
        changed = "CHANGED" if out.strip() != sql.strip() else "same"
        print(f"[{name}] {changed}")
        if changed == "CHANGED":
            print(f"  → {out}")
        print()
