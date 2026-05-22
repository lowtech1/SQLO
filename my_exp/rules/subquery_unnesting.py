import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from my_exp.ast_rewriter.ast_utils import parse_sql, clone_ast, ast_to_sql
from sqlglot import expressions as exp


class SubqueryUnnestingRule:
    """
    Subquery Unnesting Optimization — STEM 3.

    Muc dich: Chuyen doi IN/EXISTS subquery thanh JOIN de cho phep
    query optimizer su dung Hash Join thay vi Nested Loop, giam dang ke
    thoi gian voi tap du lieu lon.

    Vi du:
        Input:  SELECT c_name FROM customer WHERE c_custkey IN (SELECT o_custkey FROM orders WHERE o_totalprice > 100000);
        Output: SELECT DISTINCT customer.c_name FROM customer JOIN orders ON customer.c_custkey = orders.o_custkey WHERE orders.o_totalprice > 100000;

    Tai sao JOIN tot hon Nested Loop:
      - Nested Loop: O(n*m) — moi dong table A quet toan bo table B
      - Hash Join: O(n + m) — hash bang nho, probe nhanh

    Han che an toan:
      - Chi ap dung IN subquery don gian (1 bang, khong JOIN trong subquery)
      - Khong ap dung correlated subquery (tham chieu cot ngoai)
      - Khong ap dung NOT IN (vi NULL handling phuc tap)
    """

    def _find_in_subqueries(self, select: exp.Select) -> list:
        """
        Tim tat ca cac IN subquery o muc ngoai cung cua SELECT.
        Tra ve: list of (outer_col, inner_select, subquery_node, is_not_in)
        """
        results = []
        where = select.args.get("where")
        if not where:
            return results

        def extract(cond):
            """Dua tren expression tree, trich xuat In/Not nodes."""
            # Neu la Not: xu ly In ben trong
            if isinstance(cond, exp.Not) and isinstance(cond.this, exp.In):
                in_expr = cond.this
                outer_col = in_expr.this  # Column
                inner_subq = in_expr.args.get("query")  # Subquery
                if isinstance(outer_col, exp.Column) and isinstance(inner_subq, exp.Subquery):
                    inner_sel = inner_subq.this
                    if isinstance(inner_sel, exp.Select):
                        if self._can_unnest(select, inner_sel, inner_subq):
                            results.append((outer_col, inner_sel, inner_subq, True))
            # Neu la In truc tiep
            elif isinstance(cond, exp.In):
                outer_col = cond.this
                inner_subq = cond.args.get("query")
                if isinstance(outer_col, exp.Column) and isinstance(inner_subq, exp.Subquery):
                    inner_sel = inner_subq.this
                    if isinstance(inner_sel, exp.Select):
                        if self._can_unnest(select, inner_sel, inner_subq):
                            results.append((outer_col, inner_sel, inner_subq, False))
            # Neu la And/Or: de quy
            elif isinstance(cond, (exp.And, exp.Or)):
                if cond.this:
                    extract(cond.this)
                if isinstance(cond, exp.And) and hasattr(cond, 'expression') and cond.expression:
                    extract(cond.expression)

        extract(where.this)
        return results

    def _can_unnest(self, outer_select: exp.Select, inner_select: exp.Subquery, subq_node: exp.Subquery) -> bool:
        """
        Kiem tra xem co the unnest subquery khong.
        Quy tac:
          1. Subquery khong co correlated (khong tham chieu cot ngoai)
          2. Inner SELECT chi mot bang (khong co JOIN)
          3. Inner SELECT khong co aggregate phuc tap (HAVING)
        """
        # Lay ten bang o ngoai
        outer_from = outer_select.args.get("from_")
        outer_table_names = set()
        if outer_from:
            t = outer_from.this
            if isinstance(t, exp.Table):
                outer_table_names.add(t.alias or t.name)
                outer_table_names.add(t.name)
            elif isinstance(t, exp.Subquery):
                if t.alias:
                    outer_table_names.add(t.alias)

        # Kiem tra correlated: subquery co tham chieu cot o bang ngoai
        for col in subq_node.find_all(exp.Column):
            if col.table in outer_table_names:
                return False

        # Chi unnest neu inner la don gian (1 bang, khong JOIN)
        inner_tables = {tbl.name for tbl in inner_select.find_all(exp.Table)}
        if len(inner_tables) != 1:
            return False

        # Khong co HAVING
        if inner_select.args.get("having"):
            return False

        return True

    @property
    def description(self) -> str:
        return (
            "Chuyen IN subquery thanh JOIN. "
            "Chi ap dung subquery don (khong correlated), 1 bang trong subquery. "
            "Tang toc do dang ke bang cach cho phep Hash Join thay Nested Loop."
        )

    def apply(self, sql: str) -> str:
        """
        Thu tu thuc hien:
          1. Parse SQL thanh AST
          2. Tim cac IN subquery o muc ngoai
          3. Kiem tra tinh an toan
          4. Neu an toan: chuyen thanh JOIN
          5. Tra ve SQL da rewrite
        """
        try:
            ast = parse_sql(sql)
        except Exception:
            return sql

        ast_copy = clone_ast(ast)
        changed = False

        for select in ast_copy.find_all(exp.Select):
            # Chi xu ly SELECT ngoai cung (co WHERE)
            if not select.args.get("where"):
                continue

            subqs = self._find_in_subqueries(select)
            if not subqs:
                continue

            for outer_col, inner_select, subq_node, is_not_in in subqs:
                # Lay bang ngoai
                outer_from = select.args.get("from_")
                if not outer_from or not isinstance(outer_from.this, exp.Table):
                    continue

                outer_table = outer_from.this
                outer_alias = outer_table.alias or outer_table.name

                # Lay bang trong subquery
                inner_table_node = list(inner_select.find_all(exp.Table))[0]
                inner_alias = inner_table_node.alias or inner_table_node.name
                inner_col_name = None
                for col in inner_select.expressions:
                    if isinstance(col, exp.Column):
                        inner_col_name = col.name
                        break

                if not inner_col_name:
                    continue

                # Lay cot o subquery cho JOIN key
                subq_expr = inner_select.expressions[0] if inner_select.expressions else None
                if not isinstance(subq_expr, exp.Column):
                    continue

                # Tao JOIN condition
                if is_not_in:
                    join_cond = exp.Or(
                        this=exp.NE(
                            this=exp.Column(table=exp.to_identifier(outer_alias), this=exp.to_identifier(outer_col.name)),
                            expression=exp.Column(table=exp.to_identifier(inner_alias), this=exp.to_identifier(subq_expr.name))
                        ),
                        expression=exp.Is(
                            this=exp.Column(table=exp.to_identifier(inner_alias), this=exp.to_identifier(subq_expr.name)),
                            expression=exp.Null()
                        )
                    )
                else:
                    join_cond = exp.EQ(
                        this=exp.Column(table=exp.to_identifier(outer_alias), this=exp.to_identifier(outer_col.name)),
                        expression=exp.Column(table=exp.to_identifier(inner_alias), this=exp.to_identifier(subq_expr.name))
                    )

                # Tach WHERE cua subquery ra
                inner_where = inner_select.args.get("where")
                if inner_where:
                    inner_select.set("where", None)

                # Xay dung cau truc JOIN
                # Tu: FROM outer_table
                # -> FROM outer_table [INNER/LEFT] JOIN inner_table ON cond [WHERE inner_where]
                join_node = exp.Join(
                    this=inner_table_node.copy(),
                    side=exp.Var(this=exp.to_identifier("LEFT" if is_not_in else "INNER")),
                    kind=exp.Var(this=exp.to_identifier("JOIN")),
                    on=join_cond
                )
                join_node.this  # ensure proper setup

                new_from = exp.From(this=outer_table.copy())
                new_from.set("expressions", [join_node])

                # Cap nhat FROM
                select.set("from_", new_from)

                # Ghep WHERE: loai bo IN condition, giu lai cac dieu kien khac
                self._remove_in_condition(select, outer_col, is_not_in)

                # Them WHERE cua inner (neu co) vao WHERE ngoai
                if inner_where:
                    outer_where = select.args.get("where")
                    if outer_where:
                        merged = exp.and_(outer_where.this, inner_where.this)
                        select.set("where", exp.Where(this=merged))
                    else:
                        select.set("where", exp.Where(this=inner_where.this))

                changed = True
                break  # Chi xu ly 1 subquery moi lan

        if changed:
            try:
                return ast_to_sql(ast_copy)
            except Exception:
                return sql
        return sql

    def _remove_in_condition(self, select: exp.Select, outer_col: exp.Column, is_not_in: bool):
        """Loai bo IN condition khoi WHERE, giu lai cac dieu kien con lai."""
        where = select.args.get("where")
        if not where:
            return

        cond = where.this
        new_cond = self._remove_in_recursive(cond, outer_col, is_not_in)

        if new_cond is None:
            # Khong con dieu kien nao, xoa WHERE
            select.set("where", None)
        elif new_cond is not cond:
            select.set("where", exp.Where(this=new_cond))

    def _remove_in_recursive(self, node, outer_col: exp.Column, is_not_in: bool):
        """De quy loai bo IN condition khoi expression tree."""
        if isinstance(node, exp.Not):
            inner = node.this
            if isinstance(inner, exp.In) and isinstance(inner.this, exp.Column):
                if inner.this.name == outer_col.name:
                    return None  # Loai bo
            new_inner = self._remove_in_recursive(inner, outer_col, is_not_in)
            if new_inner is None:
                return None
            if new_inner is not inner:
                return exp.Not(this=new_inner)
            return node

        if isinstance(node, exp.In):
            if isinstance(node.this, exp.Column) and node.this.name == outer_col.name:
                return None
            return node

        if isinstance(node, exp.And):
            left = self._remove_in_recursive(node.this, outer_col, is_not_in)
            right = node.expression if hasattr(node, 'expression') else None
            if right:
                right = self._remove_in_recursive(right, outer_col, is_not_in)
            if left is None and right is None:
                return None
            if left is None:
                return right
            if right is None:
                return left
            if left is not node.this or (right and right is not node.expression):
                return exp.And(this=left, expression=right)
            return node

        if isinstance(node, exp.Or):
            left = self._remove_in_recursive(node.this, outer_col, is_not_in)
            right = node.expression if hasattr(node, 'expression') else None
            if right:
                right = self._remove_in_recursive(right, outer_col, is_not_in)
            if left is None or right is None:
                return left or right
            if left is not node.this or (right and right is not node.expression):
                return exp.Or(this=left, expression=right)
            return node

        return node


if __name__ == "__main__":
    rule = SubqueryUnnestingRule()

    tests = [
        ("IN subquery safe",
         "SELECT c_name FROM customer WHERE c_custkey IN (SELECT o_custkey FROM orders WHERE o_totalprice > 100000);"),
        ("IN sub 2",
         "SELECT p_name FROM part WHERE p_partkey IN (SELECT l_partkey FROM lineitem WHERE l_quantity > 40);"),
        ("IN sub 3",
         "SELECT s_name FROM supplier WHERE s_suppkey IN (SELECT ps_suppkey FROM partsupp WHERE ps_availqty < 10);"),
        ("No subquery",
         "SELECT * FROM orders WHERE o_totalprice > 50000;"),
        ("Multiple conditions — removes IN only",
         "SELECT c_name FROM customer WHERE c_custkey > 5 AND c_custkey IN (SELECT o_custkey FROM orders WHERE o_totalprice > 100000);"),
    ]

    for name, sql in tests:
        out = rule.apply(sql)
        changed = "CHANGED" if out.strip() != sql.strip() else "unchanged"
        print(f"[{name}] {changed}")
        print(f"  IN : {sql}")
        print(f"  OUT: {out}")
        print()
