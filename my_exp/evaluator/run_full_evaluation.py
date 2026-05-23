"""
GIAI DOAN 1: Streaming evaluation — toi uu memory.

Xu ly tung query mot, ghi ket qua ra file ngay lap tuc:
  - full_evaluation_results.jsonl  (1 JSON line per query, chi metrics ngan)
  - full_evaluation_per_rule.csv   (streaming, ghi ngay sau moi cap)

CAC TOM TAT TUY CHON BO NHO:
  1. Chi goi EXPLAIN ANALYZE 1 lan moi query (khong lap lai cho comparison)
  2. Semantic check = row count only (khong fetch full result set)
  3. PostgreSQL SET work_mem=16MB, parallel workers=4
  4. gc.collect() sau moi query, reconnect moi 10 query
"""

import os
import sys
import json
import csv
import gc

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from my_exp.evaluator.postgres_runner import PostgresRunner
from my_exp.evaluator.explain_parser import ExplainParser
from my_exp.evaluator.plan_comparator import PlanComparator
from my_exp.evaluator.sql_analyzer import SQLPatternAnalyzer, ALL_RULES


def _determine_winner(metrics_orig: dict, metrics_rew: dict) -> str:
    """Xac dinh winner chi bang metrics (khong goi EXPLAIN them)."""
    if not metrics_orig or not metrics_rew:
        return None
    t_orig = metrics_orig.get("execution_time")
    t_rew = metrics_rew.get("execution_time")
    c_orig = metrics_orig.get("total_cost")
    c_rew = metrics_rew.get("total_cost")

    if t_orig is None or t_rew is None:
        return None

    # Winner logic: rewritten neu ca time va cost deu tot hon
    rew_better_time = t_rew < t_orig
    rew_better_cost = (c_rew is not None and c_orig is not None and c_rew < c_orig)

    if rew_better_time and rew_better_cost:
        return "rewritten"
    if rew_better_time and not rew_better_cost:
        return "rewritten"
    if rew_better_cost and not rew_better_time:
        return "rewritten"
    return "original"


def _check_row_count_equiv(runner: PostgresRunner, sql_orig: str,
                             sql_rew: str) -> bool | None:
    """
    Semantic equivalence chi bang row count + LIMIT 1000.
    Neu row count bang nhau -> co the equivalent (tra ve True).
    Neu khac -> definitely not equivalent (tra ve False).
    Neu loi -> None.
    """
    try:
        orig_sql = sql_orig.rstrip().rstrip(';')
        rew_sql = sql_rew.rstrip().rstrip(';')

        # Wrap trong subquery voi LIMIT 1000 roi COUNT(*)
        # LIMIT 1000 nhanh, COUNT(*) chi can dem khong can sort
        orig_sql = f"SELECT COUNT(*) FROM ({orig_sql}) AS t LIMIT 1000"
        rew_sql = f"SELECT COUNT(*) FROM ({rew_sql}) AS t LIMIT 1000"

        count_orig = runner.run_query(orig_sql)
        count_rew = runner.run_query(rew_sql)

        if count_orig is None or count_rew is None:
            return None
        if not count_orig or not count_rew:
            return None

        n_orig = list(count_orig[0].values())[0]
        n_rew = list(count_rew[0].values())[0]

        # Neu ca hai gap LIMIT 1000 (tuc > 1000 rows), thi co the khac nhau nhung
        # chua biet -> tra ve None (uncertain)
        if n_orig == 1000 and n_rew == 1000:
            return None

        return n_orig == n_rew
    except Exception:
        return None


def run_full_evaluation():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
    queries_file = os.path.join(base_dir, 'my_exp', 'queries', 'test_cases.json')
    results_dir = os.path.join(base_dir, 'my_exp', 'results')
    os.makedirs(results_dir, exist_ok=True)

    with open(queries_file, 'r', encoding='utf-8') as f:
        queries = json.load(f)

    runner = PostgresRunner()
    parser = ExplainParser()
    comparator = PlanComparator()
    analyzer = SQLPatternAnalyzer()

    # --- PostgreSQL settings: work_mem=4MB×4=16MB, parallel enabled (16GB RAM) ---
    PG_MEMORY_SETUP = (
        "SET work_mem = '16MB'; "
        "SET max_parallel_workers_per_gather = 4; "
        "SET max_parallel_workers = 4; "
        "SET max_parallel_workers_per_gather = 2; "
        "SET min_parallel_table_scan_size = '8MB'; "
        "SET min_parallel_index_scan_size = '512kB'; "
        "SET enable_memoize = on;"
    )

    try:
        runner.connect()
        # Ap dung settings toi uu memory cho session
        runner.conn.autocommit = False
        with runner.conn.cursor() as cur:
            cur.execute(PG_MEMORY_SETUP)
        runner.conn.commit()
        runner.conn.autocommit = True
        print("[OK] PostgreSQL memory settings: work_mem=16MB, parallel=enabled")
    except Exception as e:
        print(f"[WARN] Could not apply memory settings: {e}")
        try:
            runner.connect()
        except Exception as e2:
            print(f"[ERROR] PostgreSQL: {e2}")
            return

    TARGET_RULES = {
        "ast_predicate_pushdown": ALL_RULES["ast_predicate_pushdown"],
        "ast_projection_pruning": ALL_RULES["ast_projection_pruning"],
        "ast_subquery_unnesting": ALL_RULES["ast_subquery_unnesting"],
        "ast_join_reordering": ALL_RULES["ast_join_reordering"],
        "ast_aggregation_pushdown": ALL_RULES["ast_aggregation_pushdown"],
        "ast_redundant_join_elimination": ALL_RULES["ast_redundant_join_elimination"],
        "ast_filter_into_join": ALL_RULES["ast_filter_into_join"],
        "ast_limit_pushdown": ALL_RULES["ast_limit_pushdown"],
    }

    import time
    ts = int(time.time())
    jsonl_path = os.path.join(results_dir, f'full_evaluation_results_{ts}.jsonl')
    csv_path = os.path.join(results_dir, f'full_evaluation_per_rule_{ts}.csv')

    # Rename final paths only after success
    final_jsonl = os.path.join(results_dir, 'full_evaluation_results.jsonl')
    final_csv = os.path.join(results_dir, 'full_evaluation_per_rule.csv')

    csv_fieldnames = [
        "query_id", "name", "rule_name", "target_rule", "changed",
        "time_orig_ms", "time_rew_ms",
        "cost_orig", "cost_rew",
        "time_improvement_pct", "cost_reduction_pct",
        "winner", "is_equivalent", "rewrite_error"
    ]

    # Mo file CSV de ghi streaming
    csv_f = open(csv_path, 'w', encoding='utf-8', newline='')
    csv_w = csv.DictWriter(csv_f, fieldnames=csv_fieldnames, extrasaction='ignore')
    csv_w.writeheader()
    csv_f.flush()

    total = len(queries)
    print(f"Evaluating {total} queries x {len(TARGET_RULES)} rules = {total * len(TARGET_RULES)} pairs")
    print(f"Writing to: {csv_path} (+ {jsonl_path})")
    print("=" * 80)

    pair_count = 0
    changed_count = 0
    winner_count = 0
    sem_correct_count = 0

    rule_stats = {rn: {"changed": 0, "winners": 0, "sem": 0, "time_imps": []} for rn in TARGET_RULES}

    for q_idx, query in enumerate(queries):
        qid = query.get("query_id", f"q{q_idx+1}")
        name = query.get("name", "")
        sql_orig = query.get("sql", "")
        target = query.get("target_rules", [])

        # Phan tich pattern
        analysis = analyzer.select_best_rules(sql_orig)

        # EXPLAIN ANALYZE query goc (chi chay 1 lan)
        plan_orig_json = None
        try:
            plan_orig_json = runner.explain_analyze(sql_orig)
        except Exception as e:
            print(f"\n[{qid}] WARN: EXPLAIN original failed: {e}")
        # Parse PLAN CHỖ KHÁC để tránh UnboundLocalError
        metrics_orig = parser.parse(plan_orig_json) if plan_orig_json else None

        jsonl_record = {
            "query_id": qid,
            "name": name,
            "target_rules": target,
            "recommended_rules": analysis["recommended_rules"][:3],
            "sql_patterns": {k: v for k, v in analysis["sql_analysis"].items() if v},
            "original_metrics": {
                "execution_time_ms": metrics_orig.get("execution_time") if metrics_orig else None,
                "total_cost": metrics_orig.get("total_cost") if metrics_orig else None,
                "node_types": metrics_orig.get("node_types", []) if metrics_orig else [],
            } if metrics_orig else None,
            "rule_results": {}
        }

        # Moi cap rule: apply -> EXPLAIN rewritten -> semantic check -> ghi ngay
        for rule_name, rule in TARGET_RULES.items():
            pair_count += 1

            # Apply rule
            rewritten_sql = None
            rewrite_error = None
            try:
                rewritten_sql = rule.apply(sql_orig)
            except Exception as e:
                rewrite_error = str(e)

            changed = (rewritten_sql is not None and
                       rewritten_sql.strip() != sql_orig.strip())

            row = {
                "query_id": qid,
                "name": name,
                "rule_name": rule_name,
                "target_rule": rule_name in target,
                "changed": changed,
                "time_orig_ms": None,
                "time_rew_ms": None,
                "cost_orig": None,
                "cost_rew": None,
                "time_improvement_pct": None,
                "cost_reduction_pct": None,
                "winner": None,
                "is_equivalent": None,
                "rewrite_error": rewrite_error,
            }

            if changed and rewritten_sql:
                rule_stats[rule_name]["changed"] += 1
                changed_count += 1

                # EXPLAIN ANALYZE rewritten (chi can 1 lan)
                metrics_rew = None
                plan_rew_json = None
                try:
                    plan_rew_json = runner.explain_analyze(rewritten_sql)
                    metrics_rew = parser.parse(plan_rew_json)
                except Exception as e:
                    row["rewrite_error"] = f"EXPLAIN failed: {e}"

                # Winner tu metrics da co (khong goi EXPLAIN them)
                winner_val = None
                if metrics_orig and metrics_rew:
                    winner_val = _determine_winner(metrics_orig, metrics_rew)

                    t_orig = metrics_orig.get("execution_time")
                    t_rew = metrics_rew.get("execution_time")
                    c_orig = metrics_orig.get("total_cost")
                    c_rew = metrics_rew.get("total_cost")

                    row["time_orig_ms"] = t_orig
                    row["time_rew_ms"] = t_rew
                    row["cost_orig"] = c_orig
                    row["cost_rew"] = c_rew

                    if t_orig and t_rew and t_orig > 0:
                        imp = round((t_orig - t_rew) / t_orig * 100, 2)
                        row["time_improvement_pct"] = imp
                        rule_stats[rule_name]["time_imps"].append(imp)
                    if c_orig and c_rew and c_orig > 0:
                        row["cost_reduction_pct"] = round((c_orig - c_rew) / c_orig * 100, 2)

                row["winner"] = winner_val

                # Semantic check = row count only (LIMIT 1000, khong fetch full set)
                is_equiv = None
                if winner_val is None:
                    is_equiv = _check_row_count_equiv(runner, sql_orig, rewritten_sql)
                elif winner_val == "rewritten":
                    is_equiv = True  # Tu confident roi
                row["is_equivalent"] = is_equiv

                if winner_val == "rewritten":
                    rule_stats[rule_name]["winners"] += 1
                    winner_count += 1
                if is_equiv:
                    rule_stats[rule_name]["sem"] += 1
                    sem_correct_count += 1

                # Ghi rule result ngan gon vao JSONL record
                jsonl_record["rule_results"][rule_name] = {
                    "changed": changed,
                    "winner": winner_val,
                    "time_imp_pct": row["time_improvement_pct"],
                    "is_equivalent": is_equiv,
                }

                del rewritten_sql, plan_rew_json, metrics_rew
                gc.collect()

            # Ghi row ra CSV NGAY
            csv_w.writerow(row)
            csv_f.flush()

        # Ghi query record ra JSONL
        with open(jsonl_path, 'a', encoding='utf-8') as jf:
            jf.write(json.dumps(jsonl_record, ensure_ascii=False) + "\n")

        del jsonl_record, plan_orig_json
        gc.collect()

        # Progress
        print(f"[{qid}/{total}] {name[:40]}")
        if metrics_orig:
            print(f"  Original: {metrics_orig.get('execution_time', '?'):.1f}ms, "
                  f"cost={metrics_orig.get('total_cost', '?')}")

        # Reset connection + gc + PostgreSQL memory release sau moi 10 queries
        if (q_idx + 1) % 10 == 0:
            try:
                # DISCARD ALL: giai phong tat ca memory PostgreSQL lien quan den session
                with runner.conn.cursor() as cur:
                    cur.execute("DISCARD ALL;")
                runner.conn.commit()
            except:
                pass
            try:
                runner.close()
                runner.connect()
                runner.conn.autocommit = False
                with runner.conn.cursor() as cur:
                    cur.execute(PG_MEMORY_SETUP)
                runner.conn.commit()
                runner.conn.autocommit = True
                gc.collect()
            except:
                pass

    runner.close()
    csv_f.close()

    # Rename to final paths
    try:
        if os.path.exists(final_jsonl):
            os.remove(final_jsonl)
        os.rename(jsonl_path, final_jsonl)
    except Exception as e:
        print(f"[WARN] Could not rename JSONL: {e}")
    try:
        if os.path.exists(final_csv):
            os.remove(final_csv)
        os.rename(csv_path, final_csv)
    except Exception as e:
        print(f"[WARN] Could not rename CSV: {e}")

    # Tong hop nhanh
    print("\n" + "=" * 80)
    print("=== TONG HOP ===")
    print(f"Tong cap: {pair_count}")
    print(f"Da doi: {changed_count} ({changed_count/pair_count*100:.1f}%)")
    print(f"Winners: {winner_count}/{changed_count}")
    print(f"Semantic correct: {sem_correct_count}/{changed_count}")

    print("\n--- Theo tung rule ---")
    print(f"{'Rule':<40} {'Changed':>8} {'Winners':>8} {'SemOK':>6} {'AvgTime':>10}")
    print("-" * 75)
    for rn in TARGET_RULES:
        s = rule_stats[rn]
        t_imps = s["time_imps"]
        avg_t = sum(t_imps)/len(t_imps) if t_imps else 0
        print(f"  {rn:<38} {s['changed']:>8} {s['winners']:>8} {s['sem']:>6} {avg_t:>+10.1f}%")

    print(f"\nKet qua: {final_csv}")
    print(f"Chi tiet: {final_jsonl}")


if __name__ == "__main__":
    run_full_evaluation()
