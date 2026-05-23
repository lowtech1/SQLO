"""
GIAI DOAN 2: Tinh toan Rule Effectiveness Metrics.

Doc ket qua tu full_evaluation_per_rule.csv (giai doan 1),
tinh cac metrics theo tung rule va luu vao:
  - rule_effectiveness_summary.csv
  - rule_effectiveness_report.md

Cac metrics tinh toan:
  - total_cases: So cap danh gia cho rule
  - changed_cases: So query bi thay doi boi rule
  - semantic_correct_rate: Ty le semantic equivalence
  - avg_time_improvement: Trung binh % cai thien thoi gian
  - avg_cost_reduction: Trung binh % giam cost
  - winner_rate: Ty le rewritten tot hon original
  - KB_accuracy: Ty le rule duoc recommend dung target
"""

import os
import sys
import json
import csv
import statistics

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))


def load_full_results(results_dir: str) -> list:
    """Doc ket qua chi tiet tu full_evaluation_results.jsonl (streaming JSON Lines)."""
    jsonl_path = os.path.join(results_dir, 'full_evaluation_results.jsonl')
    json_path = os.path.join(results_dir, 'full_evaluation_results.json')
    results = []

    # Thu JSONL truoc, neu khong co thi doc JSON cu
    for path in [jsonl_path, json_path]:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                if path.endswith('.jsonl'):
                    for line in f:
                        line = line.strip()
                        if line:
                            results.append(json.loads(line))
                else:
                    results = json.load(f)
            break
    else:
        print(f"[WARN] Khong tim thay ket qua. Run giai doan 1 truoc.")
    return results


def load_per_rule_csv(csv_path: str) -> list:
    """Doc du lieu per-rule tu CSV."""
    rows = []
    if not os.path.exists(csv_path):
        print(f"[WARN] {csv_path} not found.")
        return rows
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def compute_rule_metrics(rule_name: str, rows: list) -> dict:
    """Tinh metrics cho mot rule cu the."""
    rule_rows = [r for r in rows if r.get("rule_name") == rule_name]
    if not rule_rows:
        return {}

    total = len(rule_rows)

    # Changed cases
    changed = [r for r in rule_rows if r.get("changed") == "True"]
    changed_count = len(changed)

    # Semantic correctness
    sem_correct = [r for r in changed if r.get("is_equivalent") == "True"]
    sem_correct_count = len(sem_correct)
    sem_rate = (sem_correct_count / changed_count * 100) if changed_count > 0 else 0

    # Winners (rewritten better than original)
    winners = [r for r in changed if r.get("winner") == "rewritten"]
    winner_count = len(winners)
    winner_rate = (winner_count / changed_count * 100) if changed_count > 0 else 0

    # Time improvements
    time_imps = []
    for r in changed:
        v = r.get("time_improvement_pct")
        if v and v != "None" and v != "":
            try:
                time_imps.append(float(v))
            except (ValueError, TypeError):
                pass

    avg_time = statistics.mean(time_imps) if time_imps else 0
    median_time = statistics.median(time_imps) if time_imps else 0
    max_time = max(time_imps) if time_imps else 0
    min_time = min(time_imps) if time_imps else 0

    # Cost reductions
    cost_reds = []
    for r in changed:
        v = r.get("cost_reduction_pct")
        if v and v != "None" and v != "":
            try:
                cost_reds.append(float(v))
            except (ValueError, TypeError):
                pass

    avg_cost = statistics.mean(cost_reds) if cost_reds else 0

    # KB recommendation accuracy (trong tat ca queries, co bao nhieu query
    # ma rule nay nam trong target_rules cua query do)
    target_cases = [r for r in rule_rows if r.get("target_rule") == "True"]
    target_total = len(target_cases)
    target_changed = sum(1 for r in target_cases if r.get("changed") == "True")
    kb_precision = (target_changed / target_total * 100) if target_total > 0 else 0

    return {
        "rule_name": rule_name,
        "total_cases": total,
        "changed_cases": changed_count,
        "changed_rate": round(changed_count / total * 100, 1) if total > 0 else 0,
        "semantic_correct": sem_correct_count,
        "semantic_correct_rate": round(sem_rate, 1),
        "winners": winner_count,
        "winner_rate": round(winner_rate, 1),
        "avg_time_improvement_pct": round(avg_time, 2),
        "median_time_improvement_pct": round(median_time, 2),
        "max_time_improvement_pct": round(max_time, 2),
        "min_time_improvement_pct": round(min_time, 2),
        "avg_cost_reduction_pct": round(avg_cost, 2),
        "avg_time_improvement_abs_ms": round(avg_time, 3),
        "seq_scan_reduced": 0,
        "kb_target_cases": target_total,
        "kb_target_changed": target_changed,
        "kb_precision": round(kb_precision, 1),
        "improvement_cases": len([v for v in time_imps if v > 0]),
        "regression_cases": len([v for v in time_imps if v < 0]),
        "stable_cases": len([v for v in time_imps if v == 0]),
    }


def generate_rule_report(results_dir: str):
    """Doc ket qua, tinh metrics, luu bao cao."""
    csv_path = os.path.join(results_dir, 'full_evaluation_per_rule.csv')

    rows = load_per_rule_csv(csv_path)

    if not rows:
        print("[ERROR] No data. Run giai doan 1 first.")
        return

    # 8 rules
    rule_names = [
        "ast_predicate_pushdown",
        "ast_projection_pruning",
        "ast_subquery_unnesting",
        "ast_join_reordering",
        "ast_aggregation_pushdown",
        "ast_redundant_join_elimination",
        "ast_filter_into_join",
        "ast_limit_pushdown",
    ]

    # Rule descriptions
    rule_descs = {
        "ast_predicate_pushdown": "Day WHERE tu query ngoai vao subquery",
        "ast_projection_pruning": "Loai bo cot thua khoi subquery",
        "ast_subquery_unnesting": "Chuyen IN/EXISTS thanh JOIN",
        "ast_join_reordering": "Sap xep lai thu tu JOIN",
        "ast_aggregation_pushdown": "Day GROUP BY/aggregate vao subquery",
        "ast_redundant_join_elimination": "Loai bo JOIN thua",
        "ast_filter_into_join": "Day WHERE filter vao JOIN ON",
        "ast_limit_pushdown": "Day LIMIT vao subquery",
    }

    metrics_by_rule = {}
    for rn in rule_names:
        m = compute_rule_metrics(rn, rows)
        if m:
            metrics_by_rule[rn] = m

    # Tong hop
    all_changed = [r for r in rows if r.get("changed") == "True"]
    all_winners = [r for r in all_changed if r.get("winner") == "rewritten"]
    all_sem = [r for r in all_changed if r.get("is_equivalent") == "True"]

    all_time_imps = []
    for r in all_changed:
        v = r.get("time_improvement_pct")
        if v and v != "None" and v != "":
            try:
                all_time_imps.append(float(v))
            except (ValueError, TypeError):
                pass

    # Luu CSV tong hop
    csv_out = os.path.join(results_dir, 'rule_effectiveness_summary.csv')
    fieldnames = [
        "rule_name", "description", "total_cases", "changed_cases", "changed_rate",
        "semantic_correct", "semantic_correct_rate",
        "winners", "winner_rate",
        "avg_time_improvement_pct", "median_time_improvement_pct",
        "max_time_improvement_pct", "min_time_improvement_pct",
        "avg_cost_reduction_pct",
        "improvement_cases", "regression_cases", "stable_cases",
        "seq_scan_reduced",
        "kb_target_cases", "kb_target_changed", "kb_precision",
    ]

    with open(csv_out, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        for rn in rule_names:
            if rn in metrics_by_rule:
                row = dict(metrics_by_rule[rn])
                row["description"] = rule_descs.get(rn, "")
                writer.writerow(row)

    print(f"[Saved] {csv_out}")

    # Markdown report
    md_out = os.path.join(results_dir, 'rule_effectiveness_report.md')
    _write_markdown_report(md_out, metrics_by_rule, rule_descs, rows,
                           all_winners, all_sem)

    print(f"[Saved] {md_out}")
    return metrics_by_rule


def _write_markdown_report(path: str, metrics: dict, rule_descs: dict,
                           rows: list, all_winners: list, all_sem: list):
    """Viet bao cao markdown."""
    with open(path, 'w', encoding='utf-8') as f:
        f.write("# Bao Cao Hieu Qua Tung Luat Rewrite\n\n")
        f.write("*Duoc tao tu dong - Giai doan 2*\n\n")

        # Bang tom tat
        f.write("## 1. Bang Tom Tat Hieu Qua Cac Luat\n\n")
        f.write("| STT | Luat | Mo ta | Tong | Da doi | Ty le doi | Chinh xac semantic | Ty le thang | TB cai thien (%) |\n")
        f.write("|-----|------|-------|------|--------|-----------|-------------------|------------|----------------|\n")
        for i, (rn, m) in enumerate(metrics.items(), 1):
            desc = rule_descs.get(rn, "")
            if len(desc) > 35:
                desc = desc[:35] + "..."
            f.write(f"| {i} | **{rn}** | {desc} | {m['total_cases']} | "
                    f"{m['changed_cases']} | {m['changed_rate']}% | "
                    f"{m['semantic_correct']}/{m['changed_cases']} ({m['semantic_correct_rate']}%) | "
                    f"{m['winners']}/{m['changed_cases']} ({m['winner_rate']}%) | "
                    f"{m['avg_time_improvement_pct']:+.2f}% |\n")

        # Chi tiet tung rule
        f.write("\n## 2. Chi Tiet Tung Luat\n\n")
        for i, (rn, m) in enumerate(metrics.items(), 1):
            f.write(f"### {i}. {rn}\n\n")
            f.write(f"**Mo ta:** {rule_descs.get(rn, 'N/A')}\n\n")
            f.write("| Metric | Gia tri |\n")
            f.write("|--------|---------|\n")
            f.write(f"| Tong so cap danh gia | {m['total_cases']} |\n")
            f.write(f"| So query bi thay doi | {m['changed_cases']} ({m['changed_rate']}%) |\n")
            f.write(f"| Semantic correct | {m['semantic_correct']}/{m['changed_cases']} ({m['semantic_correct_rate']}%) |\n")
            f.write(f"| Rewritten tot hon (winners) | {m['winners']}/{m['changed_cases']} ({m['winner_rate']}%) |\n")
            f.write(f"| TB cai thien thoi gian | {m['avg_time_improvement_pct']:+.2f}% |\n")
            f.write(f"| Median cai thien | {m['median_time_improvement_pct']:+.2f}% |\n")
            f.write(f"| Max cai thien | {m['max_time_improvement_pct']:+.2f}% |\n")
            f.write(f"| Min cai thien | {m['min_time_improvement_pct']:+.2f}% |\n")
            f.write(f"| TB giam cost | {m['avg_cost_reduction_pct']:+.2f}% |\n")
            f.write(f"| Cases cai thien | {m['improvement_cases']} |\n")
            f.write(f"| Cases cham hon | {m['regression_cases']} |\n")
            f.write(f"| Cases khong doi | {m['stable_cases']} |\n")
            f.write(f"| Seq Scan giam | {m['seq_scan_reduced']} |\n")
            if m['kb_target_cases'] > 0:
                f.write(f"| KB Precision (target queries) | {m['kb_target_changed']}/{m['kb_target_cases']} ({m['kb_precision']}%) |\n")
            f.write("\n")

        # Bang so sanh KB vs LLM (mock)
        f.write("\n## 3. Bang So Sanh Chinh Xac KB Rule Selection\n\n")
        f.write("| Luat | Target queries | Changed (dung) | KB Precision |\n")
        f.write("|------|----------------|----------------|-------------|\n")
        for rn, m in metrics.items():
            if m['kb_target_cases'] > 0:
                f.write(f"| {rn} | {m['kb_target_cases']} | {m['kb_target_changed']} | {m['kb_precision']}% |\n")
            else:
                f.write(f"| {rn} | 0 | 0 | N/A |\n")

        # Bang timing
        all_changed = [r for r in rows if r.get("changed") == "True"]
        all_time_imps = []
        for r in all_changed:
            v = r.get("time_improvement_pct")
            if v and v != "None" and v != "":
                try:
                    all_time_imps.append(float(v))
                except (ValueError, TypeError):
                    pass

        f.write("\n## 4. Tong Hop Tat Ca Luat\n\n")
        f.write(f"| Metric | Gia tri |\n")
        f.write("|--------|---------|\n")
        f.write(f"| Tong cap danh gia | {len(rows)} |\n")
        f.write(f"| Tong query bi thay doi | {len(all_changed)} ({len(all_changed)/len(rows)*100:.1f}%) |\n")
        f.write(f"| Semantic correct | {len(all_sem)}/{len(all_changed)} ({len(all_sem)/len(all_changed)*100:.1f}%) |\n")
        f.write(f"| Winners | {len(all_winners)}/{len(all_changed)} ({len(all_winners)/len(all_changed)*100:.1f}%) |\n")
        if all_time_imps:
            f.write(f"| TB cai thien thoi gian | {statistics.mean(all_time_imps):+.2f}% |\n")
            f.write(f"| Median cai thien | {statistics.median(all_time_imps):+.2f}% |\n")
            f.write(f"| Max cai thien | {max(all_time_imps):+.2f}% |\n")
            f.write(f"| Min cai thien | {min(all_time_imps):+.2f}% |\n")

        # Ranking
        f.write("\n## 5. Bang Xep Hang Luat Theo Hieu Qua\n\n")
        f.write("| Hang | Luat | TB Thoi gian | Winner Rate | Changed Rate | Semantic Rate |\n")
        f.write("|------|------|-------------|-------------|--------------|--------------|\n")
        ranked = sorted(metrics.items(),
                       key=lambda x: (
                           x[1]['avg_time_improvement_pct'],
                           x[1]['winner_rate'],
                           x[1]['changed_rate']
                       ),
                       reverse=True)
        for rank, (rn, m) in enumerate(ranked, 1):
            f.write(f"| {rank} | {rn} | {m['avg_time_improvement_pct']:+.2f}% | "
                    f"{m['winner_rate']}% | {m['changed_rate']}% | {m['semantic_correct_rate']}% |\n")


if __name__ == "__main__":
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
    results_dir = os.path.join(base_dir, 'my_exp', 'results')
    generate_rule_report(results_dir)
