import sqlglot
from sqlglot import expressions as exp

def parse_sql(sql: str, dialect: str = "postgres") -> exp.Expression:
    """
    Parses a SQL string into an AST using sqlglot.
    """
    return sqlglot.parse_one(sql, read=dialect)

def ast_to_sql(ast: exp.Expression, dialect: str = "postgres") -> str:
    """
    Converts an AST back into a SQL string.
    """
    return ast.sql(dialect=dialect)

def clone_ast(ast: exp.Expression) -> exp.Expression:
    """
    Deep copies an AST.
    """
    return ast.copy()

def extract_tables(ast: exp.Expression) -> list:
    """
    Extracts all table expressions from the AST.
    """
    return list(ast.find_all(exp.Table))

def extract_columns(ast: exp.Expression) -> list:
    """
    Extracts all column expressions from the AST.
    """
    return list(ast.find_all(exp.Column))

if __name__ == "__main__":
    sql = "SELECT a, b FROM t WHERE a > 1"
    ast = parse_sql(sql)
    print("SQL:", sql)
    print("Tables:", [t.name for t in extract_tables(ast)])
    print("Columns:", [c.name for c in extract_columns(ast)])
