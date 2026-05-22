import sqlglot
from sqlglot import expressions as exp
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from my_exp.ast_rewriter.ast_utils import parse_sql, clone_ast, ast_to_sql

class ASTAggregationPushdown:
    """
    AST-based Aggregation Pushdown optimization using sqlglot.
    
    Detects GROUP BY operations running on top of a subquery or JOIN and pushes 
    the aggregation down into the subquery. This drastically reduces the number 
    of intermediate rows passed to the outer query.
    """
    
    def __init__(self, debug=False):
        self.debug = debug

    def can_push_aggregation(self, select_node: exp.Select, inner_select: exp.Select) -> bool:
        """
        Semantic safety checks to ensure pushing aggregation won't break the query.
        """
        # 1. Reject if outer query has an unsafe HAVING clause
        if select_node.args.get("having"):
            return False
            
        # 2. Reject if outer query has window functions or DISTINCT in aggregations
        for expr in select_node.expressions:
            if expr.find(exp.Window):
                return False
            agg = expr.find(exp.AggFunc)
            if agg and agg.args.get("distinct"):
                return False
                
        # 3. Reject if the inner subquery already has GROUP BY, LIMIT, or OFFSET
        if inner_select.args.get("group") or inner_select.args.get("limit") or inner_select.args.get("offset"):
            return False
            
        return True

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
                        sub_alias = table_expr.alias
                        
                        new_inner_exprs = []
                        new_outer_exprs = []
                        
                        # Process outer select expressions to move them down
                        for expr in select.expressions:
                            agg = expr.find(exp.AggFunc)
                            if agg:
                                if isinstance(expr, exp.Alias):
                                    new_inner_exprs.append(expr)
                                    new_outer_exprs.append(exp.column(expr.alias, table=sub_alias))
                                else:
                                    # Fallback alias for unaliased aggregation
                                    agg_alias = "pushed_agg"
                                    new_inner_exprs.append(exp.alias_(expr, agg_alias))
                                    new_outer_exprs.append(exp.column(agg_alias, table=sub_alias))
                            else:
                                # Non-aggregate columns (group by keys)
                                new_inner_exprs.append(expr)
                                if isinstance(expr, exp.Alias):
                                    new_outer_exprs.append(exp.column(expr.alias, table=sub_alias))
                                else:
                                    # Handle plain columns
                                    col_name = expr.name if isinstance(expr, exp.Column) else expr.sql(dialect="postgres")
                                    new_outer_exprs.append(exp.column(col_name, table=sub_alias))
                                    
                        # Apply AST transformation
                        inner_select.set("expressions", new_inner_exprs)
                        inner_select.set("group", group_node)
                        
                        select.set("expressions", new_outer_exprs)
                        select.set("group", None) # Remove group from outer
                        
                        pushed = True
                        
        rewritten_sql = ast_to_sql(ast_copy)
        
        if self.debug:
            print("-" * 50)
            print("Original SQL :", sql)
            print("Rewritten SQL:", rewritten_sql)
            if pushed:
                print("Pushed Agg   : Yes (Aggregation pushed to subquery)")
            else:
                print("Pushed Agg   : None (Unsafe or missing pattern)")
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
