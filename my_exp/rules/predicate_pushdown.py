import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from my_exp.ast_rewriter.ast_utils import parse_sql, clone_ast, ast_to_sql
from sqlglot import expressions as exp


class PredicatePushdownRule:
    """
    Predicate Pushdown Optimization — STEM 1.

    Muc dich: Day dieu kien WHERE tu query ngoai vao trong subquery,
    giam so dong trung gian can xu ly.

    Vi du:
        Input:  SELECT a, b FROM (SELECT a, b, c FROM t) AS sub WHERE a > 10;
        Output: SELECT a, b FROM (SELECT a, b, c FROM t WHERE a > 10) AS sub;

    Co che an toan (3 dieu kien):
      1. Inner query khong co DISTINCT
      2. Inner query khong co GROUP BY hoac ham aggregate (SUM, COUNT, AVG...)
      3. Tat ca cot trong dieu kien WHERE phai co mat trong inner projection

    Tai sao can thu tu kiem tra:
      - DISTINCT: pushdown co the tao duplicate vi filter ap dung truoc khi distinct
      - GROUP BY/Aggregate: filter sau khi aggregate la khac voi filter truoc
      - Cot khong ton tai: loi semantic neu cot chi co o ngoai ma khong co trong inner
    """

    def can_pushdown_condition(self, condition: exp.Expression, inner_select: exp.Select) -> bool:
        """Kiem tra xem dieu kien WHERE co the day xuong subquery khong."""
        # 1. Inner khong co DISTINCT
        if inner_select.args.get("distinct"):
            return False

        # 2. Inner khong co GROUP BY
        if inner_select.args.get("group"):
            return False

        # 3. Inner khong co ham aggregate
        for expr in inner_select.expressions:
            if expr.find(exp.AggFunc):
                return False

        # 4. Kiem tra cot trong dieu kien co ton tai trong inner projection
        has_star = False
        inner_cols = set()
        for proj in inner_select.expressions:
            if isinstance(proj, exp.Star):
                has_star = True
            elif isinstance(proj, exp.Alias):
                inner_cols.add(proj.alias.lower())
            elif isinstance(proj, exp.Column):
                inner_cols.add(proj.name.lower())

        cond_cols = {col.name.lower() for col in condition.find_all(exp.Column)}

        if not has_star:
            for c in cond_cols:
                if c not in inner_cols:
                    return False

        return True

    @property
    def description(self) -> str:
        return (
            "Day cac dieu kien WHERE tu query ngoai vao trong subquery. "
            "Chi ap dung khi subquery khong co DISTINCT, GROUP BY, hoac aggregate. "
            "Cot trong WHERE phai ton tai trong inner projection."
        )

    def apply(self, sql: str) -> str:
        """
        Thu tu thuc hien:
          1. Parse SQL thanh AST
          2. Tim tat ca cac cap (outer SELECT co WHERE + FROM la subquery)
          3. Kiem tra tinh an toan cua tung cap
          4. Neu an toan: day WHERE vao inner, xoa khoi outer
          5. Tra ve SQL da rewrite
        """
        try:
            ast = parse_sql(sql)
        except Exception:
            return sql

        ast_copy = clone_ast(ast)
        pushed = []

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
                    if self.can_pushdown_condition(condition, inner_select):
                        existing_where = inner_select.args.get("where")
                        if existing_where:
                            inner_select.where(
                                exp.and_(existing_where.this, condition), copy=False
                            )
                        else:
                            inner_select.where(condition, copy=False)
                        select.set("where", None)
                        pushed.append(condition.sql(dialect="postgres"))

        rewritten = ast_to_sql(ast_copy)

        if pushed:
            return rewritten
        return sql


if __name__ == "__main__":
    rule = PredicatePushdownRule()

    tests = [
        ("Safe pushdown",       "SELECT a, b FROM (SELECT a, b, c FROM t) AS sub WHERE a > 10;"),
        ("Unsafe (AGG)",        "SELECT sum_b FROM (SELECT a, SUM(b) AS sum_b FROM t GROUP BY a) AS sub WHERE sum_b > 100;"),
        ("Unsafe (DISTINCT)",   "SELECT a FROM (SELECT DISTINCT a, b FROM t) AS sub WHERE a = 5;"),
        ("Unsafe (col missing)","SELECT x FROM (SELECT b AS x FROM t) AS sub WHERE y = 1;"),
        ("No subquery",         "SELECT a FROM t WHERE a > 10;"),
        ("Multiple conditions", "SELECT a FROM (SELECT a, b FROM t) AS sub WHERE a > 5 AND b < 10;"),
    ]

    for name, sql in tests:
        out = rule.apply(sql)
        changed = "CHANGED" if out.strip() != sql.strip() else "unchanged"
        print(f"[{name}] {changed}")
        print(f"  IN : {sql}")
        print(f"  OUT: {out}")
        print()
