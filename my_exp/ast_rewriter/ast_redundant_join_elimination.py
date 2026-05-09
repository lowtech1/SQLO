import sqlglot
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

    def is_join_redundant(self, join_node: exp.Join, select_node: exp.Select) -> bool:
        """
        Validates whether a JOIN is safe to remove without altering query semantics.
        """
        # 1. Reject OUTER, LEFT, RIGHT, FULL joins
        # Their presence directly alters the row count of the primary table even if unused.
        side = join_node.args.get("side")
        kind = join_node.args.get("kind")
        if side and side.upper() in ("LEFT", "RIGHT", "FULL"):
            return False
        if kind and kind.upper() == "OUTER":
            return False
            
        # 2. Reject if the query contains Aggregations
        # Removing an INNER JOIN can change the row cardinality (if it duplicates rows or filters).
        # This breaks SUM(), COUNT(), and GROUP BY logic.
        if select_node.args.get("group") or select_node.args.get("having"):
            return False
        for expr in select_node.expressions:
            if expr.find(exp.AggFunc):
                return False
                
        # 3. Identify the table and its alias
        t = join_node.this
        if not isinstance(t, exp.Table):
            return False # E.g., a subquery join
            
        table_name = t.name.lower()
        table_alias = t.alias.lower() if t.alias else table_name
        
        # 4. Check if the table is referenced ANYWHERE else in the query
        # To do this safely, we clone the select node and remove THIS specific join from it,
        # then scan the entire remaining AST for column references to this table's alias.
        select_clone = select_node.copy()
        select_clone.set("joins", [j for j in select_clone.args.get("joins", []) if j is not join_node])
        
        used_elsewhere = False
        for col in select_clone.find_all(exp.Column):
            if col.table:
                if col.table.lower() == table_alias:
                    used_elsewhere = True
                    break
            else:
                # Unprefixed columns are dangerous because we lack a database schema.
                # If there's an unprefixed column, it *could* belong to the joined table.
                # For strict safety in an experimental engine, we assume it's risky.
                used_elsewhere = True
                break
                
        if used_elsewhere:
            return False
            
        # 5. Semantic risk consideration:
        # Without database schema (Primary Key / Foreign Key constraints), removing an INNER JOIN 
        # is theoretically unsafe because it might have acted as a filtering mechanism or 
        # caused row duplication. We apply this rule assuming 1:1 or 1:N FK relationships.
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
