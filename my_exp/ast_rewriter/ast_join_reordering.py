import sqlglot
from sqlglot import expressions as exp
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from my_exp.ast_rewriter.ast_utils import parse_sql, clone_ast, ast_to_sql

class ASTJoinReordering:
    """
    AST-based Join Reordering optimization using sqlglot.
    
    Explanation of Database Optimizer Concepts:
    - Hash Join: An efficient join algorithm for large, unsorted datasets. It builds an in-memory hash table on the smaller relation, then probes it with the larger relation.
    - Nested Loop: A simple join algorithm that iterates over the outer table and performs a lookup on the inner table for each row. Efficient with indexes on small datasets, but disastrous (O(N*M)) for large Cartesian products.
    - Join Cardinality: The estimated number of rows resulting from joining tables.
    - Intermediate Row Explosion: A critical performance issue where joining large tables early (without restrictive filters) creates a massive intermediate result set, exhausting memory and CPU before the final filters are applied.
    
    This experimental rule heuristically reorders INNER JOINs in the AST to place smaller or heavily filtered tables earlier,
    aiming to reduce intermediate row explosion and encourage the planner to use optimal Hash Joins.
    """
    
    def __init__(self, debug=False):
        self.debug = debug

    def _get_table_alias_name(self, table_node: exp.Table) -> str:
        if table_node.alias:
            return table_node.alias.lower()
        return table_node.name.lower()

    def estimate_join_priority(self, table_name: str, alias: str, where_cols: set) -> int:
        """
        Heuristic function to estimate join priority.
        Lower number = Higher priority (executed earlier in the pipeline).
        
        Rules:
        1. Small dimension tables (e.g., nation, region) -> base priority 10
        2. Medium dimension tables (e.g., part, supplier, customer) -> base priority 30
        3. Fact tables (e.g., orders) -> base priority 80
        4. Huge fact tables (e.g., lineitem) -> base priority 100
        5. If the table is filtered in the WHERE clause, its priority is boosted.
        """
        name = table_name.lower()
        priority = 50 # default
        
        # Size heuristics (TPC-H scale assumptions)
        if name in ["nation", "region"]:
            priority = 10
        elif name in ["part", "supplier", "customer"]:
            priority = 30
        elif name in ["orders"]:
            priority = 80
        elif name in ["lineitem"]:
            priority = 100
            
        # Boost priority if table is heavily filtered
        if alias in where_cols or name in where_cols:
            priority -= 25 # Move it up the pipeline
            
        return max(0, priority)

    def _is_safe_to_reorder(self, select_node: exp.Select) -> bool:
        """
        Semantic safety checks.
        It is extremely dangerous to reorder OUTER JOINs, LEFT JOINs, or FULL JOINs
        because their result sets depend strictly on their evaluation order.
        Only purely INNER/CROSS joins are considered safe for naive AST reordering.
        """
        if not select_node.args.get("joins"):
            return False
            
        for join in select_node.args["joins"]:
            side = join.args.get("side")
            kind = join.args.get("kind")
            
            # side: LEFT, RIGHT, FULL
            if side and side.upper() in ("LEFT", "RIGHT", "FULL"):
                return False
                
            # kind: OUTER
            if kind and kind.upper() == "OUTER":
                return False
                
        return True

    def apply(self, sql: str) -> str:
        try:
            ast = parse_sql(sql)
        except Exception:
            return sql
            
        ast_copy = clone_ast(ast)
        
        for select in ast_copy.find_all(exp.Select):
            if not self._is_safe_to_reorder(select):
                continue
                
            joins = select.args.get("joins", [])
            # Need at least 2 joins (3 tables) to reorder joins meaningfully
            if len(joins) < 2:
                continue
                
            # Extract where columns to see which tables are filtered
            where_cols = set()
            where_node = select.args.get("where")
            if where_node:
                for col in where_node.find_all(exp.Column):
                    if col.table:
                        where_cols.add(col.table.lower())
                    else:
                        where_cols.add(col.name.lower())
                        
            original_order = []
            join_objects = []
            
            # Analyze JOIN nodes
            for j in joins:
                t = j.this
                if isinstance(t, exp.Table):
                    t_name = t.name.lower()
                    t_alias = self._get_table_alias_name(t)
                    original_order.append(t_alias or t_name)
                    
                    priority = self.estimate_join_priority(t_name, t_alias, where_cols)
                    join_objects.append({
                        "node": j,
                        "name": t_name,
                        "alias": t_alias,
                        "priority": priority
                    })
                else:
                    # Subqueries in JOINs get a neutral priority
                    original_order.append("subquery")
                    join_objects.append({
                        "node": j,
                        "name": "subquery",
                        "alias": "subquery",
                        "priority": 50
                    })

            # Reorder joins based on calculated priority
            # (Note: A rigorous DB engine would also validate ON condition dependencies here)
            join_objects.sort(key=lambda x: x["priority"])
            
            rewritten_order = [obj["alias"] or obj["name"] for obj in join_objects]
            
            if original_order != rewritten_order:
                # Apply new AST structure
                new_joins = [obj["node"] for obj in join_objects]
                select.set("joins", new_joins)
                
                if self.debug:
                    print("-" * 50)
                    print("AST Join Reordering Applied")
                    print(f"Original Order : {' -> '.join(original_order)}")
                    print(f"Rewritten Order: {' -> '.join(rewritten_order)}")
                    print("-" * 50)

        return ast_to_sql(ast_copy)

if __name__ == "__main__":
    rule = ASTJoinReordering(debug=True)
    
    print("\n[Test 1] Simple join reordering")
    # nation (small) should move before lineitem (huge)
    sql1 = "SELECT * FROM orders o JOIN lineitem l ON o.id = l.o_id JOIN nation n ON o.n_id = n.id;"
    print("Input :", sql1)
    print("Output:", rule.apply(sql1))
    
    print("\n[Test 2] Filtered join")
    # lineitem is huge, but it has a WHERE filter 'l.status', so its priority boosts
    sql2 = "SELECT * FROM orders o JOIN lineitem l ON o.id = l.o_id JOIN part p ON l.p_id = p.id WHERE l.status = 'SHIPPED';"
    print("Input :", sql2)
    print("Output:", rule.apply(sql2))
    
    print("\n[Test 3] Unsafe outer join (Should NOT rewrite)")
    sql3 = "SELECT * FROM orders o LEFT JOIN lineitem l ON o.id = l.o_id JOIN nation n ON o.n_id = n.id;"
    print("Input :", sql3)
    print("Output:", rule.apply(sql3))
