import json

class ExplainParser:
    """
    Parses PostgreSQL EXPLAIN ANALYZE JSON output to extract key metrics.
    """
    
    def parse(self, plan_json) -> dict:
        """
        Parses the execution plan JSON and extracts relevant metrics.
        Returns None for missing fields to prevent crashes.

        Args:
            plan_json (dict or list): The parsed JSON plan from PostgreSQL.

        Returns:
            dict: Extracted metrics containing execution_time, planning_time, 
                  total_cost, actual_rows, plan_type, node_types, scan_types, 
                  and join_types.
        """
        # PostgreSQL EXPLAIN output is usually a list containing one dictionary
        if isinstance(plan_json, list) and len(plan_json) > 0:
            plan_json = plan_json[0]
            
        if not isinstance(plan_json, dict):
            return self._empty_result()
            
        plan_node = plan_json.get("Plan", {})
        if not plan_node:
            return self._empty_result()

        node_types = []
        scan_types = []
        join_types = []

        self._traverse_plan(plan_node, node_types, scan_types, join_types)

        return {
            "execution_time": plan_json.get("Execution Time"),
            "planning_time": plan_json.get("Planning Time"),
            "total_cost": plan_node.get("Total Cost"),
            "actual_rows": plan_node.get("Actual Rows"),
            "plan_type": plan_node.get("Node Type"),
            "node_types": list(set(node_types)),
            "scan_types": list(set(scan_types)),
            "join_types": list(set(join_types))
        }

    def _empty_result(self) -> dict:
        return {
            "execution_time": None,
            "planning_time": None,
            "total_cost": None,
            "actual_rows": None,
            "plan_type": None,
            "node_types": [],
            "scan_types": [],
            "join_types": []
        }

    def _traverse_plan(self, node: dict, node_types: list, scan_types: list, join_types: list):
        if not isinstance(node, dict):
            return
            
        node_type = node.get("Node Type")
        if node_type:
            node_types.append(node_type)
            
            # Categorize scan types
            if "Scan" in node_type:
                scan_types.append(node_type)
                
            # Categorize join types
            if "Join" in node_type or "Nested Loop" in node_type:
                join_types.append(node_type)
                
        # Recursively traverse children plans
        if "Plans" in node:
            for child in node["Plans"]:
                self._traverse_plan(child, node_types, scan_types, join_types)

if __name__ == "__main__":
    parser = ExplainParser()
    
    # Mock data representing PostgreSQL EXPLAIN ANALYZE FORMAT JSON output
    mock_json = [
        {
            "Plan": {
                "Node Type": "Aggregate",
                "Strategy": "Plain",
                "Partial Mode": "Simple",
                "Parallel Aware": False,
                "Async Capable": False,
                "Startup Cost": 15.35,
                "Total Cost": 15.36,
                "Plan Rows": 1,
                "Plan Width": 8,
                "Actual Rows": 1,
                "Actual Loops": 1,
                "Plans": [
                    {
                        "Node Type": "Hash Join",
                        "Parent Relationship": "Outer",
                        "Parallel Aware": False,
                        "Async Capable": False,
                        "Join Type": "Inner",
                        "Startup Cost": 1.06,
                        "Total Cost": 15.35,
                        "Plan Rows": 1,
                        "Plan Width": 4,
                        "Actual Rows": 0,
                        "Actual Loops": 1,
                        "Plans": [
                            {
                                "Node Type": "Seq Scan",
                                "Parent Relationship": "Outer",
                                "Parallel Aware": False,
                                "Async Capable": False,
                                "Relation Name": "customer",
                                "Alias": "customer",
                                "Startup Cost": 0.00,
                                "Total Cost": 14.00,
                                "Plan Rows": 400,
                                "Plan Width": 4,
                                "Actual Rows": 400,
                                "Actual Loops": 1
                            },
                            {
                                "Node Type": "Hash",
                                "Parent Relationship": "Inner",
                                "Parallel Aware": False,
                                "Async Capable": False,
                                "Startup Cost": 1.05,
                                "Total Cost": 1.05,
                                "Plan Rows": 1,
                                "Plan Width": 4,
                                "Actual Rows": 1,
                                "Actual Loops": 1,
                                "Plans": [
                                    {
                                        "Node Type": "Index Scan",
                                        "Parent Relationship": "Outer",
                                        "Parallel Aware": False,
                                        "Async Capable": False,
                                        "Scan Direction": "Forward",
                                        "Index Name": "orders_pkey",
                                        "Relation Name": "orders",
                                        "Alias": "orders",
                                        "Startup Cost": 0.15,
                                        "Total Cost": 1.05,
                                        "Plan Rows": 1,
                                        "Plan Width": 4,
                                        "Actual Rows": 1,
                                        "Actual Loops": 1
                                    }
                                ]
                            }
                        ]
                    }
                ]
            },
            "Planning Time": 0.152,
            "Triggers": [],
            "Execution Time": 0.058
        }
    ]
    
    print("Testing ExplainParser with mock JSON data...")
    result = parser.parse(mock_json)
    print(json.dumps(result, indent=2))
