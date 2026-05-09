import os
import sys
import json
import csv

# Ensure we can import my_exp from the project root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from my_exp.experiments.cost_aware_optimizer import CostAwareOptimizer
from my_exp.evaluator.postgres_runner import PostgresRunner
from my_exp.evaluator.explain_parser import ExplainParser

def run_optimizer_benchmark():
    """
    Runs the complete CostAwareOptimizer against the test cases JSON
    and outputs the benchmarking results to a CSV file.
    """
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    queries_file = os.path.join(base_dir, 'queries', 'test_cases.json')
    results_file = os.path.join(base_dir, 'results', 'optimizer_benchmark_results.csv')

    if not os.path.exists(queries_file):
        print(f"Error: {queries_file} not found.")
        return

    with open(queries_file, 'r', encoding='utf-8') as f:
        queries = json.load(f)

    # Initialize components
    optimizer = CostAwareOptimizer()
    runner = PostgresRunner()
    parser = ExplainParser()
    
    try:
        runner.connect()
    except Exception as e:
        print(f"PostgreSQL connection failed: {e}")
        return

    results = []

    print(f"Starting Cost-Aware Optimizer Benchmark on {len(queries)} queries...")

    for i, query in enumerate(queries, 1):
        query_id = query.get('query_id', f'unknown_{i}')
        original_sql = query.get('sql', '')
        
        print(f"Processing [{i}/{len(queries)}]: {query_id}")

        # 1. Measure baseline metrics for Original SQL
        orig_time = None
        orig_cost = None
        try:
            orig_plan = runner.explain_analyze(original_sql)
            if orig_plan:
                orig_metrics = parser.parse(orig_plan)
                orig_time = orig_metrics.get("execution_time")
                orig_cost = orig_metrics.get("total_cost")
        except Exception:
            pass

        # 2. Run CostAwareOptimizer
        try:
            opt_result = optimizer.optimize(original_sql)
            optimized_sql = opt_result.get("best_sql", original_sql)
            applied_rules = opt_result.get("best_rules", [])
            best_score = opt_result.get("best_score", 0.0)
            reasoning = opt_result.get("optimizer_reasoning", "")
            eval_count = opt_result.get("evaluated_candidates", 0)
            rej_cands = opt_result.get("rejected_candidates", [])
            
            note = "Optimization successful" if best_score > 0 else "No effective rewrite"
        except Exception as e:
            # 5. Do not crash if a query fails
            optimized_sql = original_sql
            applied_rules = []
            best_score = 0.0
            reasoning = f"Optimizer crashed: {str(e)}"
            eval_count = 0
            rej_cands = []
            note = "Error during optimization"

        # 3. Measure metrics for Optimized SQL
        opt_time = None
        opt_cost = None
        if optimized_sql.strip() != original_sql.strip():
            try:
                opt_plan = runner.explain_analyze(optimized_sql)
                if opt_plan:
                    opt_metrics = parser.parse(opt_plan)
                    opt_time = opt_metrics.get("execution_time")
                    opt_cost = opt_metrics.get("total_cost")
            except Exception as e:
                note += f" | Explain optimized SQL failed: {str(e)}"
        else:
            opt_time = orig_time
            opt_cost = orig_cost

        # 4. Save results row
        results.append({
            'query_id': query_id,
            'original_sql': original_sql,
            'optimized_sql': optimized_sql,
            'applied_rules': json.dumps(applied_rules),
            'original_time': orig_time,
            'optimized_time': opt_time,
            'original_cost': orig_cost,
            'optimized_cost': opt_cost,
            'best_score': best_score,
            'evaluated_candidates': eval_count,
            'rejected_candidates': len(rej_cands),
            'optimizer_reasoning': reasoning,
            'note': note
        })

    # Export to CSV
    os.makedirs(os.path.dirname(results_file), exist_ok=True)
    with open(results_file, 'w', newline='', encoding='utf-8') as f:
        fieldnames = [
            'query_id', 'original_sql', 'optimized_sql', 'applied_rules', 
            'original_time', 'optimized_time', 'original_cost', 'optimized_cost',
            'best_score', 'evaluated_candidates', 'rejected_candidates', 
            'optimizer_reasoning', 'note'
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    optimizer.close()
    runner.close()
    print("\nBenchmark completed successfully.")
    print(f"Results saved to: {results_file}")

if __name__ == "__main__":
    run_optimizer_benchmark()
