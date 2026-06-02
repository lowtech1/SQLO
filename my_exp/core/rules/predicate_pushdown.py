"""
my_exp.core.rules.predicate_pushdown
====================================
Luật 1: Đẩy Điều Kiện Lọc Xuống (Predicate Pushdown).
"""

import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from my_exp.ast_rewriter.ast_predicate_pushdown import ASTPredicatePushdown
from my_exp.core.sql_parser import parse_sql
from sqlglot import expressions as exp


class PredicatePushdownRule:
    """
    Mục đích: Di chuyển WHERE từ query ngoài vào subquery trong FROM clause.

    Công thức lợi ích:
        Rows_after = Rows_before × selectivity(filter)

    Điều kiện an toàn:
        1. Inner query không có DISTINCT
        2. Inner query không có GROUP BY hoặc aggregate
        3. Tất cả cột trong WHERE phải tồn tại trong inner projection

    Ví dụ:
        Input:  SELECT a, b FROM (SELECT a, b, c FROM t) AS sub WHERE a > 10
        Output: SELECT a, b FROM (SELECT a, b, c FROM t WHERE a > 10) AS sub
    """

    METADATA = {
        "id": 1, "name": "Predicate Pushdown", "name_vi": "Đẩy Điều Kiện Lọc Xuống",
        "category": "filter_optimization", "expected_benefit": "high", "risk_level": "low",
        "trigger_keywords": ["WHERE on subquery", "outer WHERE + subquery"],
        "not_trigger_keywords": ["DISTINCT", "GROUP BY", "HAVING", "Aggregate"],
    }

    def __init__(self):
        self.ast_rule = ASTPredicatePushdown()

    def apply(self, sql: str) -> str:
        return self.ast_rule.apply(sql)

    def can_apply(self, sql: str):
        try:
            ast = parse_sql(sql)
        except Exception:
            return False, "Parse error"
        if ast is None:
            return False, "Khong parse duoc SQL"

        from my_exp.core.sql_parser import extract_where, extract_subqueries

        has_where = extract_where(ast) is not None
        has_sq = len(extract_subqueries(ast)) > 0
        if not (has_where and has_sq):
            return False, "Khong co WHERE tren subquery"

        for sq in extract_subqueries(ast):
            inner = sq.this
            if isinstance(inner, exp.Select):
                if inner.args.get("distinct"):
                    return False, "Subquery co DISTINCT — khong an toan"
                if inner.args.get("group"):
                    return False, "Subquery co GROUP BY — khong an toan"
                # Check aggregates ONLY in inner's own SELECT list, not nested deeper
                for expr in inner.expressions:
                    if isinstance(expr, exp.AggFunc):
                        return False, "Subquery co aggregate — khong an toan"
                # Also check inner's WHERE
                inner_where = inner.args.get("where")
                if inner_where:
                    for node in inner_where.walk():
                        if isinstance(node, exp.AggFunc):
                            return False, "Subquery co aggregate trong WHERE — khong an toan"

                # Check: all WHERE columns must exist in inner projection
                where = extract_where(ast)
                if where:
                    where_cols = {col.name.lower() for col in where.find_all(exp.Column)}
                    inner_cols = set()
                    has_star = any(isinstance(p, exp.Star) for p in inner.expressions)
                    if not has_star:
                        for proj in inner.expressions:
                            if isinstance(proj, exp.Alias):
                                inner_cols.add(proj.alias.lower())
                            elif isinstance(proj, exp.Column):
                                inner_cols.add(proj.name.lower())
                        missing = where_cols - inner_cols
                        if missing:
                            return False, f"Cot {missing} trong WHERE khong ton tai trong subquery"

        return True, "Dieu kien WHERE co the day vao subquery an toan"

    def explain(self, sql: str):
        can, reason = self.can_apply(sql)
        return {
            "rule": "Predicate Pushdown", "can_apply": can, "reason": reason,
            "mechanism": "Di chuyển WHERE từ query ngoài vào subquery trong FROM clause",
            "benefit": "Giảm số dòng trung gian: N × selectivity(filter)",
            "safety_checks": [
                "Subquery không có DISTINCT",
                "Subquery không có GROUP BY",
                "Subquery không có aggregate (SUM/COUNT/AVG/MIN/MAX)",
                "Cột trong WHERE tồn tại trong inner projection"
            ],
            "example": {
                "input": "SELECT a FROM (SELECT a, b FROM t) AS sub WHERE a > 10",
                "output": "SELECT a FROM (SELECT a, b FROM t WHERE a > 10) AS sub",
                "why": "Filter a > 10 chạy trước, chỉ giữ dòng thỏa mãn điều kiện"
            }
        }


if __name__ == "__main__":
    rule = PredicatePushdownRule()
    tests = [
        ("An toàn", "SELECT a FROM (SELECT a, b FROM t) AS sub WHERE a > 10"),
        ("Không an toàn (AGG)", "SELECT sum_b FROM (SELECT a, SUM(b) AS sum_b FROM t GROUP BY a) AS sub WHERE sum_b > 100"),
        ("Không an toàn (DISTINCT)", "SELECT a FROM (SELECT DISTINCT a, b FROM t) AS sub WHERE a = 5"),
    ]
    for name, sql in tests:
        can, reason = rule.can_apply(sql)
        out = rule.apply(sql)
        changed = "CHANGED" if out.strip() != sql.strip() else "same"
        print(f"[{name}] can_apply={can} | reason={reason}")
        if changed == "CHANGED":
            print(f"  Rewrite: {out}")
        print()
