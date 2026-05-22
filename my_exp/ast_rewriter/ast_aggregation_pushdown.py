from sqlglot import expressions as exp
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from my_exp.ast_rewriter.ast_utils import parse_sql, clone_ast, ast_to_sql

class ASTAggregationPushdown:
    """
    AST-based Aggregation Pushdown optimization using sqlglot.

    Muc dich: Day GROUP BY / aggregate function tu query ngoai vao subquery.

    Cong thuc:
      Input:  SELECT sub.key, SUM(sub.val) FROM (SELECT key, val FROM t) AS sub GROUP BY sub.key
      Output: SELECT sub.key, sub.sum_val FROM (SELECT key, SUM(val) AS sum_val FROM t GROUP BY key) AS sub

    Loi ich: Giam so dong trung gian tu N*M (cross product) xuong N (sau khi aggregate).

    Han che an toan:
      - Outer khong co HAVING, DISTINCT aggregate, window functions
      - Inner khong co GROUP BY, LIMIT, OFFSET san
      - Cac cot GROUP BY phai la cot goc (khong phai alias)
    """

    def __init__(self, debug=False):
        self.debug = debug

    def can_push_aggregation(self, select_node: exp.Select, inner_select: exp.Select) -> bool:
        if select_node.args.get("having"):
            return False
        for expr in select_node.expressions:
            if expr.find(exp.Window):
                return False
            agg = expr.find(exp.AggFunc)
            if agg and agg.args.get("distinct"):
                return False
        if inner_select.args.get("group") or inner_select.args.get("limit") or inner_select.args.get("offset"):
            return False
        return True

    def _build_column(self, col_name: str, table: str = None):
        """Tao Column expression voi cac tham so dung."""
        if table:
            return exp.column(col_name, table=table)
        return exp.column(col_name)

    def _strip_outer_alias(self, node: exp.Expression, outer_alias: str):
        """Strip 'sub.' prefix tu Column nodes khi di chuyen xuong inner query."""
        for col in node.find_all(exp.Column):
            if col.table and col.table.lower() == outer_alias.lower():
                col.set("table", None)

    def apply(self, sql: str) -> str:
        try:
            ast = parse_sql(sql)
        except Exception:
            return sql

        ast_copy = clone_ast(ast)
        pushed = False

        for select in ast_copy.find_all(exp.Select):
            group_node = select.args.get("group")
            if not group_node:
                continue

            from_exp = select.args.get("from_")
            if not from_exp:
                continue

            table_expr = from_exp.this
            if isinstance(table_expr, exp.Subquery):
                inner_select = table_expr.this
                if isinstance(inner_select, exp.Select):
                    if self.can_push_aggregation(select, inner_select):
                        sub_alias = table_expr.alias or "tmp_sub"
                        new_inner_exprs = []
                        new_outer_exprs = []
                        added_inner_keys = set()

                        outer_group_by = group_node.find_all(exp.Column)
                        group_key_names = []
                        for gbc in outer_group_by:
                            stripped = gbc.name
                            if stripped not in added_inner_keys:
                                group_key_names.append(stripped)
                                added_inner_keys.add(stripped)
                                inner_copy = gbc.copy()
                                inner_copy.set("table", None)
                                new_inner_exprs.append(inner_copy)
                                new_outer_exprs.append(exp.column(stripped, table=sub_alias))

                        for expr in select.expressions:
                            agg = expr.find(exp.AggFunc)
                            if agg:
                                agg_alias = expr.alias
                                if not agg_alias:
                                    c = agg.find(exp.Column)
                                    agg_alias = f"pushed_agg_{c.name if c else 'x'}"
                                inner_expr = expr.copy() if isinstance(expr, exp.Alias) else exp.alias_(expr.copy(), agg_alias)
                                self._strip_outer_alias(inner_expr, sub_alias)
                                new_inner_exprs.append(inner_expr)
                                new_outer_exprs.append(exp.column(agg_alias, table=sub_alias))

                        inner_group_bys = [self._build_column(k) for k in group_key_names]

                        inner_select.set("expressions", new_inner_exprs)
                        inner_select.set("group", exp.Group(expressions=inner_group_bys))

                        select.set("expressions", new_outer_exprs)
                        select.set("group", None)

                        pushed = True

        rewritten_sql = ast_to_sql(ast_copy)

        if self.debug:
            print("-" * 50)
            print("Original SQL :", sql)
            print("Rewritten SQL:", rewritten_sql)
            if pushed:
                print("Pushed Agg   : Yes")
            else:
                print("Pushed Agg   : No (Unsafe or missing pattern)")
            print("-" * 50)

        return rewritten_sql


if __name__ == "__main__":
    rule = ASTAggregationPushdown(debug=True)

    print("\n[Test 1] Safe aggregation pushdown")
    sql1 = "SELECT sub.a, SUM(sub.b) AS sum_b FROM (SELECT a, b FROM t) AS sub GROUP BY sub.a;"
    rule.apply(sql1)

    print("\n[Test 2] Unsafe aggregation (DISTINCT)")
    sql2 = "SELECT sub.a, COUNT(DISTINCT sub.b) AS c FROM (SELECT a, b FROM t) AS sub GROUP BY sub.a;"
    rule.apply(sql2)

    print("\n[Test 3] Unsafe aggregation (HAVING)")
    sql3 = "SELECT sub.a, SUM(sub.b) AS s FROM (SELECT a, b FROM t) AS sub GROUP BY sub.a HAVING SUM(sub.b) > 100;"
    rule.apply(sql3)

    print("\n[Test 4] Unsafe inner select (already has limit)")
    sql4 = "SELECT sub.a, SUM(sub.b) FROM (SELECT a, b FROM t LIMIT 10) AS sub GROUP BY sub.a;"
    rule.apply(sql4)

    print("\n[Test 5] TPC-H q13")
    sql5 = "SELECT sub.o_custkey, SUM(sub.o_totalprice) AS sum_price FROM (SELECT o_custkey, o_totalprice FROM orders) AS sub GROUP BY sub.o_custkey;"
    rule.apply(sql5)
