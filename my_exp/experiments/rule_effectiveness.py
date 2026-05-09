import csv
import os
import sys

def safe_float(val):
    try:
        return float(val)
    except (ValueError, TypeError):
        return None

def analyze_single_rules(single_results_file):
    rules_data = {}
    
    if not os.path.exists(single_results_file):
        print(f"Warning: File not found {single_results_file}")
        return rules_data

    with open(single_results_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rule = row.get('rule_name')
            if not rule:
                continue
                
            if rule not in rules_data:
                rules_data[rule] = {
                    'total_cases': 0,
                    'changed_cases': 0,
                    'successful_cases': 0,
                    'worse_cases': 0,
                    'semantic_mismatch_cases': 0,
                    'no_change_cases': 0,
                    'sum_improvement': 0.0,
                    'count_improvement': 0,
                    'sum_cost_reduction': 0.0,
                    'count_cost_reduction': 0
                }
                
            data = rules_data[rule]
            data['total_cases'] += 1
            
            changed = row.get('changed', 'False').lower() == 'true'
            is_equiv = row.get('is_equivalent', 'False').lower() == 'true'
            note = row.get('note', '').lower()
            
            imp_pct = safe_float(row.get('improvement_percent'))
            cost_pct = safe_float(row.get('cost_reduction_percent'))
            
            if not changed:
                data['no_change_cases'] += 1
            else:
                data['changed_cases'] += 1
                
                if not is_equiv:
                    data['semantic_mismatch_cases'] += 1
                else:
                    # Valid rewrite
                    if imp_pct is not None:
                        data['sum_improvement'] += imp_pct
                        data['count_improvement'] += 1
                    if cost_pct is not None:
                        data['sum_cost_reduction'] += cost_pct
                        data['count_cost_reduction'] += 1
                        
                    is_better = (imp_pct is not None and imp_pct > 0) or (cost_pct is not None and cost_pct > 0)
                    if is_better or "successful" in note:
                        data['successful_cases'] += 1
                    else:
                        data['worse_cases'] += 1

    # Calculate averages and rates
    for rule, data in rules_data.items():
        data['average_execution_improvement'] = (data['sum_improvement'] / data['count_improvement']) if data['count_improvement'] > 0 else 0.0
        data['average_cost_reduction'] = (data['sum_cost_reduction'] / data['count_cost_reduction']) if data['count_cost_reduction'] > 0 else 0.0
        
        data['success_rate'] = (data['successful_cases'] / data['total_cases'] * 100) if data['total_cases'] > 0 else 0.0
        
        if data['changed_cases'] > 0:
            data['semantic_correctness_rate'] = ((data['changed_cases'] - data['semantic_mismatch_cases']) / data['changed_cases']) * 100
        else:
            data['semantic_correctness_rate'] = 100.0

    return rules_data

def analyze_multi_rules(multi_results_file):
    multi_data = {
        'total_cases': 0,
        'improved_queries': 0,
        'worsened_queries': 0,
        'no_effective_rewrite': 0,
        'sum_improvement': 0.0,
        'count_improvement': 0,
        'sum_cost_reduction': 0.0,
        'count_cost_reduction': 0,
        'average_improvement': 0.0,
        'average_cost_reduction': 0.0
    }
    
    if not os.path.exists(multi_results_file):
        print(f"Warning: File not found {multi_results_file}")
        return multi_data

    with open(multi_results_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            multi_data['total_cases'] += 1
            
            note = row.get('note', '').lower()
            imp_pct = safe_float(row.get('improvement_percent'))
            cost_pct = safe_float(row.get('cost_reduction_percent'))
            
            if "no effective rewrite" in note:
                multi_data['no_effective_rewrite'] += 1
            else:
                if imp_pct is not None:
                    multi_data['sum_improvement'] += imp_pct
                    multi_data['count_improvement'] += 1
                if cost_pct is not None:
                    multi_data['sum_cost_reduction'] += cost_pct
                    multi_data['count_cost_reduction'] += 1
                    
                is_better = (imp_pct is not None and imp_pct > 0) or (cost_pct is not None and cost_pct > 0)
                if is_better or "successful" in note:
                    multi_data['improved_queries'] += 1
                else:
                    multi_data['worsened_queries'] += 1

    if multi_data['count_improvement'] > 0:
        multi_data['average_improvement'] = multi_data['sum_improvement'] / multi_data['count_improvement']
    if multi_data['count_cost_reduction'] > 0:
        multi_data['average_cost_reduction'] = multi_data['sum_cost_reduction'] / multi_data['count_cost_reduction']

    return multi_data

def generate_reports():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    results_dir = os.path.join(base_dir, 'results')
    
    single_results_file = os.path.join(results_dir, 'single_rule_results.csv')
    multi_results_file = os.path.join(results_dir, 'multi_rule_results.csv')
    
    report_csv_file = os.path.join(results_dir, 'rule_effectiveness_report.csv')
    report_md_file = os.path.join(results_dir, 'rule_effectiveness_summary.md')

    rules_data = analyze_single_rules(single_results_file)
    multi_data = analyze_multi_rules(multi_results_file)
    
    if not rules_data and multi_data['total_cases'] == 0:
        print("Error: No data available to analyze.")
        return

    # Export to CSV
    os.makedirs(results_dir, exist_ok=True)
    with open(report_csv_file, 'w', newline='', encoding='utf-8') as f:
        fieldnames = [
            'rule_name', 'total_cases', 'changed_cases', 'successful_cases', 
            'worse_cases', 'semantic_mismatch_cases', 'no_change_cases', 
            'average_execution_improvement', 'average_cost_reduction', 
            'success_rate', 'semantic_correctness_rate'
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for rule, data in rules_data.items():
            row = {'rule_name': rule}
            row.update({k: round(v, 2) if isinstance(v, float) else v for k, v in data.items() if k in fieldnames})
            writer.writerow(row)

    # Determine Summary Insights
    best_rule = None
    worst_rule = None
    safest_rule = None
    most_unstable_rule = None
    
    if rules_data:
        # Best rule: Highest average execution improvement
        best_rule = max(rules_data.keys(), key=lambda r: rules_data[r]['average_execution_improvement'])
        
        # Worst rule: Highest worse_cases or lowest improvement
        worst_rule = min(rules_data.keys(), key=lambda r: rules_data[r]['average_execution_improvement'])
        
        # Safest rule: Highest semantic correctness rate
        safest_rule = max(rules_data.keys(), key=lambda r: rules_data[r]['semantic_correctness_rate'])
        
        # Most unstable rule: Lowest semantic correctness rate
        most_unstable_rule = min(rules_data.keys(), key=lambda r: rules_data[r]['semantic_correctness_rate'])

    # Best strategy
    multi_avg_imp = multi_data.get('average_improvement', 0.0)
    best_single_avg_imp = rules_data[best_rule]['average_execution_improvement'] if best_rule else 0.0
    
    best_strategy = "Multi-Rule" if multi_avg_imp > best_single_avg_imp else "Single-Rule"

    # Export to Markdown
    with open(report_md_file, 'w', encoding='utf-8') as f:
        f.write("# Optimizer Rule Effectiveness Summary\n\n")
        
        f.write("## Insights\n")
        f.write(f"- **Best Rule**: `{best_rule}` (Highest average execution time improvement)\n")
        f.write(f"- **Worst Rule**: `{worst_rule}` (Lowest average execution time improvement)\n")
        f.write(f"- **Safest Rule**: `{safest_rule}` (Highest semantic correctness rate)\n")
        f.write(f"- **Most Unstable Rule**: `{most_unstable_rule}` (Lowest semantic correctness rate or highest mismatches)\n")
        f.write(f"- **Best Overall Strategy**: `{best_strategy}` (Comparing average improvement: Multi-Rule={multi_avg_imp:.2f}% vs Best Single-Rule={best_single_avg_imp:.2f}%)\n\n")
        
        f.write("## Multi-Rule Pipeline Performance\n")
        f.write(f"- **Total Queries Evaluated**: {multi_data['total_cases']}\n")
        f.write(f"- **Improved Queries**: {multi_data['improved_queries']}\n")
        f.write(f"- **Worsened/No-Benefit Queries**: {multi_data['worsened_queries']}\n")
        f.write(f"- **No Effective Rewrite**: {multi_data['no_effective_rewrite']}\n")
        f.write(f"- **Average Time Improvement**: {multi_avg_imp:.2f}%\n")
        f.write(f"- **Average Cost Reduction**: {multi_data['average_cost_reduction']:.2f}%\n\n")

        f.write("## Single Rule Metrics Breakdown\n")
        f.write("| Rule Name | Total | Changed | Success | Worse | Mismatch | No Change | Time Imp. (%) | Cost Red. (%) | Success Rate (%) | Correctness Rate (%) |\n")
        f.write("|-----------|-------|---------|---------|-------|----------|-----------|---------------|---------------|------------------|----------------------|\n")
        
        for rule, data in rules_data.items():
            f.write(f"| {rule} | {data['total_cases']} | {data['changed_cases']} | {data['successful_cases']} | "
                    f"{data['worse_cases']} | {data['semantic_mismatch_cases']} | {data['no_change_cases']} | "
                    f"{data['average_execution_improvement']:.2f} | {data['average_cost_reduction']:.2f} | "
                    f"{data['success_rate']:.2f} | {data['semantic_correctness_rate']:.2f} |\n")

    print(f"Report CSV saved to: {report_csv_file}")
    print(f"Summary Markdown saved to: {report_md_file}")

if __name__ == "__main__":
    generate_reports()
