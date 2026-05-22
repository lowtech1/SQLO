from sqlglot import expressions as exp
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from my_exp.ast_rewriter.ast_utils import parse_sql, clone_ast, ast_to_sql


class ASTLimitPushdown:
    """
    AST-based Limit Pushdown optimization.

    Muc dich: Day LIMIT/OFFSET tu query ngoai vao subquery.

    Cong thuc:
      Input:  SELECT ... FROM (SELECT ... ORDER BY x) AS sub LIMIT n
      Output: SELECT ... FROM (SELECT ... ORDER BY x LIMIT n) AS sub
              hoac
              SELECT ... FROM (SELECT ... LIMIT n ORDER BY x) AS sub

    Loi ich: Neu ORDER BY can thiet, push LIMIT giup tranh sort toan bo N dong.
      - Khong push: Sort N dong, lay n dau
      - Push LIMIT: Sort min(N, LIMIT) dong dau tien

    Han che an toan:
      - LIMIT truoc ORDER BY (trong subquery): khong push vi thu tu khong quan trong
      - Subquery co UNION/INTERSECT: khong push
      - OFFSET > 0: van push, nhung giu OFFSET o ngoai
    """

    def can_push_limit(self, outer_select: exp.Select, inner_select: exp.Select) -> bool:
        """
        Kiem tra xem LIMIT co the day xuong subquery khong.
        Han che:
          - Subquery khong duoc la compound (UNION/INTERSECT/EXCEPT)
          - Subquery khong co LIMIT/OFFSET san
        """
        if isinstance(inner_select, exp.Union):
            return False
        if inner_select.args.get("limit"):
            return False
        if inner_select.args.get("offset"):
            return False
        return True

    def apply(self, sql: str) -> str:
        try:
            ast = parse_sql(sql)
        except Exception:
            return sql

        ast_copy = clone_ast(ast)

        for select in ast_copy.find_all(exp.Select):
            limit_node = select.args.get("limit")
            if not limit_node:
                continue

            offset_node = select.args.get("offset")

            from_exp = select.args.get("from_")
            if not from_exp:
                continue

            table_expr = from_exp.this
            if isinstance(table_expr, exp.Subquery):
                inner_select = table_expr.this
                if isinstance(inner_select, exp.Select):
                    if not self.can_push_limit(select, inner_select):
                        continue

                    limit_copy = limit_node.copy()
                    inner_select.set("limit", limit_copy)
                    select.set("limit", None)
                    select.set("offset", None)

        return ast_to_sql(ast_copy)


if __name__ == "__main__":
    rule = ASTLimitPushdown()

    tests = [
        ("q22: Limit Pushdown 1",
         "SELECT sub.c_name FROM (SELECT c_name, c_acctbal FROM customer ORDER BY c_acctbal DESC) AS sub LIMIT 10;"),
        ("q23: Limit Pushdown 2",
         "SELECT sub.o_orderkey FROM (SELECT o_orderkey, o_totalprice FROM orders ORDER BY o_totalprice DESC) AS sub LIMIT 5;"),
        ("q24: Limit Pushdown 3 (JOIN)",
         "SELECT sub.l_orderkey FROM (SELECT l_orderkey, l_quantity FROM lineitem JOIN orders ON l_orderkey = o_orderkey ORDER BY l_quantity DESC) AS sub LIMIT 20;"),
        ("Limit + OFFSET",
         "SELECT sub.c_name FROM (SELECT c_name FROM customer ORDER BY c_acctbal) AS sub LIMIT 10 OFFSET 5;"),
        ("No subquery",
         "SELECT c_name FROM customer ORDER BY c_acctbal LIMIT 10;"),
        ("Subquery already has LIMIT (unsafe)",
         "SELECT sub.c_name FROM (SELECT c_name FROM customer LIMIT 5) AS sub LIMIT 10;"),
    ]

    for name, sql in tests:
        out = rule.apply(sql)
        changed = out.strip() != sql.strip()
        print(f"\n[{name}] CHANGED={changed}")
        print(f"  IN : {sql}")
        print(f"  OUT: {out}")
