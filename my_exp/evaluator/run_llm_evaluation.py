"""
GIAI DOAN 1b: LLM-based Rule Selection Evaluation.

Su dung Gemini (REST API) de goi y rule cho 35 test queries,
sau do danh gia nhu Giai doan 1 (KB evaluation).

Buoc 1: LLM goi y rules cho tung query
Buoc 2: Apply rule -> EXPLAIN ANALYZE -> semantic check -> winner
Buoc 3: Streaming write ra CSV + JSONL

So sanh voi KB (Giai doan 1):
  - KB: Pattern matching (14 features) -> rule scores -> top-K
  - LLM: Gemini/groq/anthropic phan tich SQL -> goi y rules

Output:
  - llm_evaluation_results.jsonl   (1 JSON/line, chi tiet per query)
  - llm_evaluation_per_rule.csv     (1 row/rule-query pair)
"""

import os
import sys
import json
import csv
import gc
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from dotenv import load_dotenv
load_dotenv()

from my_exp.evaluator.postgres_runner import PostgresRunner
from my_exp.evaluator.explain_parser import ExplainParser
from my_exp.evaluator.sql_analyzer import SQLPatternAnalyzer, ALL_RULES

# --- LLM Provider Selection ---
LLM_PROVIDER = os.environ.get("LLM_EVAL_PROVIDER", "groq").lower()
LLM_MODEL = os.environ.get("LLM_EVAL_MODEL", "llama-3.3-70b-versatile")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

# Gemini REST API endpoint
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"

# 8 AST rules available
AST_RULES = [
    "ast_predicate_pushdown",
    "ast_projection_pruning",
    "ast_subquery_unnesting",
    "ast_join_reordering",
    "ast_aggregation_pushdown",
    "ast_redundant_join_elimination",
    "ast_filter_into_join",
    "ast_limit_pushdown",
]

RULE_TO_CLASS = {rn: ALL_RULES[rn] for rn in AST_RULES}


def _build_llm_prompt(sql: str) -> str:
    """Xay dung prompt cho LLM de goi y rules.

    Original baseline prompt (88.6% accuracy on ground truth).
    """
    prompt = f"""Ban la chuyen gia toi uu SQL. Phan tich SQL va goi y cac rule toi uu.

RULES:
1. ast_predicate_pushdown     — Day WHERE tu query ngoai vao subquery
2. ast_projection_pruning    — Loai bo cot thua trong SELECT *
3. ast_subquery_unnesting    — Chuyen IN/EXISTS thanh JOIN
4. ast_join_reordering        — Sap xep lai thu tu JOINs
5. ast_aggregation_pushdown  — Day GROUP BY vao subquery
6. ast_redundant_join_elimination — Loai bo JOIN thua: JOIN chi de loc, cot JOIN khong dung o SELECT/query ngoai
7. ast_filter_into_join       — Chuyen WHERE loc theo bang trong JOIN vao ON, giu nguyen JOIN
8. ast_limit_pushdown         — Day LIMIT/OFFSET vao subquery

QUY TAC:
  - Chi tra ve JSON hop le, khong giai thich
  - "recommended_rules": list cac rule name (toi da 3)
  - "reasoning": giai thich ngan (1-2 cau)
  - Neu khong co rule nao phu hop: tra ve list rong

SQL QUERY:
{sql}

OUTPUT (JSON only, khong markdown):
{{
    "recommended_rules": ["ast_predicate_pushdown"],
    "reasoning": "Co WHERE tren subquery ngoai, co the day dieu kien vao."
}}
"""
    return prompt


def _call_gemini(prompt: str) -> dict:
    """Goi Gemini REST API."""
    model = LLM_MODEL or "gemini-2.0-flash"
    url = GEMINI_API_URL.format(model=model, key=GEMINI_API_KEY)
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.1,
            "topP": 0.8,
            "maxOutputTokens": 512,
        }
    }
    try:
        import requests
        resp = requests.post(url, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
        return _parse_llm_response(text)
    except Exception as e:
        print(f"    [GEMINI ERROR] {e}")
        return {"recommended_rules": [], "reasoning": f"API error: {e}"}


def _call_anthropic(prompt: str) -> dict:
    """Goi Anthropic Claude."""
    from anthropic import Anthropic
    model = LLM_MODEL or "claude-sonnet-4-20250514"
    client = Anthropic(api_key=ANTHROPIC_API_KEY)
    try:
        response = client.messages.create(
            model=model,
            max_tokens=512,
            temperature=0.1,
            messages=[{"role": "user", "content": prompt}]
        )
        text = response.content[0].text
        return _parse_llm_response(text)
    except Exception as e:
        print(f"    [ANTHROPIC ERROR] {e}")
        return {"recommended_rules": [], "reasoning": f"API error: {e}"}


def _call_groq(prompt: str) -> dict:
    """Goi Groq REST API (OpenAI-compatible endpoint) voi retry."""
    import requests as _requests
    import time as _time

    model = LLM_MODEL or "llama-3.3-70b-versatile"
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": 512,
    }
    for attempt in range(3):
        try:
            resp = _requests.post(url, headers=headers, json=payload, timeout=60)
            if resp.status_code == 429:
                wait = 2 ** attempt
                _time.sleep(wait)
                continue
            resp.raise_for_status()
            data = resp.json()
            text = data["choices"][0]["message"]["content"]
            return _parse_llm_response(text)
        except Exception as e:
            if attempt == 2:
                print(f"    [GROQ ERROR] {e}")
                return {"recommended_rules": [], "reasoning": f"API error: {e}"}
            _time.sleep(2 ** attempt)
    return {"recommended_rules": [], "reasoning": "Max retries exceeded"}


def _parse_llm_response(text: str) -> dict:
    """Parse JSON tu LLM response."""
    try:
        text = text.strip()
        # Strip markdown code blocks
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        parsed = json.loads(text)
        rules = parsed.get("recommended_rules", [])
        if isinstance(rules, str):
            rules = [rules]
        # Neu LLM tra ve rule cu (ko co ast_), thu map
        old_to_ast = {
            "predicate_pushdown": "ast_predicate_pushdown",
            "projection_pruning": "ast_projection_pruning",
            "subquery_unnesting": "ast_subquery_unnesting",
            "join_reordering": "ast_join_reordering",
            "aggregation_pushdown": "ast_aggregation_pushdown",
            "redundant_join_elimination": "ast_redundant_join_elimination",
            "filter_into_join": "ast_filter_into_join",
            "limit_pushdown": "ast_limit_pushdown",
        }
        mapped = []
        for r in rules:
            if r in AST_RULES:
                mapped.append(r)
            elif r in old_to_ast:
                mapped.append(old_to_ast[r])
        mapped = list(dict.fromkeys(mapped))  # remove dupes, keep order
        return {
            "recommended_rules": mapped[:3],
            "reasoning": parsed.get("reasoning", ""),
        }
    except Exception as e:
        return {"recommended_rules": [], "reasoning": f"Parse error: {e} | Raw: {text[:100]}"}


def _call_llm(prompt: str) -> dict:
    """Dispatch to the configured LLM provider."""
    if LLM_PROVIDER == "gemini":
        return _call_gemini(prompt)
    elif LLM_PROVIDER == "anthropic":
        return _call_anthropic(prompt)
    elif LLM_PROVIDER == "groq":
        # Supports any model: llama-3.3-70b-versatile, deepseek-chat, qwen-qwq-32b, etc.
        return _call_groq(prompt)
    else:
        return {"recommended_rules": [], "reasoning": f"Unknown provider: {LLM_PROVIDER}"}


def _determine_winner(metrics_orig: dict, metrics_rew: dict) -> str:
    """Xac dinh winner chi bang metrics."""
    if not metrics_orig or not metrics_rew:
        return None
    t_orig = metrics_orig.get("execution_time")
    t_rew = metrics_rew.get("execution_time")
    c_orig = metrics_orig.get("total_cost")
    c_rew = metrics_rew.get("total_cost")
    if t_orig is None or t_rew is None:
        return None
    if t_rew < t_orig or (c_rew is not None and c_orig is not None and c_rew < c_orig):
        return "rewritten"
    return "original"


def _check_row_count_equiv(runner: PostgresRunner, sql_orig: str,
                             sql_rew: str) -> bool | None:
    """Semantic equivalence chi bang row count LIMIT 1000."""
    try:
        orig_sql = sql_orig.rstrip().rstrip(';')
        rew_sql = sql_rew.rstrip().rstrip(';')
        orig_sql = f"SELECT COUNT(*) FROM ({orig_sql}) AS t LIMIT 1000"
        rew_sql = f"SELECT COUNT(*) FROM ({rew_sql}) AS t LIMIT 1000"
        count_orig = runner.run_query(orig_sql)
        count_rew = runner.run_query(rew_sql)
        if count_orig is None or count_rew is None:
            return None
        n_orig = list(count_orig[0].values())[0]
        n_rew = list(count_rew[0].values())[0]
        if n_orig == 1000 and n_rew == 1000:
            return None
        return n_orig == n_rew
    except Exception:
        return None


def run_llm_evaluation(dataset: str = "tpch", sample: int = 0):
    """Run LLM evaluation on a dataset.

    Args:
        dataset: 'tpch', 'dsb', or 'job'. Defaults to 'tpch'.
        sample: If > 0, only evaluate first N queries (for quick testing).
    """
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
    results_dir = os.path.join(base_dir, 'my_exp', 'results')
    os.makedirs(results_dir, exist_ok=True)

    # Load queries
    from my_exp.evaluator.dataset_loader import load_test_cases
    queries = load_test_cases(dataset)
    if sample > 0:
        queries = queries[:sample]
    if not queries:
        print(f"[ERROR] No queries found for dataset '{dataset}'")
        return

    runner = PostgresRunner(dataset)
    parser = ExplainParser()
    analyzer = SQLPatternAnalyzer()

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
        runner.conn.autocommit = False
        with runner.conn.cursor() as cur:
            cur.execute(PG_MEMORY_SETUP)
        runner.conn.commit()
        runner.conn.autocommit = True
        print(f"[OK] PostgreSQL memory settings applied")
    except Exception as e:
        print(f"[WARN] Could not apply memory settings: {e}")

    # Output paths — include dataset name
    ds_suffix = f"_{dataset}" if dataset != "tpch" else ""
    ts = int(time.time())
    jsonl_path = os.path.join(results_dir, f'llm_evaluation_results{ds_suffix}_{ts}.jsonl')
    csv_path = os.path.join(results_dir, f'llm_evaluation_per_rule{ds_suffix}_{ts}.csv')
    final_jsonl = os.path.join(results_dir, f'llm_evaluation_results{ds_suffix}.jsonl')
    final_csv = os.path.join(results_dir, f'llm_evaluation_per_rule{ds_suffix}.csv')

    csv_fieldnames = [
        "query_id", "name", "dataset", "rule_name", "llm_recommended",
        "changed", "time_orig_ms", "time_rew_ms",
        "cost_orig", "cost_rew",
        "time_improvement_pct", "cost_reduction_pct",
        "winner", "is_equivalent", "rewrite_error"
    ]

    csv_f = open(csv_path, 'w', encoding='utf-8', newline='')
    csv_w = csv.DictWriter(csv_f, fieldnames=csv_fieldnames, extrasaction='ignore')
    csv_w.writeheader()
    csv_f.flush()

    # LLM stats
    llm_call_times = []
    total_llm_calls = 0
    failed_llm_calls = 0

    print(f"\n{'='*80}")
    print(f"LLM EVALUATION — Provider: {LLM_PROVIDER.upper()}")
    if LLM_MODEL:
        print(f"Model: {LLM_MODEL}")
    print(f"{'='*80}")
    print(f"Queries: {len(queries)}")
    print(f"Output: {csv_path}")
    print(f"{'='*80}\n")

    # KB ground truth (from existing results)
    kb_results = {}
    kb_csv_path = os.path.join(results_dir, 'full_evaluation_per_rule.csv')
    if os.path.exists(kb_csv_path):
        with open(kb_csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                qid = row['query_id']
                if qid not in kb_results:
                    kb_results[qid] = {}
                rn = row['rule_name']
                kb_results[qid][rn] = row

    total = len(queries)
    pair_count = 0
    changed_count = 0
    winner_count = 0
    sem_correct_count = 0

    # Rule-level stats (for LLM recommended rules only)
    rule_stats = {rn: {"changed": 0, "winners": 0, "sem": 0, "time_imps": [], "recommended": 0}
                  for rn in AST_RULES}

    # KB agreement tracking
    kb_agreement = 0
    kb_disagreement = 0

    for q_idx, query in enumerate(queries):
        qid = query.get("query_id", f"q{q_idx+1}")
        name = query.get("name", "")
        sql_orig = query.get("sql", "")
        target = query.get("target_rules", [])

        # --- Step 1: LLM recommends rules ---
        if q_idx > 0:
            time.sleep(15)
        prompt = _build_llm_prompt(sql_orig)

        t0 = time.time()
        llm_result = _call_llm(prompt)
        llm_time = time.time() - t0
        llm_call_times.append(llm_time)
        total_llm_calls += 1
        if not llm_result.get("recommended_rules"):
            failed_llm_calls += 1

        recommended_rules = llm_result.get("recommended_rules", [])
        llm_reasoning = llm_result.get("reasoning", "")

        # KB recommended rules for comparison
        kb_analysis = analyzer.select_best_rules(sql_orig)
        kb_rules = kb_analysis["recommended_rules"][:3]

        # --- Agreement tracking ---
        overlap = set(recommended_rules) & set(kb_rules)
        if overlap:
            kb_agreement += 1
        else:
            kb_disagreement += 1

        # --- Step 2: EXPLAIN ANALYZE original (once per query) ---
        plan_orig_json = None
        try:
            plan_orig_json = runner.explain_analyze(sql_orig)
        except Exception as e:
            print(f"\n[{qid}] WARN: EXPLAIN original failed: {e}")
        metrics_orig = parser.parse(plan_orig_json) if plan_orig_json else None

        # JSONL record
        jsonl_record = {
            "query_id": qid,
            "name": name,
            "dataset": dataset,
            "llm_provider": LLM_PROVIDER,
            "llm_model": LLM_MODEL or "default",
            "target_rules": target,
            "llm_recommended_rules": recommended_rules,
            "llm_reasoning": llm_reasoning,
            "llm_call_time_ms": round(llm_time * 1000, 1),
            "kb_recommended_rules": kb_rules,
            "kb_llm_agreement": list(overlap),
            "original_metrics": {
                "execution_time_ms": metrics_orig.get("execution_time") if metrics_orig else None,
                "total_cost": metrics_orig.get("total_cost") if metrics_orig else None,
                "node_types": metrics_orig.get("node_types", []) if metrics_orig else [],
            } if metrics_orig else None,
            "rule_results": {}
        }

        # --- Step 3: Evaluate each LLM-recommended rule ---
        for rule_name in recommended_rules:
            if rule_name not in RULE_TO_CLASS:
                continue

            pair_count += 1
            rule_class = RULE_TO_CLASS[rule_name]
            rule_stats[rule_name]["recommended"] += 1

            rewritten_sql = None
            rewrite_error = None
            try:
                rewritten_sql = rule_class.apply(sql_orig)
            except Exception as e:
                rewrite_error = str(e)

            changed = (rewritten_sql is not None and
                       rewritten_sql.strip() != sql_orig.strip())

            # KB result for this (qid, rule_name) pair
            kb_pair = kb_results.get(qid, {}).get(rule_name, {})
            kb_winner = kb_pair.get("winner", "")
            kb_semantic = kb_pair.get("is_equivalent", "")

            row = {
                "query_id": qid,
                "name": name,
                "dataset": dataset,
                "rule_name": rule_name,
                "llm_recommended": True,
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

                metrics_rew = None
                try:
                    plan_rew_json = runner.explain_analyze(rewritten_sql)
                    metrics_rew = parser.parse(plan_rew_json)
                except Exception as e:
                    row["rewrite_error"] = f"EXPLAIN failed: {e}"

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

                is_equiv = None
                if winner_val is None:
                    is_equiv = _check_row_count_equiv(runner, sql_orig, rewritten_sql)
                elif winner_val == "rewritten":
                    is_equiv = True
                row["is_equivalent"] = is_equiv

                if winner_val == "rewritten":
                    rule_stats[rule_name]["winners"] += 1
                    winner_count += 1
                if is_equiv:
                    rule_stats[rule_name]["sem"] += 1
                    sem_correct_count += 1

                jsonl_record["rule_results"][rule_name] = {
                    "changed": changed,
                    "winner": winner_val,
                    "time_imp_pct": row["time_improvement_pct"],
                    "is_equivalent": is_equiv,
                    "kb_winner": kb_winner if kb_winner else None,
                    "kb_equivalent": kb_semantic if kb_semantic else None,
                }

                del rewritten_sql, plan_rew_json, metrics_rew
                gc.collect()

            csv_w.writerow(row)
            csv_f.flush()

        # Write JSONL
        with open(jsonl_path, 'a', encoding='utf-8') as jf:
            jf.write(json.dumps(jsonl_record, ensure_ascii=False) + "\n")

        # Progress
        rules_str = ", ".join(recommended_rules[:3]) if recommended_rules else "(none)"
        print(f"[{qid}/{total}] {name[:35]:<35} | LLM: {rules_str:<40} | KB: {', '.join(kb_rules[:2])}")
        if metrics_orig:
            print(f"  Orig: {metrics_orig.get('execution_time', 0):.1f}ms, "
                  f"LLM call: {llm_time:.1f}s")

        del jsonl_record, plan_orig_json
        gc.collect()

        # Reset connection every 10 queries
        if (q_idx + 1) % 10 == 0:
            try:
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
    for src, dst in [(jsonl_path, final_jsonl), (csv_path, final_csv)]:
        try:
            if os.path.exists(dst):
                os.remove(dst)
            os.rename(src, dst)
        except Exception as e:
            print(f"[WARN] Could not rename {src}: {e}")

    # Summary
    print(f"\n{'='*80}")
    print("=== LLM EVALUATION SUMMARY ===")
    print(f"Provider: {LLM_PROVIDER.upper()}")
    print(f"Total LLM calls: {total_llm_calls}")
    print(f"Failed LLM calls: {failed_llm_calls}")
    if llm_call_times:
        avg_llm = sum(llm_call_times) / len(llm_call_times)
        print(f"Avg LLM call time: {avg_llm:.1f}s")
    print(f"Total rule-query pairs evaluated: {pair_count}")
    print(f"Changed: {changed_count}")
    print(f"Winners: {winner_count}")
    print(f"Semantic correct: {sem_correct_count}")
    print(f"KB-LLM agreement: {kb_agreement}/{total} ({kb_agreement/total*100:.1f}%)")
    print(f"KB-LLM disagreement: {kb_disagreement}/{total} ({kb_disagreement/total*100:.1f}%)")

    print(f"\n--- Per-rule (LLM recommended only) ---")
    print(f"{'Rule':<40} {'Rec':>4} {'Changed':>7} {'Winners':>7} {'SemOK':>6} {'AvgTime':>10}")
    print("-" * 75)
    for rn in AST_RULES:
        s = rule_stats[rn]
        t_imps = s["time_imps"]
        avg_t = sum(t_imps)/len(t_imps) if t_imps else 0
        print(f"  {rn:<38} {s['recommended']:>4} {s['changed']:>7} "
              f"{s['winners']:>7} {s['sem']:>6} {avg_t:>+10.1f}%")

    print(f"\nOutput: {final_csv}")
    print(f"Detail: {final_jsonl}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="LLM-based rule selection evaluation")
    parser.add_argument("--dataset", default="tpch",
                        choices=["tpch", "dsb", "job"],
                        help="Dataset to evaluate on (default: tpch)")
    parser.add_argument("--sample", type=int, default=0,
                        help="Only evaluate first N queries (0=all, for quick testing)")
    args = parser.parse_args()
    run_llm_evaluation(dataset=args.dataset, sample=args.sample)
