import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor

# Attempt to load from .env file
try:
    # pyrefly: ignore [missing-import]
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # If dotenv is not installed, it will fall back to existing environment variables
    pass

class PostgresRunner:
    """
    A utility class to connect to PostgreSQL and execute queries or retrieve query execution plans.
    """

    def __init__(self):
        self.host = os.getenv("POSTGRES_HOST", "localhost")
        self.port = os.getenv("POSTGRES_PORT", "5432")
        self.dbname = os.getenv("POSTGRES_DB", "postgres")
        self.user = os.getenv("POSTGRES_USER", "postgres")
        self.password = os.getenv("POSTGRES_PASSWORD", "")
        self.conn = None

    def connect(self):
        """
        Establishes a connection to the PostgreSQL database using credentials from environment variables.
        """
        try:
            if self.conn is None or self.conn.closed:
                self.conn = psycopg2.connect(
                    host=self.host,
                    port=self.port,
                    dbname=self.dbname,
                    user=self.user,
                    password=self.password
                )
                self.conn.autocommit = True
        except psycopg2.Error as e:
            print(f"Error connecting to PostgreSQL: {e}")
            raise

    def close(self):
        """
        Safely closes the connection to the database.
        """
        if self.conn and not self.conn.closed:
            self.conn.close()

    def run_query(self, sql: str):
        """
        Executes a standard SQL query.

        Args:
            sql (str): The SQL statement to run.

        Returns:
            list: The fetched rows as dictionaries, or None if an error occurs.
        """
        self.connect()
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql)
                # If the query does not return rows (e.g., INSERT/UPDATE/DELETE), cur.description is None
                if cur.description:
                    return cur.fetchall()
                return []
        except Exception as e:
            print(f"Error executing run_query: {e}")
            return None

    def explain_analyze(self, sql: str):
        """
        Runs EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) to get the query execution plan.

        Args:
            sql (str): The SQL statement to analyze.

        Returns:
            list/dict: The parsed JSON plan from PostgreSQL, or None if an error occurs.
        """
        self.connect()
        try:
            explain_query = f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {sql}"
            with self.conn.cursor() as cur:
                cur.execute(explain_query)
                result = cur.fetchone()
                if result:
                    # PostgreSQL returns a single JSON object (which is usually a list of plan nodes)
                    return result[0]
                return None
        except Exception as e:
            print(f"Error executing explain_analyze: {e}")
            return None


if __name__ == "__main__":
    print("Initializing PostgresRunner...")
    runner = PostgresRunner()
    
    print("\n[1] Testing run_query: SELECT 1 AS num;")
    try:
        res = runner.run_query("SELECT 1 AS num;")
        print("Result:", res)
    except Exception as e:
        print(f"Failed to run query test: {e}")

    print("\n[2] Testing explain_analyze: SELECT 1;")
    try:
        plan = runner.explain_analyze("SELECT 1;")
        if plan:
            print(json.dumps(plan, indent=2))
        else:
            print("No plan returned.")
    except Exception as e:
        print(f"Failed to run explain_analyze test: {e}")
        
    finally:
        runner.close()
