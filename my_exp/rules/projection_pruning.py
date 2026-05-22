import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from my_exp.ast_rewriter.ast_utils import parse_sql, clone_ast, ast_to_sql
from sqlglot import expressions as exp


class ProjectionPruningRule:
    """
    Projection Pruning Optimization — STEM 2.

    Muc dich: Loai bo cac cot khong can thiet khoi SELECT trong subquery,
    giam luong du lieu doc tu database.

    Vi du:
        Input:  SELECT c_name, c_phone FROM (SELECT * FROM customer WHERE c_mktsegment='BUILDING') AS sub;
        Output: SELECT c_name, c_phone FROM (SELECT c_name, c_phone FROM customer WHERE c_mktsegment='BUILDING') AS sub;

    Vi du 2:
        Input:  SELECT a FROM (SELECT a, b, c FROM t) AS sub;
        Output: SELECT a FROM (SELECT a FROM t) AS sub;

    Han che:
      - Khong mo rong SELECT * cua table goc khi khong co schema (chi warning)
      - Chi xu ly khi outer query chi su dung mot phan cot cua inner subquery
    """

    def _extract_column_names(self, node: exp.Expression) -> set:
        """Trich xuat tat ca ten cot tu mot expression node."""
        names = set()
        if node is None:
            return names
        for col in node.find_all(exp.Column):
            names.add(col.name.lower())
        for alias in node.find_all(exp.Alias):
            names.add(alias.alias.lower())
        return names

    def _collect_needed_columns(self, outer_select: exp.Select) -> set:
        """Thu thap tat ca cac cot can thiet tu outer SELECT."""
        needed = set()
        for expr in outer_select.expressions:
            needed.update(self._extract_column_names(expr))
        for key in ("where", "group"):
            node = outer_select.args.get(key)
            if node:
                n = node.this if hasattr(node, 'this') else node
                needed.update(self._extract_column_names(n))
        return {c.lower() for c in needed if c}

    @property
    def description(self) -> str:
        return (
            "Loai bo cot thua khoi SELECT cua subquery. "
            "Chi ap dung khi outer query chi su dung mot phan cot cua subquery. "
            "Khong mo rong SELECT * khi khong co schema."
        )

    def apply(self, sql: str) -> str:
        """
        Thu tu thuc hien:
          1. Parse SQL thanh AST
          2. Tim cap (outer SELECT + inner subquery) o muc ngoai cung
          3. Neu inner la danh sach cot cu the: loai bo cot thua
          4. Neu inner la SELECT *: chi warning (khong co schema)
          5. Tra ve SQL da rewrite
        """
        try:
            ast = parse_sql(sql)
        except Exception:
            return sql

        ast_copy = clone_ast(ast)

        for outer_select in ast_copy.find_all(exp.Select):
            from_ = outer_select.args.get("from_")
            if not from_:
                continue

            table_expr = from_.this

            # Chi xu ly Subquery nho (inner SELECT)
            if not isinstance(table_expr, exp.Subquery):
                continue

            inner = table_expr.this
            if not isinstance(inner, exp.Select):
                continue

            # Bo qua neu inner co Star (can schema de mo rong)
            if any(isinstance(e, exp.Star) for e in inner.expressions):
                continue

            # Thu thap cot can thiet tu outer
            needed = self._collect_needed_columns(outer_select)
            if not needed:
                continue

            # Xay dung anh xa cot trong inner
            alias_map = {}  # alias_name -> expression
            col_map = {}    # col_name -> expression
            for e in inner.expressions:
                if isinstance(e, exp.Alias):
                    alias_map[e.alias.lower()] = e
                elif isinstance(e, exp.Column):
                    col_map[e.name.lower()] = e

            # Loai bo cot thua (chi giu cot can thiet + cot trong WHERE/GROUP cua inner)
            kept = []
            inner_where = inner.args.get("where")
            inner_group = inner.args.get("group")
            inner_needed = set()
            if inner_where:
                inner_needed.update(self._extract_column_names(inner_where.this))
            if inner_group:
                for g in (inner_group.expressions if hasattr(inner_group, 'expressions') else []):
                    inner_needed.update(self._extract_column_names(g))

            for e in inner.expressions:
                name = None
                if isinstance(e, exp.Alias):
                    name = e.alias.lower()
                elif isinstance(e, exp.Column):
                    name = e.name.lower()
                if name and (name in needed or name in inner_needed):
                    kept.append(e)

            # Chi rewrite neu thuc su loai bo cot
            if len(kept) < len(inner.expressions):
                inner.set("expressions", kept)
                return ast_to_sql(ast_copy)

        return sql


if __name__ == "__main__":
    rule = ProjectionPruningRule()

    tests = [
        ("Safe prune extra cols",
         "SELECT a FROM (SELECT a, b, c FROM t) AS sub;"),
        ("With alias",
         "SELECT sub.x, sub.y FROM (SELECT a AS x, b AS y, c FROM t) AS sub;"),
        ("No change needed",
         "SELECT a FROM (SELECT a, b FROM t) AS sub;"),
        ("With WHERE",
         "SELECT c_name FROM (SELECT c_custkey, c_name, c_phone FROM customer WHERE c_mktsegment='AUTOMOBILE') AS sub;"),
        ("Select * — skip (no schema)",
         "SELECT * FROM t;"),
        ("Three cols, need two",
         "SELECT a, b FROM (SELECT a, b, c, d FROM t) AS sub WHERE c > 5;"),
    ]

    for name, sql in tests:
        out = rule.apply(sql)
        changed = "CHANGED" if out.strip() != sql.strip() else "unchanged"
        print(f"[{name}] {changed}")
        print(f"  IN : {sql}")
        print(f"  OUT: {out}")
        print()
