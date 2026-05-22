import sqlglot
from sqlglot import expressions as exp
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from my_exp.ast_rewriter.ast_utils import parse_sql, clone_ast, ast_to_sql


class ASTPredicatePushdown:
    """
    AST-based Predicate Pushdown optimization using sqlglot.

    Muc dich: Day WHERE condition tu query ngoai vao subquery trong FROM clause.

    Cong thuc:
      Input:  SELECT ... FROM (SELECT cols FROM t) AS sub WHERE sub.col = val
      Output: SELECT ... FROM (SELECT cols FROM t WHERE col = val) AS sub

    Loi ich: Giam so dong trung gian = N × selectivity(condition)
    Chi phi: Neu inner query nho, loi ich it. Neu inner query lon, loi ich lon.

    Han che an toan:
      - inner khong co DISTINCT, GROUP BY, HAVING, aggregate functions
      - Tat ca cot trong WHERE phai ton tai trong inner projection
      - Cac cot trong WHERE phai khong co alias o ngoai (chi cot goc)
    """

    def __init__(self, debug=False):
        self.debug = debug

    def can_pushdown_condition(self, condition: exp.Expression, inner_select: exp.Select) -> bool:
        """
        Checks if a condition can be safely pushed down into the inner_select.
        Rules:
        1. inner_select cannot have DISTINCT.
        2. inner_select cannot have GROUP BY / HAVING / Aggregates.
        3. All columns used in the condition must exist in the inner_select projection.
        """
        if inner_select.args.get("distinct"):
            return False
        if inner_select.args.get("group"):
            return False
        if inner_select.args.get("having"):
            return False

        for expr in inner_select.expressions:
            if expr.find(exp.AggFunc):
                return False

        has_star = any(isinstance(p, exp.Star) for p in inner_select.expressions)
        inner_cols = set()
        for proj in inner_select.expressions:
            if isinstance(proj, exp.Alias):
                inner_cols.add(proj.alias.lower())
            elif isinstance(proj, exp.Column):
                inner_cols.add(proj.name.lower())

        cond_cols = {col.name.lower() for col in condition.find_all(exp.Column)}
        if not has_star:
            for c in cond_cols:
                if c not in inner_cols:
                    return False

        return True

    def _strip_outer_alias(self, node: exp.Expression, outer_alias: str):
        """
        Strip outer derived-table alias prefix from Column nodes.

        Bug fix: Khi outer query su dung 'sub.col', 'sub' la alias cua derived table.
        Khi push condition xuong inner query, 'sub' khong ton tai trong inner scope.
        -> Phai chuyen 'sub.col' thanh 'col'.

        Vi du:
          outer: SELECT ... FROM (SELECT c_custkey, c_name FROM customer) AS sub
                 WHERE sub.c_mktsegment = 'BUILDING'
          inner: SELECT c_custkey, c_name FROM customer
          sau fix: WHERE c_mktsegment = 'BUILDING'  (khong con 'sub.')
        """
        for col in node.find_all(exp.Column):
            if col.table and col.table.lower() == outer_alias.lower():
                col.set("table", None)

    def apply(self, sql: str) -> str:
        try:
            ast = parse_sql(sql)
        except Exception:
            return sql

        ast_copy = clone_ast(ast)
        pushed_predicates = []

        for select in ast_copy.find_all(exp.Select):
            where = select.args.get("where")
            if not where:
                continue

            from_exp = select.args.get("from_")
            if not from_exp:
                continue

            table_expr = from_exp.this
            if isinstance(table_expr, exp.Subquery):
                inner_select = table_expr.this
                if isinstance(inner_select, exp.Select):
                    condition = where.this
                    outer_alias = table_expr.alias

                    if outer_alias and self.can_pushdown_condition(condition, inner_select):
                        existing_where = inner_select.args.get("where")

                        cond_copy = condition.copy()
                        self._strip_outer_alias(cond_copy, outer_alias)

                        if existing_where:
                            inner_select.where(exp.and_(existing_where.this, cond_copy), copy=False)
                        else:
                            inner_select.where(cond_copy, copy=False)

                        select.set("where", None)
                        pushed_predicates.append(cond_copy.sql(dialect="postgres"))

        rewritten_sql = ast_to_sql(ast_copy)

        if self.debug:
            print("Original SQL :", sql)
            print("Rewritten SQL:", rewritten_sql)
            if pushed_predicates:
                print("Pushed Preds :", ", ".join(pushed_predicates))
            else:
                print("Pushed Preds : None (Unsafe or missing)")
            print("-" * 50)

        return rewritten_sql


if __name__ == "__main__":
    rule = ASTPredicatePushdown(debug=True)

    print("\n[Test 1] Simple pushdown (Safe)")
    sql1 = "SELECT a, b FROM (SELECT a, b FROM t) AS sub WHERE a > 10;"
    rule.apply(sql1)

    print("\n[Test 2] Aggregation case (Unsafe)")
    sql2 = "SELECT a, sum_b FROM (SELECT a, SUM(b) AS sum_b FROM t GROUP BY a) AS sub WHERE sum_b > 100;"
    rule.apply(sql2)

    print("\n[Test 3] DISTINCT case (Unsafe)")
    sql3 = "SELECT a FROM (SELECT DISTINCT a, b FROM t) AS sub WHERE a = 5;"
    rule.apply(sql3)

    print("\n[Test 4] Missing column case (Unsafe)")
    sql4 = "SELECT x FROM (SELECT b AS x FROM t) AS sub WHERE y = 1;"
    rule.apply(sql4)

    print("\n[Test 5] Real TPC-H query (sub.c_mktsegment alias)")
    sql5 = "SELECT sub.c_name, sub.c_phone FROM (SELECT c_custkey, c_name, c_phone, c_mktsegment FROM customer) AS sub WHERE sub.c_mktsegment = 'BUILDING';"
    rule.apply(sql5)
