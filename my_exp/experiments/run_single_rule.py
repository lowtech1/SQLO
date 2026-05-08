import json
import csv
import os
import sys

# Ensure we can import my_exp from the project root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from my_exp.rules.rule_registry import RULES

def run_single_rule_experiments():
    """
    Loads test queries, applies each rule individually, and records the results to a CSV file.
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

    # 2 & 3. Iterate through queries and run each rule
    for query in queries:
        query_id = query.get('query_id', 'unknown')
        original_sql = query.get('sql', '')
        
        for rule_name, rule_instance in RULES.items():
            try:
                # Apply the rule
                rewritten_sql = rule_instance.apply(original_sql)
                
                # Compare text to see if it changed
                changed = (original_sql.strip() != rewritten_sql.strip())
                note = ""
                
            except Exception as e:
                rewritten_sql = original_sql
                changed = False
                note = f"Error during execution: {str(e)}"
            
            # Store result
            results.append({
                'query_id': query_id,
                'rule_name': rule_name,
                'original_sql': original_sql,
                'rewritten_sql': rewritten_sql,
                'changed': changed,
                'note': note
            })

    # 4 & 5. Write results to CSV
    os.makedirs(os.path.dirname(results_file), exist_ok=True)
    with open(results_file, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['query_id', 'rule_name', 'original_sql', 'rewritten_sql', 'changed', 'note']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        
        writer.writeheader()
        for row in results:
            writer.writerow(row)
            
    print(f"Successfully ran single rule experiments. Results saved to: {results_file}")

if __name__ == "__main__":
    run_single_rule_experiments()
