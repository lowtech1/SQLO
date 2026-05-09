import sqlglot
from sqlglot import expressions as exp
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from my_exp.ast_rewriter.ast_utils import parse_sql, clone_ast, ast_to_sql

class ASTPredicatePushdown:
    """
    AST-based Predicate Pushdown optimization using sqlglot.
    Safely pushes WHERE conditions from outer queries into subqueries.
    """
    def __init__(self, debug=False):
        self.debug = debug

    def can_pushdown_condition(self, condition: exp.Expression, inner_select: exp.Select) -> bool:
        """
        Checks if a condition can be safely pushed down into the inner_select.
        Rules:
        1. inner_select cannot have DISTINCT.
        2. inner_select cannot have Aggregations (GROUP BY or Aggregate functions).
        3. All columns used in the condition must exist in the inner_select projection.
        """
        # 1. Check for DISTINCT
        if inner_select.args.get("distinct"):
            return False
            
        # 2. Check for GROUP BY
        if inner_select.args.get("group"):
            return False
            
        # 3. Check for Aggregate functions in the SELECT list
        for expr in inner_select.expressions:
            if expr.find(exp.AggFunc):
                return False

        # 4. Extract projected columns from inner_select
        has_star = False
        inner_cols = set()
        for proj in inner_select.expressions:
            if isinstance(proj, exp.Star):
                has_star = True
            elif isinstance(proj, exp.Alias):
                inner_cols.add(proj.alias.lower())
            elif isinstance(proj, exp.Column):
                inner_cols.add(proj.name.lower())
                
        # 5. Extract columns from the condition
        cond_cols = set()
        for col in condition.find_all(exp.Column):
            cond_cols.add(col.name.lower())
            
        # 6. Check if condition columns exist in inner projection
        if not has_star:
            for c in cond_cols:
                if c not in inner_cols:
                    return False
                    
        return True

    def apply(self, sql: str) -> str:
        try:
            ast = parse_sql(sql)
        except Exception:
            return sql
            
        ast_copy = clone_ast(ast)
        pushed_predicates = []
        
        # Look for Select nodes with WHERE clauses and Subqueries in FROM
        for select in ast_copy.find_all(exp.Select):
            where = select.args.get("where")
            if not where:
                continue
                
            from_exp = select.args.get("from")
            if not from_exp:
                continue
                
            # If the FROM clause is a subquery (e.g. FROM (SELECT ...))
            table_expr = from_exp.this
            if isinstance(table_expr, exp.Subquery):
                inner_select = table_expr.this
                if isinstance(inner_select, exp.Select):
                    condition = where.this
                    
                    # Check semantic safety
                    if self.can_pushdown_condition(condition, inner_select):
                        # Determine if inner query already has a WHERE clause
                        existing_where = inner_select.args.get("where")
                        
                        # Push the condition down into the subquery
                        if existing_where:
                            inner_select.where(exp.and_(existing_where.this, condition), copy=False)
                        else:
                            inner_select.where(condition, copy=False)
                            
                        # Remove the WHERE clause from the outer query
                        select.set("where", None)
                        pushed_predicates.append(condition.sql(dialect="postgres"))

        rewritten_sql = ast_to_sql(ast_copy)
        
        if self.debug:
            print("Original SQL :", sql)
            print("Rewritten SQL:", rewritten_sql)
            if pushed_predicates:
                print("Pushed Preds :", ", ".join(pushed_predicates))
            else:
                print("Pushed Preds : None (Unsafe or missing)")
            print("-" * 50)
            
        return rewritten_sql

if __name__ == "__main__":
    rule = ASTPredicatePushdown(debug=True)
    
    print("\n[Test 1] Simple pushdown (Safe)")
    sql1 = "SELECT a, b FROM (SELECT a, b FROM t) AS sub WHERE a > 10;"
    rule.apply(sql1)
    
    print("\n[Test 2] Aggregation case (Unsafe)")
    sql2 = "SELECT a, sum_b FROM (SELECT a, SUM(b) AS sum_b FROM t GROUP BY a) AS sub WHERE sum_b > 100;"
    rule.apply(sql2)
    
    print("\n[Test 3] DISTINCT case (Unsafe)")
    sql3 = "SELECT a FROM (SELECT DISTINCT a, b FROM t) AS sub WHERE a = 5;"
    rule.apply(sql3)
    
    print("\n[Test 4] Missing column case (Unsafe)")
    sql4 = "SELECT x FROM (SELECT b AS x FROM t) AS sub WHERE y = 1;"
    rule.apply(sql4)
