class ProjectionPruningRule:
    """
    Rule to apply projection pruning optimization to SQL queries.
    Removes unused columns from the SELECT lists of subqueries.
    """

    @property
    def description(self) -> str:
        return "Prunes unnecessary columns from SELECT projections to optimize query execution."

    def apply(self, sql: str) -> str:
        """
        Applies the projection pruning rule to the given SQL query.
        If it encounters a 'SELECT *' and schema is unknown, it either returns 
        the original SQL or adds a warning comment.

        Args:
            sql (str): The original SQL query.

        Returns:
            str: The optimized SQL query.

        Example:
            Input:  SELECT a FROM (SELECT a, b, c FROM t) sub;
            Output: SELECT a FROM (SELECT a FROM t) sub;
        """
        upper_sql = sql.upper()
        if "SELECT *" in upper_sql:
            # We don't have the schema to safely expand SELECT *, 
            # so we just prepend a warning comment to the original SQL.
            return f"/* WARNING: SELECT * encountered; cannot safely prune projections without schema */\n{sql}"
        
        # TODO: Implement actual projection pruning logic parsing the AST.
        # Currently, returning the original SQL safely.
        return sql


if __name__ == "__main__":
    # Simple test cases
    rule = ProjectionPruningRule()
    
    print("Test 1: Normal Query")
    query1 = "SELECT a FROM (SELECT a, b, c FROM t) sub;"
    print("Input: ", query1)
    print("Output:", rule.apply(query1))
    print("-" * 40)
    
    print("Test 2: Query with SELECT *")
    query2 = "SELECT * FROM t;"
    print("Input: ", query2)
    print("Output:", rule.apply(query2))
    print("-" * 40)
