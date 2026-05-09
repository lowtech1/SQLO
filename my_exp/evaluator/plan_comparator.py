import os
import sys
import json

# Ensure we can import my_exp from the project root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from my_exp.evaluator.explain_parser import ExplainParser

class PlanComparator:
    """
    Compares two PostgreSQL execution plans (original vs rewritten)
    to determine which one is better based on cost, time, and operators.
    Generates detailed optimizer reasoning.
    """

    def __init__(self):
        self.parser = ExplainParser()

    def _extract_plan_node(self, plan_json):
        if isinstance(plan_json, list) and len(plan_json) > 0:
            plan_json = plan_json[0]
        if isinstance(plan_json, dict):
            return plan_json.get("Plan", {})
        return {}

    def _count_node_type(self, node, target_type):
        """Recursively count occurrences of a specific node type."""
        count = 0
        if not isinstance(node, dict):
            return count
            
        if node.get("Node Type") == target_type:
            count += 1
            
        if "Plans" in node:
            for child in node["Plans"]:
                count += self._count_node_type(child, target_type)
        return count

    def _get_node_counts(self, node):
        return {
            "Seq Scan": self._count_node_type(node, "Seq Scan"),
            "Index Scan": self._count_node_type(node, "Index Scan"),
            "Bitmap Heap Scan": self._count_node_type(node, "Bitmap Heap Scan"),
            "Hash Join": self._count_node_type(node, "Hash Join"),
            "Merge Join": self._count_node_type(node, "Merge Join"),
            "Nested Loop": self._count_node_type(node, "Nested Loop"),
        }

    def _get_total_actual_rows(self, node):
        """Estimate total intermediate rows processed by all nodes."""
        rows = 0
        if not isinstance(node, dict):
            return rows
        if "Actual Rows" in node:
            # We take Actual Rows * Actual Loops as a rough estimate of processed rows
            loops = node.get("Actual Loops", 1)
            rows += (node.get("Actual Rows", 0) * loops)
            
        if "Plans" in node:
            for child in node["Plans"]:
                rows += self._get_total_actual_rows(child)
        return rows

    def generate_analysis_report(self, original_plan_json, rewritten_plan_json) -> dict:
        """
        Analyzes plan changes, extracts metrics, and infers optimizer reasoning.
        """
        orig_metrics = self.parser.parse(original_plan_json)
        rew_metrics = self.parser.parse(rewritten_plan_json)

        orig_node = self._extract_plan_node(original_plan_json)
        rew_node = self._extract_plan_node(rewritten_plan_json)

        orig_counts = self._get_node_counts(orig_node)
        rew_counts = self._get_node_counts(rew_node)

        orig_rows = self._get_total_actual_rows(orig_node)
        rew_rows = self._get_total_actual_rows(rew_node)

        orig_cost = orig_metrics.get("total_cost")
        rew_cost = rew_metrics.get("total_cost")
        orig_cost_val = orig_cost if orig_cost is not None else float('inf')
        rew_cost_val = rew_cost if rew_cost is not None else float('inf')
        
        orig_time = orig_metrics.get("execution_time")
        rew_time = rew_metrics.get("execution_time")
        orig_time_val = orig_time if orig_time is not None else float('inf')
        rew_time_val = rew_time if rew_time is not None else float('inf')
        
        # Calculations
        cost_diff = orig_cost_val - rew_cost_val if orig_cost_val != float('inf') and rew_cost_val != float('inf') else 0
        time_diff = orig_time_val - rew_time_val if orig_time_val != float('inf') and rew_time_val != float('inf') else 0
        
        row_reduction = orig_rows - rew_rows
        scan_reduction = orig_counts["Seq Scan"] - rew_counts["Seq Scan"]
        
        # Join efficiency: Positive means we moved from nested loops to hash/merge joins
        orig_efficient_joins = orig_counts["Hash Join"] + orig_counts["Merge Join"]
        rew_efficient_joins = rew_counts["Hash Join"] + rew_counts["Merge Join"]
        orig_nested = orig_counts["Nested Loop"]
        rew_nested = rew_counts["Nested Loop"]
        join_efficiency = (rew_efficient_joins - orig_efficient_joins) - (rew_nested - orig_nested)

        # Determine winner
        winner = "original"
        if rew_cost_val < orig_cost_val and rew_time_val < orig_time_val:
            winner = "rewritten"
        elif rew_cost_val < orig_cost_val:
            winner = "rewritten"
        elif rew_time_val < orig_time_val:
            winner = "rewritten"
        elif rew_time_val == orig_time_val and rew_cost_val == orig_cost_val and (scan_reduction > 0 or join_efficiency > 0):
            winner = "rewritten"

        # Generate Reasoning
        reasoning = []
        if scan_reduction > 0:
            reasoning.append("Predicate pushdown or projection pruning reduced sequential scans.")
            
        if rew_counts["Index Scan"] > orig_counts["Index Scan"] or rew_counts["Bitmap Heap Scan"] > orig_counts["Bitmap Heap Scan"]:
            reasoning.append("Rewrite enabled index usage.")
            
        if join_efficiency > 0:
            reasoning.append("Subquery unnesting enabled hash or merge join over nested loops.")
            
        if row_reduction > 0:
            reasoning.append("Rewrite reduced intermediate rows.")
            
        if not reasoning:
            if winner == "rewritten":
                reasoning.append("Rewritten query has better overall cost/time without major structural operator changes.")
            else:
                reasoning.append("Original query is structurally equivalent or better.")

        return {
            "winner": winner,
            "optimizer_reasoning": reasoning,
            "performance_summary": {
                "cost_original": orig_cost,
                "cost_rewritten": rew_cost,
                "cost_difference": round(cost_diff, 2),
                "time_original": orig_time,
                "time_rewritten": rew_time,
                "time_difference": round(time_diff, 3),
                "row_reduction": row_reduction,
                "scan_reduction": scan_reduction,
                "join_efficiency": join_efficiency
            },
            "physical_plan_changes": {
                "Seq Scan": {"original": orig_counts["Seq Scan"], "rewritten": rew_counts["Seq Scan"]},
                "Index Scan": {"original": orig_counts["Index Scan"], "rewritten": rew_counts["Index Scan"]},
                "Bitmap Heap Scan": {"original": orig_counts["Bitmap Heap Scan"], "rewritten": rew_counts["Bitmap Heap Scan"]},
                "Hash Join": {"original": orig_counts["Hash Join"], "rewritten": rew_counts["Hash Join"]},
                "Merge Join": {"original": orig_counts["Merge Join"], "rewritten": rew_counts["Merge Join"]},
                "Nested Loop": {"original": orig_counts["Nested Loop"], "rewritten": rew_counts["Nested Loop"]}
            }
        }


if __name__ == "__main__":
    comparator = PlanComparator()
    
    # Mock data showing Seq Scan -> Index Scan, and Nested Loop -> Hash Join
    mock_original = [{
        "Plan": {
            "Node Type": "Nested Loop",
            "Total Cost": 500.00,
            "Actual Rows": 1000,
            "Actual Loops": 1,
            "Plans": [
                {
                    "Node Type": "Seq Scan", 
                    "Total Cost": 250.00,
                    "Actual Rows": 1000,
                    "Actual Loops": 1
                },
                {
                    "Node Type": "Seq Scan", 
                    "Total Cost": 250.00,
                    "Actual Rows": 1,
                    "Actual Loops": 1000
                }
            ]
        },
        "Execution Time": 45.5
    }]
    
    mock_rewritten = [{
        "Plan": {
            "Node Type": "Hash Join",
            "Total Cost": 200.00,
            "Actual Rows": 1000,
            "Actual Loops": 1,
            "Plans": [
                {
                    "Node Type": "Index Scan", 
                    "Total Cost": 150.00,
                    "Actual Rows": 500,
                    "Actual Loops": 1
                },
                {
                    "Node Type": "Hash", 
                    "Total Cost": 50.00,
                    "Actual Rows": 500,
                    "Actual Loops": 1,
                    "Plans": [
                        {
                            "Node Type": "Index Scan",
                            "Total Cost": 50.00,
                            "Actual Rows": 500,
                            "Actual Loops": 1
                        }
                    ]
                }
            ]
        },
        "Execution Time": 12.2
    }]
    
    print("Testing PlanComparator - generate_analysis_report()...")
    result = comparator.generate_analysis_report(mock_original, mock_rewritten)
    print(json.dumps(result, indent=2))
