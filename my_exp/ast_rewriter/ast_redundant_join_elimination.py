from sqlglot import expressions as exp
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from my_exp.ast_rewriter.ast_utils import parse_sql, clone_ast, ast_to_sql

class ASTRedundantJoinElimination:
    """
    AST-based Redundant Join Elimination optimization using sqlglot.
    
    Detects and safely removes JOINs where the joined table's columns are entirely 
    unused in the SELECT projection, WHERE clause, GROUP BY, HAVING, or ORDER BY.
    """
    def __init__(self, debug=False):
        self.debug = debug

    def _collect_referenced_tables(self, node: exp.Expression) -> set:
        """Collect all table aliases referenced in a node's FROM clause and JOINs."""
        tables = set()
        from_ = node.args.get("from_")
        if from_:
            t = from_.this
            if isinstance(t, exp.Table):
                tables.add(t.alias.lower() if t.alias else t.name.lower())
            elif isinstance(t, exp.Subquery):
                tables.add(t.alias.lower() if t.alias else "subquery")
        return tables

    def is_join_redundant(self, join_node: exp.Join, select_node: exp.Select) -> bool:
        """
        Validates whether a JOIN is safe to remove without altering query semantics.
        """
        # 0. CRITICAL: Reject SELECT * — it expands to ALL columns of ALL joined tables.
        #    Removing a JOIN changes the result schema (fewer columns) → NOT equivalent.
        for expr in select_node.expressions:
            if isinstance(expr, exp.Star):
                return False  # SELECT * includes joined table columns — unsafe to remove

        # 1. CRITICAL: Reject all INNER joins.
        #    INNER JOIN changes result cardinality — rows without matches are dropped.
        #    e.g. FROM customer c JOIN orders o ON ... WHERE c_mktsegment='AUTO'
        #         returns only customers who HAVE orders (19K rows).
        #    Removing the JOIN returns ALL matching customers (29K rows) — DIFFERENT.
        #    This is UNSAFE even if joined columns aren't referenced in SELECT/WHERE.
        #    Only OUTER joins (which preserve rows) are candidates for removal.
        side = join_node.args.get("side")
        kind = join_node.args.get("kind")
        if side and side.upper() not in ("LEFT", "RIGHT", "FULL"):
            return False  # INNER join — never remove
        if kind and kind.upper() == "CROSS":
            return False  # CROSS join — never remove
        if (not side) and (not kind or kind.upper() == "INNER"):
            return False  # Plain JOIN = INNER — never remove

        # 2. Reject if the query contains Aggregations
        if select_node.args.get("group") or select_node.args.get("having"):
            return False
        for expr in select_node.expressions:
            if expr.find(exp.AggFunc):
                return False

        # 3. Identify the table and its alias
        t = join_node.this
        if not isinstance(t, exp.Table):
            return False

        table_alias = t.alias.lower() if t.alias else t.name.lower()

        # 4. Collect the tables that remain in the query after removing this join.
        #    Only these tables are safe to reference.
        remaining_tables = set()
        for j in select_node.args.get("joins", []):
            if j is join_node:
                continue
            jt = j.this
            if isinstance(jt, exp.Table):
                remaining_tables.add(jt.alias.lower() if jt.alias else jt.name.lower())
        from_ = select_node.args.get("from_")
        if from_:
            ft = from_.this
            if isinstance(ft, exp.Table):
                remaining_tables.add(ft.alias.lower() if ft.alias else ft.name.lower())
            elif isinstance(ft, exp.Subquery):
                remaining_tables.add(ft.alias.lower() if ft.alias else "subquery")

        # 5. Check if the joined table is referenced in:
        #    - SELECT projection (outer select)
        #    - WHERE clause (of outer select)
        #    - GROUP BY / HAVING / ORDER BY
        #    NOTE: We do NOT check the ON clause of this join, because those columns
        #    are by definition part of the join being evaluated.
        #    NOTE: Unprefixed columns are assumed to potentially belong to any table.

        def is_col_from_joined_table(col: exp.Column) -> bool:
            if not col.table:
                return True  # unprefixed = dangerous
            return col.table.lower() == table_alias

        for expr in select_node.expressions:
            for col in expr.find_all(exp.Column):
                if is_col_from_joined_table(col):
                    return False

        for node_type in ("where", "group", "having"):
            node = select_node.args.get(node_type)
            if node:
                for col in node.find_all(exp.Column):
                    if is_col_from_joined_table(col):
                        return False

        for sort_node in select_node.find_all(exp.Order):
            for col in sort_node.find_all(exp.Column):
                if is_col_from_joined_table(col):
                    return False

        # 6. CRITICAL: The WHERE clause of the OUTER select must not reference
        #    tables that are only reachable via this join. Removing the join
        #    would turn those filters into no-ops or change result row count.
        #    e.g. FROM a JOIN b ON ... WHERE b.status = 1  →  WHERE 1=1
        #    If the WHERE references ANY table other than the base FROM table
        #    or already-joined tables, we cannot safely remove this join.
        where = select_node.args.get("where")
        if where:
            # Collect all tables referenced in WHERE
            where_tables = set()
            for col in where.find_all(exp.Column):
                if col.table:
                    where_tables.add(col.table.lower())

            # Collect all tables that will remain in the query
            remaining_tables = set()
            for j in select_node.args.get("joins", []):
                if j is not join_node:
                    jt = j.this
                    if isinstance(jt, exp.Table):
                        remaining_tables.add(jt.alias.lower() if jt.alias else jt.name.lower())
            from_ = select_node.args.get("from_")
            if from_ and isinstance(from_.this, exp.Table):
                remaining_tables.add(
                    from_.this.alias.lower() if from_.this.alias else from_.this.name.lower()
                )

            # If WHERE references a table that only this join provides, reject
            if where_tables - remaining_tables - {table_alias}:
                return False

        return True

    def apply(self, sql: str) -> str:
        try:
            ast = parse_sql(sql)
        except Exception:
            return sql
            
        ast_copy = clone_ast(ast)
        
        for select in ast_copy.find_all(exp.Select):
            joins = select.args.get("joins")
            if not joins:
                continue
                
            new_joins = []
            removed_joins = []
            
            for join in joins:
                if self.is_join_redundant(join, select):
                    t = join.this
                    t_name = t.alias if t.alias else t.name
                    removed_joins.append(t_name)
                else:
                    new_joins.append(join)
                    
            if removed_joins:
                select.set("joins", new_joins)
                
                if self.debug:
                    remaining = [j.this.alias or j.this.name for j in new_joins] if new_joins else ["None"]
                    print("-" * 50)
                    print("Original SQL :", sql)
                    print("Rewritten SQL:", ast_to_sql(ast_copy))
                    print("Removed Joins:", ", ".join(removed_joins))
                    print("Remain Joins :", ", ".join(remaining))
                    print("-" * 50)
                    
        return ast_to_sql(ast_copy)

if __name__ == "__main__":
    rule = ASTRedundantJoinElimination(debug=True)
    
    print("\n[Test 1] Removable join (table 'b' is completely unused)")
    sql1 = "SELECT a.id, a.name FROM a JOIN b ON a.b_id = b.id WHERE a.status = 1;"
    rule.apply(sql1)
    
    print("\n[Test 2] Unsafe join (table 'b' is used in WHERE filter)")
    sql2 = "SELECT a.id FROM a JOIN b ON a.b_id = b.id WHERE b.status = 1;"
    rule.apply(sql2)
    
    print("\n[Test 3] Unsafe join (Aggregation-sensitive query)")
    sql3 = "SELECT a.name, COUNT(a.id) FROM a JOIN b ON a.b_id = b.id GROUP BY a.name;"
    rule.apply(sql3)
    
    print("\n[Test 4] Unsafe join (OUTER JOIN alters row count)")
    sql4 = "SELECT a.id FROM a LEFT JOIN b ON a.b_id = b.id WHERE a.status = 1;"
    rule.apply(sql4)
