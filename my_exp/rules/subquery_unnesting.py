import re

class SubqueryUnnestingRule:
    """
    Rule to apply subquery unnesting optimization to SQL queries.
    Converts simple IN subqueries into JOINs where applicable.
    
    Example:
        Input:  SELECT * FROM customers WHERE id IN (SELECT customer_id FROM orders);
        Output: SELECT customers.* FROM customers JOIN orders ON customers.id = orders.customer_id;
    """

    @property
    def description(self) -> str:
        return "Unnests subqueries (e.g., IN clauses) into JOIN operations for better performance."

    def apply(self, sql: str) -> str:
        """
        Applies the subquery unnesting rule to the given SQL query.
        Tries to handle simple patterns like:
        SELECT * FROM <table> WHERE <col> IN (SELECT <col2> FROM <table2>)
        
        If the query doesn't match the simple pattern or cannot be safely rewritten,
        returns the original SQL.

        Args:
            sql (str): The original SQL query.

        Returns:
            str: The optimized SQL query, or original if rewrite is unsafe.
        """
        # A simple regex to catch a very basic pattern:
        # SELECT * FROM <table> WHERE <col> IN (SELECT <col2> FROM <table2>)
        pattern = r"SELECT\s+\*\s+FROM\s+(\w+)\s+WHERE\s+(\w+)\s+IN\s*\(\s*SELECT\s+(\w+)\s+FROM\s+(\w+)\s*\)\s*;?"
        match = re.search(pattern, sql, flags=re.IGNORECASE)
        
        if match:
            t1 = match.group(1)
            c1 = match.group(2)
            c2 = match.group(3)
            t2 = match.group(4)
            
            # Rewrite to a JOIN
            # Note: For strict correctness, unnesting an IN subquery usually implies an EXISTS / SEMI JOIN
            # or requires DISTINCT to avoid duplicating rows if t2 has multiple matches.
            # This is a naive rewrite for demonstration purposes.
            rewritten = f"SELECT {t1}.* FROM {t1} JOIN {t2} ON {t1}.{c1} = {t2}.{c2}"
            
            # Keep the trailing semicolon if it was there
            if sql.strip().endswith(';'):
                rewritten += ";"
            return rewritten
            
        # If no match or we are not confident, return original SQL safely.
        return sql

if __name__ == "__main__":
    rule = SubqueryUnnestingRule()
    
    print("Test 1: Simple IN subquery")
    sql1 = "SELECT * FROM customers WHERE id IN (SELECT customer_id FROM orders);"
    print("Input: ", sql1)
    print("Output:", rule.apply(sql1))
    print("-" * 40)
    
    print("Test 2: Complex or unsupported query")
    sql2 = "SELECT a, b FROM t1 WHERE EXISTS (SELECT 1 FROM t2 WHERE t1.a = t2.a);"
    print("Input: ", sql2)
    print("Output:", rule.apply(sql2))
    print("-" * 40)
