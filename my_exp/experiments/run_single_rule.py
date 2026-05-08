import json
import csv
import os
import sys

# Ensure we can import my_exp from the project root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from my_exp.rules.rule_registry import RULES
from my_exp.evaluator.postgres_runner import PostgresRunner
from my_exp.evaluator.explain_parser import ExplainParser

# Configuration flag
USE_POSTGRES = False

def calculate_improvement(original, new_val):
    if original is None or new_val is None or original == 0:
        return None
    return round(((original - new_val) / original) * 100, 2)

def run_single_rule_experiments():
    """
    Loads test queries, applies each rule individually, and records the results to a CSV file.
    Optionally evaluates the queries against PostgreSQL to gather cost and time metrics.
    """
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    queries_file = os.path.join(base_dir, 'queries', 'test_cases.json')
    results_file = os.path.join(base_dir, 'results', 'single_rule_results.csv')

    # 1. Load queries
    if not os.path.exists(queries_file):
        print(f"Error: {queries_file} not found.")
        return

    with open(queries_file, 'r', encoding='utf-8') as f:
        queries = json.load(f)

    results = []
    
    # Initialize DB components if USE_POSTGRES is enabled
    runner = None
    parser = None
    global USE_POSTGRES
    if USE_POSTGRES:
        try:
            runner = PostgresRunner()
            parser = ExplainParser()
            runner.connect()
            print("Successfully connected to PostgreSQL for evaluation.")
        except Exception as e:
            print(f"Failed to initialize PostgreSQL runner: {e}")
            print("Falling back to text-only comparison (USE_POSTGRES = False).")
            USE_POSTGRES = False

    # 2 & 3. Iterate through queries and run each rule
    for query in queries:
        query_id = query.get('query_id', 'unknown')
        original_sql = query.get('sql', '')
        
        for rule_name, rule_instance in RULES.items():
            original_time = None
            rewritten_time = None
            improvement_percent = None
            original_cost = None
            rewritten_cost = None
            cost_reduction_percent = None
            note = ""
            changed = False
            rewritten_sql = original_sql
            
            try:
                # Apply the rule
                rewritten_sql = rule_instance.apply(original_sql)
                
                # Compare text to see if it changed
                changed = (original_sql.strip() != rewritten_sql.strip())
                
            except Exception as e:
                rewritten_sql = original_sql
                changed = False
                note = f"Rewrite Error: {str(e)}"
            
            # If PostgreSQL evaluation is enabled, gather metrics
            if USE_POSTGRES and not note.startswith("Rewrite Error"):
                try:
                    # Get metrics for Original SQL
                    orig_plan_json = runner.explain_analyze(original_sql)
                    if orig_plan_json:
                        orig_metrics = parser.parse(orig_plan_json)
                        original_time = orig_metrics.get("execution_time")
                        original_cost = orig_metrics.get("total_cost")
                    else:
                        note += "Original SQL explain failed. "

                    # Get metrics for Rewritten SQL (only run explain if query changed to save time)
                    if changed:
                        rew_plan_json = runner.explain_analyze(rewritten_sql)
                        if rew_plan_json:
                            rew_metrics = parser.parse(rew_plan_json)
                            rewritten_time = rew_metrics.get("execution_time")
                            rewritten_cost = rew_metrics.get("total_cost")
                        else:
                            note += "Rewritten SQL explain failed. "
                    else:
                        rewritten_time = original_time
                        rewritten_cost = original_cost
                        
                    # Calculate improvements
                    if original_time is not None and rewritten_time is not None:
                        improvement_percent = calculate_improvement(original_time, rewritten_time)
                        
                    if original_cost is not None and rewritten_cost is not None:
                        cost_reduction_percent = calculate_improvement(original_cost, rewritten_cost)
                        
                except Exception as e:
                    note += f"DB Error: {str(e)}"

            # 4 & 5. Store result
            results.append({
                'query_id': query_id,
                'rule_name': rule_name,
                'original_sql': original_sql,
                'rewritten_sql': rewritten_sql,
                'changed': changed,
                'original_time': original_time,
                'rewritten_time': rewritten_time,
                'improvement_percent': improvement_percent,
                'original_cost': original_cost,
                'rewritten_cost': rewritten_cost,
                'cost_reduction_percent': cost_reduction_percent,
                'note': note.strip()
            })

    # Write results to CSV
    os.makedirs(os.path.dirname(results_file), exist_ok=True)
    with open(results_file, 'w', newline='', encoding='utf-8') as f:
        fieldnames = [
            'query_id', 'rule_name', 'original_sql', 'rewritten_sql', 'changed',
            'original_time', 'rewritten_time', 'improvement_percent',
            'original_cost', 'rewritten_cost', 'cost_reduction_percent', 'note'
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        
        writer.writeheader()
        for row in results:
            writer.writerow(row)
            
    print(f"Successfully ran single rule experiments. Results saved to: {results_file}")
    
    if runner:
        runner.close()

if __name__ == "__main__":
    run_single_rule_experiments()
