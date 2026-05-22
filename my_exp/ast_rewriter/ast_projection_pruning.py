from sqlglot import expressions as exp
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from my_exp.ast_rewriter.ast_utils import parse_sql, clone_ast, ast_to_sql


# TPC-H schema: table_name -> [column_names in order]
TPCH_SCHEMA = {
    "customer": ["c_custkey", "c_name", "c_address", "c_nationkey", "c_phone",
                 "c_acctbal", "c_mktsegment", "c_comment"],
    "lineitem": ["l_orderkey", "l_partkey", "l_suppkey", "l_linenumber", "l_quantity",
                 "l_extendedprice", "l_discount", "l_tax", "l_returnflag", "l_linestatus",
                 "l_shipdate", "l_commitdate", "l_receiptdate", "l_shipinstruct",
                 "l_shipmode", "l_comment"],
    "nation": ["n_nationkey", "n_name", "n_regionkey", "n_comment"],
    "orders": ["o_orderkey", "o_custkey", "o_orderstatus", "o_totalprice", "o_orderdate",
               "o_orderpriority", "o_clerk", "o_shippriority", "o_comment"],
    "part": ["p_partkey", "p_name", "p_mfgr", "p_brand", "p_type", "p_size",
             "p_container", "p_retailprice", "p_comment"],
    "partsupp": ["ps_partkey", "ps_suppkey", "ps_availqty", "ps_supplycost", "ps_comment"],
    "region": ["r_regionkey", "r_name", "r_comment"],
    "supplier": ["s_suppkey", "s_name", "s_address", "s_nationkey", "s_phone",
                 "s_acctbal", "s_comment"],
}


class ASTProjectionPruning:
    """
    AST-based Projection Pruning optimization.

    Muc dich: Loai bo cot thua trong subquery, giam I/O.

    Cong thuc:
      I/O reduction = (So cot bi loai bo) / Tong so cot × Ti so giam I/O

    Hai truong hop:
      1. SELECT *: Thay * bang cac cot thuc su can thiet
      2. Cot thua: Chi giu cac cot duoc su dung o ngoai

    Han che:
      - Phai biet schema de expand SELECT *
      - Khong loai bo cot duoc tham chieu trong WHERE/HAVING cua subquery

    Thu tu thuc hien:
      1. Tim cac subquery voi SELECT *
      2. Xac dinh table goc cua subquery (tu FROM clause)
      3. Lay danh sach cot tu TPC-H schema
      4. Tim cot nao thuc su duoc su dung o ngoai
      5. Loai bo cot thua, giu cot can thiet + cot trong WHERE subquery
    """

    def _get_subquery_columns(self, subquery_select: exp.Select) -> list:
        """Lay danh sach ten bang + cot tu FROM clause cua subquery."""
        from_exp = subquery_select.args.get("from_")
        if not from_exp:
            return []

        table_expr = from_exp.this
        tables = []

        if isinstance(table_expr, exp.Table):
            tables.append((table_expr.name, table_expr.alias))
        elif isinstance(table_expr, exp.Join):
            tables.append((table_expr.this.name, table_expr.this.alias))

        for j in subquery_select.args.get("joins", []):
            t = j.this
            if isinstance(t, exp.Table):
                tables.append((t.name, t.alias))

        return tables

    def _get_required_columns(self, subquery_select: exp.Select,
                              outer_select: exp.Select) -> set:
        """
        Tim cac cot can thiet trong subquery.
        = cot trong outer SELECT (ten cot, khong can prefix)
        + cot trong WHERE/HAVING/GROUP/ORDER cua subquery
        """
        needed = set()

        if outer_select:
            for expr in outer_select.expressions:
                if isinstance(expr, exp.Column):
                    needed.add(expr.name.lower())
                elif isinstance(expr, exp.Alias):
                    needed.add(expr.alias.lower())
                elif isinstance(expr, exp.Star):
                    pass  # SELECT * needs all columns

        for node_type in ["where", "having"]:
            node = subquery_select.args.get(node_type)
            if node:
                for col in node.find_all(exp.Column):
                    needed.add(col.name.lower())

        for sort_node in subquery_select.find_all(exp.Order):
            for col in sort_node.find_all(exp.Column):
                needed.add(col.name.lower())

        return needed

    def _expand_star(self, star: exp.Star, subquery_select: exp.Select,
                     outer_select: exp.Select) -> list:
        """
        Thay SELECT * bang cac cot thuc te.
        Su dung TPC-H schema de biet cot nao ton tai.
        """
        tables = self._get_subquery_columns(subquery_select)
        if not tables:
            return [star]

        all_cols = set()
        for tbl_name, tbl_alias in tables:
            key = tbl_name.lower()
            if key in TPCH_SCHEMA:
                for col in TPCH_SCHEMA[key]:
                    all_cols.add(col.lower())

        if not all_cols:
            return [star]

        needed = self._get_required_columns(subquery_select, outer_select)
        needed_lower = needed if needed else all_cols

        kept = sorted(all_cols & needed_lower)
        if not kept:
            kept = sorted(all_cols)[:3]

        result = []
        for col_name in kept:
            result.append(exp.column(col_name))
        return result

    def _is_select_star(self, select: exp.Select) -> bool:
        """Kiem tra SELECT nao co SELECT * (khong phai derived table)."""
        if not select.expressions:
            return False
        if len(select.expressions) == 1 and isinstance(select.expressions[0], exp.Star):
            return True
        return False

    def apply(self, sql: str) -> str:
        try:
            ast = parse_sql(sql)
        except Exception:
            return sql

        ast_copy = clone_ast(ast)

        for select in ast_copy.find_all(exp.Select):
            from_exp = select.args.get("from_")
            if not from_exp:
                continue

            table_expr = from_exp.this

            if isinstance(table_expr, exp.Subquery):
                inner_select = table_expr.this
                if isinstance(inner_select, exp.Select) and self._is_select_star(inner_select):
                    sub_alias = table_expr.alias
                    if sub_alias:
                        expanded = self._expand_star(
                            inner_select.expressions[0], inner_select, select
                        )
                        inner_select.set("expressions", expanded)

        return ast_to_sql(ast_copy)


if __name__ == "__main__":
    rule = ASTProjectionPruning()

    tests = [
        ("q4: Projection Pruning",
         "SELECT c_name, c_phone FROM (SELECT * FROM customer WHERE c_mktsegment = 'AUTOMOBILE') AS sub;"),
        ("q5: Projection Pruning",
         "SELECT o_orderkey FROM (SELECT * FROM orders WHERE o_orderstatus = 'F') AS sub;"),
        ("q6: Projection Pruning (JOIN)",
         "SELECT n_name FROM (SELECT * FROM nation JOIN region ON n_regionkey = r_regionkey) AS sub;"),
        ("q10: SELECT * outer",
         "SELECT * FROM orders o JOIN customer c ON o.o_custkey = c.c_custkey;"),
    ]

    for name, sql in tests:
        out = rule.apply(sql)
        changed = out.strip() != sql.strip()
        print(f"\n[{name}] CHANGED={changed}")
        print(f"  IN : {sql}")
        print(f"  OUT: {out}")

