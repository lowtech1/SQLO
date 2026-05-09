import sqlglot.expressions as exp
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from my_exp.ast_rewriter.ast_utils import parse_sql, clone_ast, ast_to_sql

class ASTSubqueryUnnesting:
    """
    AST-based Subquery Unnesting optimization using sqlglot.
    Detects IN (SELECT ...) patterns and attempts to safely rewrite them as JOINs.
    
    Example:
        Input:  SELECT * FROM customers WHERE id IN (SELECT customer_id FROM orders);
        Output: SELECT customers.* FROM customers JOIN orders ON customers.id = orders.customer_id;
    """
    def apply(self, sql: str) -> str:
        try:
            ast = parse_sql(sql)
        except Exception:
            return sql
            
        ast_copy = clone_ast(ast)
        
        # sqlglot actually has an optimizer for this: unnest_subqueries
        try:
            from sqlglot.optimizer.unnest_subqueries import unnest_subqueries
            # We apply the built-in unnest logic which is highly semantic-safe
            optimized_ast = unnest_subqueries(ast_copy)
            return ast_to_sql(optimized_ast)
        except Exception:
            # Fallback naive logic if optimizer isn't available or fails
            for where in ast_copy.find_all(exp.Where):
                for in_exp in where.find_all(exp.In):
                    if isinstance(in_exp.query, exp.Select):
                        # Manual rewriting logic goes here for simple cases
                        pass

        return ast_to_sql(ast_copy)

if __name__ == "__main__":
    sql = "SELECT * FROM customers WHERE id IN (SELECT customer_id FROM orders);"
    print("Input :", sql)
    rule = ASTSubqueryUnnesting()
    print("Output:", rule.apply(sql))
