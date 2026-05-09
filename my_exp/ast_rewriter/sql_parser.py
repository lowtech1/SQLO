import os
import sys

# Ensure we can import my_exp from the project root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from my_exp.ast_rewriter.ast_utils import parse_sql

def debug_ast(sql: str):
    """
    Parses the given SQL and prints its AST representation for debugging.
    """
    ast = parse_sql(sql)
    print("SQL:")
    print(sql)
    print("-" * 40)
    print("AST Tree (repr):")
    print(repr(ast))

if __name__ == "__main__":
    sql = "SELECT * FROM t WHERE id IN (SELECT id FROM t2);"
    debug_ast(sql)
