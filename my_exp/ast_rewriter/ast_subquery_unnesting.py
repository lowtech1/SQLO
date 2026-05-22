from sqlglot import expressions as exp
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from my_exp.ast_rewriter.ast_utils import parse_sql, clone_ast, ast_to_sql


class ASTSubqueryUnnesting:
    """
    AST-based Subquery Unnesting Optimization.

    Muc dich: Chuyen IN/EXISTS subquery thanh JOIN de cho phep
    PostgreSQL optimizer su dung Hash Join thay vi Nested Loop.

    Cong thuc:
      Time: O(n x m) Nested Loop -> O(n + m) Hash Join
      Space: O(1) -> O(m) hash table

    Vi du:
        Input:  SELECT c_name FROM customer WHERE c_custkey IN (SELECT o_custkey FROM orders WHERE o_totalprice > 100000);
        Output: SELECT customer.c_name FROM customer INNER JOIN (SELECT DISTINCT o_custkey FROM orders WHERE o_totalprice > 100000) AS _sq_0 ON customer.c_custkey = _sq_0.o_custkey

    Han che an toan:
      - Chi ap dung IN subquery don gian (1 bang, khong correlated)
      - Khong ap dung NOT IN (vi NULL handling phuc tap)
    """

    def _find_in_subqueries(self, select: exp.Select) -> list:
        """Tim tat ca IN subqueries o muc ngoai cung. Tra ve list of (outer_col, inner_select, in_node)."""
        results = []
        where = select.args.get("where")
        if not where:
            return results

        def walk(node):
            if isinstance(node, exp.In):
                outer_col = node.this
                inner_subq = node.args.get("query")
                if isinstance(outer_col, exp.Column) and isinstance(inner_subq, exp.Subquery):
                    inner_sel = inner_subq.this
                    if isinstance(inner_sel, exp.Select) and self._can_unnest(select, inner_subq):
                        results.append((outer_col, inner_sel, inner_subq, False))
            elif isinstance(node, exp.Not):
                walk(node.this)
            elif isinstance(node, (exp.And, exp.Or)):
                walk(node.this)
                walk(node.expression)

        walk(where.this)
        return results

    def _can_unnest(self, outer_select: exp.Select, inner_subq: exp.Subquery) -> bool:
        """Kiem tra co the unnest subquery khong. Chi correlated subquery thi khong."""
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

        for col in inner_subq.find_all(exp.Column):
            if col.table in outer_table_names:
                return False

        inner_tables = {tbl.name for tbl in inner_subq.find_all(exp.Table)}
        if len(inner_tables) != 1:
            return False

        inner_sel = inner_subq.this
        if inner_sel.args.get("having"):
            return False

        return True

    def _remove_in_condition(self, select: exp.Select, outer_col: exp.Column):
        """Loai bo IN condition khoi WHERE clause."""
        where = select.args.get("where")
        if not where:
            return

        cond = where.this
        new_cond = self._remove_in_recursive(cond, outer_col)
        if new_cond is None:
            select.set("where", None)
        elif new_cond is not cond:
            select.set("where", exp.Where(this=new_cond))

    def _remove_in_recursive(self, node, outer_col: exp.Column):
        """De quy loai bo IN condition khoi expression tree."""
        if isinstance(node, exp.Not):
            inner = node.this
            if isinstance(inner, exp.In) and isinstance(inner.this, exp.Column):
                if inner.this.name == outer_col.name:
                    return None
            new_inner = self._remove_in_recursive(inner, outer_col)
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
            left = self._remove_in_recursive(node.this, outer_col)
            right = node.expression if hasattr(node, 'expression') and node.expression else None
            if right:
                right = self._remove_in_recursive(right, outer_col)
            if left is None and right is None:
                return None
            if left is None:
                return right
            if right is None:
                return left
            if left is not node.this or (right is not None and right is not (node.expression if hasattr(node, 'expression') else None)):
                return exp.And(this=left, expression=right)
            return node

        if isinstance(node, exp.Or):
            left = self._remove_in_recursive(node.this, outer_col)
            right = node.expression if hasattr(node, 'expression') and node.expression else None
            if right:
                right = self._remove_in_recursive(right, outer_col)
            if left is None or right is None:
                return left or right
            if left is not node.this or (right is not None and right is not (node.expression if hasattr(node, 'expression') else None)):
                return exp.Or(this=left, expression=right)
            return node

        return node

    def apply(self, sql: str) -> str:
        try:
            ast = parse_sql(sql)
        except Exception:
            return sql

        ast_copy = clone_ast(ast)
        changed = False

        for select in ast_copy.find_all(exp.Select):
            if not select.args.get("where"):
                continue

            subqs = self._find_in_subqueries(select)
            if not subqs:
                continue

            for outer_col, inner_sel, inner_subq, is_not_in in subqs:
                outer_from = select.args.get("from_")
                if not outer_from or not isinstance(outer_from.this, exp.Table):
                    continue

                outer_table = outer_from.this
                outer_alias = outer_table.alias or outer_table.name

                inner_col = inner_sel.expressions[0] if inner_sel.expressions else None
                if not isinstance(inner_col, exp.Column):
                    continue

                inner_col_name = inner_col.name

                # Tao CTE cho inner query (giữ nguyên WHERE bên trong, them DISTINCT de tranh duplicate)
                inner_sel.set("distinct", exp.Distinct())
                cte_alias = "_sq_0"
                cte_subquery = exp.Subquery(
                    this=inner_sel,
                    alias=exp.TableAlias(this=exp.to_identifier(cte_alias))
                )

                # Tao JOIN condition
                join_cond = exp.EQ(
                    this=exp.Column(table=exp.to_identifier(outer_alias), this=exp.to_identifier(outer_col.name)),
                    expression=exp.Column(table=exp.to_identifier(cte_alias), this=exp.to_identifier(inner_col_name))
                )

                # Tao JOIN node
                join_node = exp.Join(
                    this=cte_subquery,
                    on=join_cond
                )

                existing_joins = select.args.get("joins", [])
                existing_joins.append(join_node)
                select.set("joins", existing_joins)

                # Loai bo IN khoi WHERE
                self._remove_in_condition(select, outer_col)

                changed = True
                break

        if changed:
            try:
                return ast_to_sql(ast_copy)
            except Exception:
                return sql
        return sql


if __name__ == "__main__":
    rule = ASTSubqueryUnnesting()

    tests = [
        ("q7: IN subquery",
         "SELECT c_name FROM customer WHERE c_custkey IN (SELECT o_custkey FROM orders WHERE o_totalprice > 100000);"),
        ("q8: IN subquery 2",
         "SELECT p_name FROM part WHERE p_partkey IN (SELECT l_partkey FROM lineitem WHERE l_quantity > 40);"),
        ("q9: IN subquery 3",
         "SELECT s_name FROM supplier WHERE s_suppkey IN (SELECT ps_suppkey FROM partsupp WHERE ps_availqty < 10);"),
        ("No subquery",
         "SELECT * FROM orders WHERE o_totalprice > 50000;"),
        ("Multiple conditions",
         "SELECT c_name FROM customer WHERE c_custkey > 5 AND c_custkey IN (SELECT o_custkey FROM orders WHERE o_totalprice > 100000);"),
    ]

    for name, sql in tests:
        out = rule.apply(sql)
        changed = "CHANGED" if out.strip() != sql.strip() else "unchanged"
        print(f"\n[{name}] {changed}")
        print(f"  IN : {sql}")
        print(f"  OUT: {out}")
