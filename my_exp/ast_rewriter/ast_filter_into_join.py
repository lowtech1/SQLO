import sqlglot
from sqlglot import expressions as exp
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from my_exp.ast_rewriter.ast_utils import parse_sql, clone_ast, ast_to_sql

class ASTFilterIntoJoin:
    """
    AST-based Filter Into Join optimization using sqlglot.
    
    Explanation:
    - Filter Into Join: Moving a WHERE condition directly into the JOIN's ON clause.
    - Why it reduces intermediate rows: By applying the filter during the join operation 
      rather than after it, the database planner can discard non-matching rows earlier 
      in the execution pipeline. This reduces memory footprint and speeds up execution.
    - Semantic Risk with OUTER JOIN: Pushing a WHERE condition into a LEFT JOIN's ON clause 
      changes the semantics. A WHERE condition on a LEFT JOIN filters out NULLs (acting like an 
      INNER JOIN), whereas an ON condition preserves the left row and just yields NULL for the right side.
      Therefore, this rewrite is ONLY safe for INNER JOINs.
    """
    
    def __init__(self, debug=False):
        self.debug = debug

    def extract_where_conditions(self, node: exp.Expression) -> list:
        """
        Recursively splits an ANDed WHERE expression into a list of single conditions.
        """
        if isinstance(node, exp.And):
            return self.extract_where_conditions(node.left) + self.extract_where_conditions(node.right)
        # We clone the node to avoid mutating the original tree inadvertently
        return [node.copy()]

    def can_move_filter_to_join(self, condition: exp.Expression) -> bool:
        """
        Checks if a standalone condition is structurally safe to push into an ON clause.
        """
        # 1. No Subqueries
        if condition.find(exp.Subquery):
            return False
        # 2. No complex OR (pushing OR into JOIN ON can confuse some legacy planners or break safety)
        if condition.find(exp.Or):
            return False
        # 3. No Aggregations or Window functions
        if condition.find(exp.AggFunc) or condition.find(exp.Window):
            return False
            
        return True

    def move_filter_to_join(self, ast_copy: exp.Expression) -> tuple:
        """
        Main logic to move conditions from WHERE into JOIN ON.
        Returns a tuple of (moved_filters, skipped_filters) for debugging.
        """
        moved_filters = []
        skipped_filters = []
        
        for select in ast_copy.find_all(exp.Select):
            where = select.args.get("where")
            joins = select.args.get("joins")
            
            if not where or not joins:
                continue
                
            from_table = select.args.get("from_")
            if not from_table:
                continue
                
            # Parse available tables from the primary FROM clause
            available_tables = set()
            ft = from_table.this
            if isinstance(ft, exp.Table):
                available_tables.add(ft.alias.lower() if ft.alias else ft.name.lower())
                
            # Break down WHERE into individual conditions
            conditions = self.extract_where_conditions(where.this)
            remaining_conditions = conditions[:]
            
            for join in joins:
                t = join.this
                if not isinstance(t, exp.Table):
                    continue
                    
                jt_alias = t.alias.lower() if t.alias else t.name.lower()
                available_tables.add(jt_alias)
                
                # Check if this is a strict INNER JOIN
                side = join.args.get("side")
                kind = join.args.get("kind")
                
                is_inner = True
                if side and side.upper() in ("LEFT", "RIGHT", "FULL"):
                    is_inner = False
                if kind and kind.upper() in ("OUTER", "CROSS"):
                    is_inner = False
                    
                if not is_inner:
                    continue
                    
                # Try to push remaining conditions into this JOIN
                new_remaining = []
                for cond in remaining_conditions:
                    cols = list(cond.find_all(exp.Column))
                    
                    # We only push if it explicitly references the table we just joined
                    has_joined_table = False
                    safe_columns = True
                    
                    if not cols:
                        safe_columns = False # e.g. 1 = 1
                        
                    for c in cols:
                        if not c.table:
                            safe_columns = False # Unprefixed columns are dangerous
                            break
                        ct = c.table.lower()
                        if ct == jt_alias:
                            has_joined_table = True
                        if ct not in available_tables:
                            safe_columns = False
                            break
                            
                    # If it uses the joined table, only uses available tables, and passes structural checks:
                    if safe_columns and has_joined_table and self.can_move_filter_to_join(cond):
                        on_clause = join.args.get("on")
                        if on_clause:
                            join.set("on", exp.and_(on_clause, cond))
                        else:
                            join.set("on", cond)
                            
                        moved_filters.append(cond.sql(dialect="postgres"))
                    else:
                        new_remaining.append(cond)
                        
                remaining_conditions = new_remaining
                
            # Reconstruct WHERE clause with remaining conditions
            if len(remaining_conditions) < len(conditions):
                if remaining_conditions:
                    new_where = remaining_conditions[0]
                    for c in remaining_conditions[1:]:
                        new_where = exp.and_(new_where, c)
                    select.set("where", exp.Where(this=new_where))
                else:
                    select.set("where", None)
                    
            # Record what was skipped for this Select node
            for c in remaining_conditions:
                skipped_filters.append(c.sql(dialect="postgres"))
                
        return moved_filters, skipped_filters

    def apply(self, sql: str) -> str:
        try:
            ast = parse_sql(sql)
        except Exception:
            return sql
            
        ast_copy = clone_ast(ast)
        moved, skipped = self.move_filter_to_join(ast_copy)
        rewritten_sql = ast_to_sql(ast_copy)
        
        if self.debug:
            print("-" * 50)
            print("Original SQL :", sql)
            print("Rewritten SQL:", rewritten_sql)
            print("Moved Filters:", moved if moved else "None")
            print("Skipped Flt  :", skipped if skipped else "None")
            print("-" * 50)
            
        return rewritten_sql

if __name__ == "__main__":
    rule = ASTFilterIntoJoin(debug=True)
    
    print("\n[Test 1] Inner join safe case")
    sql1 = "SELECT * FROM a JOIN b ON a.id = b.a_id WHERE b.status = 'ACTIVE' AND a.type = 1;"
    rule.apply(sql1)
    
    print("\n[Test 2] Left join unsafe case")
    sql2 = "SELECT * FROM a LEFT JOIN b ON a.id = b.a_id WHERE b.status = 'ACTIVE';"
    rule.apply(sql2)
    
    print("\n[Test 3] Condition unrelated to join (Unprefixed column)")
    sql3 = "SELECT * FROM a JOIN b ON a.id = b.a_id WHERE status = 'ACTIVE';"
    rule.apply(sql3)
    
    print("\n[Test 4] Subquery condition unsafe case")
    sql4 = "SELECT * FROM a JOIN b ON a.id = b.a_id WHERE b.val IN (SELECT val FROM c);"
    rule.apply(sql4)
