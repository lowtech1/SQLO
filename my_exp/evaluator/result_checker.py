import os
import sys

# Ensure we can import my_exp from the project root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from my_exp.evaluator.postgres_runner import PostgresRunner

class ResultChecker:
    """
    Utility class to execute two SQL queries and compare their result sets for equivalence.
    """

    def __init__(self):
        self.runner = PostgresRunner()

    def check_equivalence(self, original_sql: str, rewritten_sql: str) -> dict:
        """
        Executes both the original and rewritten SQL queries and compares their results.

        Args:
            original_sql (str): The original query.
            rewritten_sql (str): The optimized/rewritten query.

        Returns:
            dict: Contains boolean is_equivalent, row counts, and a descriptive message.
        """
        result = {
            "is_equivalent": False,
            "original_row_count": None,
            "rewritten_row_count": None,
            "message": ""
        }

        if not original_sql or not rewritten_sql:
            result["message"] = "One or both SQL queries are empty."
            return result

        try:
            self.runner.connect()
        except Exception as e:
            result["message"] = f"Failed to connect to database: {str(e)}"
            return result

        try:
            # 1. Execute Original SQL
            try:
                orig_data = self.runner.run_query(original_sql)
            except Exception as e:
                result["message"] = f"Original SQL failed: {str(e)}"
                return result

            if orig_data is None:
                result["message"] = "Original SQL execution failed (possibly syntax error)."
                return result

            # 2. Execute Rewritten SQL
            try:
                rew_data = self.runner.run_query(rewritten_sql)
            except Exception as e:
                result["message"] = f"Rewritten SQL failed: {str(e)}"
                return result

            if rew_data is None:
                result["message"] = "Rewritten SQL execution failed (possibly syntax error)."
                return result

            # Record row counts
            result["original_row_count"] = len(orig_data)
            result["rewritten_row_count"] = len(rew_data)

            # 3. Compare results
            if len(orig_data) != len(rew_data):
                result["message"] = "Row counts do not match."
                return result
            
            # Deep comparison (order-independent)
            # Convert RealDictCursor output (list of dicts) to a comparable format.
            # We sort the rows based on their items so the order of returned rows doesn't affect equivalence.
            def make_hashable(data_list):
                return sorted([tuple(sorted(row.items())) for row in data_list])
                
            if make_hashable(orig_data) == make_hashable(rew_data):
                result["is_equivalent"] = True
                result["message"] = "Results are fully equivalent."
            else:
                result["message"] = "Row counts match but data content differs."

        except Exception as e:
            result["message"] = f"Unexpected error during comparison: {str(e)}"

        return result

    def close(self):
        """
        Closes the underlying database connection.
        """
        self.runner.close()


if __name__ == "__main__":
    print("Initializing ResultChecker...")
    checker = ResultChecker()
    
    q_orig = "SELECT 1 AS a, 2 AS b;"
    q_rew  = "SELECT 1 AS a, 2 AS b;"
    q_diff = "SELECT 1 AS a, 3 AS b;"
    q_err  = "SELECT * FROM table_that_does_not_exist;"
    
    print("\n[Test 1] Equivalent Queries:")
    res1 = checker.check_equivalence(q_orig, q_rew)
    print(res1)
    
    print("\n[Test 2] Different Queries:")
    res2 = checker.check_equivalence(q_orig, q_diff)
    print(res2)

    print("\n[Test 3] Error Query:")
    res3 = checker.check_equivalence(q_orig, q_err)
    print(res3)
    
    checker.close()
