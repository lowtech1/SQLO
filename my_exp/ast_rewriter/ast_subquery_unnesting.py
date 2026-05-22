import sqlglot
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from my_exp.ast_rewriter.ast_utils import parse_sql


class ASTSubqueryUnnesting:
    """
    AST-based Subquery Unnesting Optimization.

    Muc dich: Chuyen doi IN/EXISTS subquery thanh JOIN de cho phep
    PostgreSQL optimizer su dung Hash Join thay vi Nested Loop.

    Su dung sqlglot optimizer de dam bao tinh dung dan.
    Cong thuc: IN (SELECT ...) -> LEFT JOIN CTE ON ... WHERE NOT CTE.key IS NULL

    Vi du:
        Input:  SELECT c_name FROM customer WHERE c_custkey IN (SELECT o_custkey FROM orders WHERE o_totalprice > 100000);
        Output: WITH "_u_0" AS (...) SELECT customer.c_name FROM customer LEFT JOIN "_u_0" ON "_u_0".o_custkey = customer.c_custkey WHERE NOT "_u_0".o_custkey IS NULL
    """

    def apply(self, sql: str) -> str:
        """
        Thu tu thuc hien:
          1. Parse SQL thanh AST
          2. Su dung sqlglot optimizer de unnest subqueries
          3. Tra ve SQL da rewrite

        Tai sao dung optimizer:
          - Duoc test ky luong boi sqlglot
          - Tu dong xu ly cac truong hop phuc tap
          - Dam bao semantic equivalence
        """
        try:
            ast = parse_sql(sql)
        except Exception:
            return sql

        try:
            optimized = sqlglot.optimizer.optimize(ast, read="postgres")
            return optimized.sql(dialect="postgres")
        except Exception:
            return sql


if __name__ == "__main__":
    rule = ASTSubqueryUnnesting()

    tests = [
        ("Simple IN",
         "SELECT c_name FROM customer WHERE c_custkey IN (SELECT o_custkey FROM orders WHERE o_totalprice > 100000);"),
        ("No subquery",
         "SELECT * FROM orders WHERE o_totalprice > 50000;"),
        ("IN with 2 tables",
         "SELECT p_name FROM part WHERE p_partkey IN (SELECT l_partkey FROM lineitem WHERE l_quantity > 40);"),
    ]

    for name, sql in tests:
        out = rule.apply(sql)
        changed = "CHANGED" if out.strip() != sql.strip() else "unchanged"
        print(f"[{name}] {changed}")
        print(f"  IN : {sql}")
        print(f"  OUT: {out}")
        print()
