"""
my_exp.research_report
====================
Research report generator for LLM-R2-Enhanced.
Generates comprehensive research documentation with metrics, comparisons,
and ablation studies for thesis/dissertation.
"""

import sys, os
# Add project root to path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, PROJECT_ROOT)

import json
import time
from datetime import datetime
from typing import Optional

from my_exp.core.rules import RULE_METADATA, get_all_rules
from my_exp.core.sql_analyzer import SQLFeatureExtractor
from my_exp.core.multi_rewrite_engine import MultiRewriteEngine
from my_exp.dss.optimizer_pipeline import OptimizationPipeline


# ============================================================
# Test Queries from Multiple Datasets
# ============================================================

TPC_H_QUERIES = [
    {
        "id": "TPCH-Q1",
        "query": """SELECT l_returnflag, l_linestatus, SUM(l_quantity) AS sum_qty,
        SUM(l_extendedprice) AS sum_base_price, SUM(l_extendedprice*(1-l_discount)) AS sum_disc_price,
        SUM(l_extendedprice*(1-l_discount)*(1+l_tax)) AS sum_charge, AVG(l_quantity) AS avg_qty,
        AVG(l_extendedprice) AS avg_price, AVG(l_discount) AS avg_disc, COUNT(*) AS count_order
        FROM lineitem WHERE l_shipdate <= DATE '1998-12-01' - INTERVAL '90 days'
        GROUP BY l_returnflag, l_linestatus ORDER BY l_returnflag, l_linestatus""",
        "description": "TPC-H Q1: Pricing Summary Report",
        "expected_rules": ["aggregation_pushdown", "projection_pruning"],
    },
    {
        "id": "TPCH-Q3",
        "query": """SELECT l_orderkey, SUM(l_extendedprice*(1-l_discount)) AS revenue, o_orderdate, o_shippriority
        FROM customer c JOIN orders o ON c.c_custkey = o.o_custkey
        JOIN lineitem l ON o.o_orderkey = l.l_orderkey
        WHERE c.c_mktsegment = 'AUTOMOBILE' AND o.o_orderdate < DATE '1995-03-15' AND l.l_shipdate > DATE '1995-03-15'
        GROUP BY l_orderkey, o_orderdate, o_shippriority ORDER BY revenue DESC, o_orderdate LIMIT 10""",
        "description": "TPC-H Q3: Shipping Priority",
        "expected_rules": ["filter_into_join", "join_reordering"],
    },
    {
        "id": "TPCH-Q5",
        "query": """SELECT n_name, SUM(l_extendedprice*(1-l_discount)) AS revenue
        FROM customer c JOIN orders o ON c.c_custkey = o.o_custkey
        JOIN lineitem l ON o.o_orderkey = l.l_orderkey JOIN supplier s ON l.l_suppkey = s.s_suppkey
        JOIN nation n ON c.c_nationkey = n.n_nationkey JOIN region r ON n.n_regionkey = r.r_regionkey
        WHERE r.r_name = 'ASIA' AND o.o_orderdate >= DATE '1994-01-01' AND o.o_orderdate < DATE '1995-01-01'
        GROUP BY n_name ORDER BY revenue DESC""",
        "description": "TPC-H Q5: Local Supplier Volume",
        "expected_rules": ["filter_into_join", "join_reordering", "projection_pruning"],
    },
    {
        "id": "TPCH-Q10",
        "query": """SELECT c_custkey, c_name, SUM(l_extendedprice*(1-l_discount)) AS revenue, c_acctbal,
        n_name, c_address, c_phone, c_comment
        FROM customer c JOIN nation n ON c.c_nationkey = n.n_nationkey
        JOIN orders o ON c.c_custkey = o.o_custkey JOIN lineitem l ON o.o_orderkey = l.l_orderkey
        WHERE o.o_orderdate >= DATE '1993-10-01' AND o.o_orderdate < DATE '1994-01-01'
        AND l.l_returnflag = 'R' GROUP BY c_custkey, c_name, c_acctbal, n_name, c_address, c_phone, c_comment
        ORDER BY revenue DESC LIMIT 20""",
        "description": "TPC-H Q10: Returned Item Reporting",
        "expected_rules": ["filter_into_join", "projection_pruning"],
    },
    {
        "id": "TPCH-Q17",
        "query": """SELECT SUM(l_extendedprice) / 7.0 AS avg_yearly
        FROM lineitem l2 JOIN part p ON l2.l_partkey = p.p_partkey
        WHERE p.p_brand = 'Brand#23' AND p.p_container = 'MED BOX'
        AND l2.l_quantity < (SELECT 0.2 * AVG(l_quantity) FROM lineitem WHERE l_partkey = p.p_partkey)""",
        "description": "TPC-H Q17: Small-Quantity-Order Revenue",
        "expected_rules": ["subquery_unnesting", "predicate_pushdown"],
    },
]

DSB_QUERIES = [
    {
        "id": "DSB-Q1",
        "query": """SELECT d_weeknuminyear, d_year, d_moy, SUM(cs_net_paid_inc_ship_tax) AS total_net_paid
        FROM catalog_sales cs JOIN date_dim d ON cs.cs_sold_date_sk = d.d_date_sk
        WHERE d.d_date BETWEEN '1999-01-01' AND '1999-12-31'
        GROUP BY d_weeknuminyear, d_year, d_moy
        ORDER BY d_year, d_weeknuminyear, d_moy""",
        "description": "DSB: Catalog Sales Summary",
        "expected_rules": ["filter_into_join"],
    },
    {
        "id": "DSB-Q2",
        "query": """SELECT c_customer_id, c_first_name, c_last_name, SUM(ss_quantity) AS total_qty
        FROM store_sales ss JOIN customer c ON ss.ss_customer_sk = c.c_customer_sk
        WHERE ss.ss_sold_date_sk BETWEEN 2451182 AND 2451547
        GROUP BY c_customer_id, c_first_name, c_last_name
        ORDER BY total_qty DESC LIMIT 100""",
        "description": "DSB: Customer Purchase Summary",
        "expected_rules": ["filter_into_join", "join_reordering"],
    },
    {
        "id": "DSB-Q3",
        "query": """SELECT w_warehouse_name, i_item_id, SUM(w_warehouse_sq ft) AS warehouse_sqft,
        SUM(i_item_sk) AS item_count
        FROM inventory inv JOIN warehouse w ON inv.inv_warehouse_sk = w.w_warehouse_sk
        JOIN item i ON inv.inv_item_sk = i.i_item_sk
        WHERE inv.inv_date BETWEEN '1999-01-01' AND '1999-03-31'
        GROUP BY w_warehouse_name, i_item_id
        ORDER BY warehouse_sqft DESC""",
        "description": "DSB: Warehouse Inventory",
        "expected_rules": ["filter_into_join"],
    },
]

JOB_QUERIES = [
    {
        "id": "JOB-Q1",
        "query": """SELECT MIN(title.year) AS first_movie_year, MAX(title.year) AS last_movie_year,
        MIN(info.info) AS movie_info, COUNT(DISTINCT title.id) AS num_movies
        FROM title JOIN movie_info_idx AS info ON title.id = info.movie_id
        JOIN cast_info AS ci ON title.id = ci.movie_id
        WHERE info.info_type_id = 100 AND title.kind_id <= 2
        AND ci.person_id IN (SELECT id FROM name WHERE name LIKE '%Spielberg%')""",
        "description": "JOB: Spielberg Movies",
        "expected_rules": ["predicate_pushdown", "projection_pruning"],
    },
    {
        "id": "JOB-Q2",
        "query": """SELECT title.id, title.title, title.production_year
        FROM title JOIN movie_companies AS mc ON title.id = mc.movie_id
        JOIN company_name AS cn ON mc.company_id = cn.id
        WHERE cn.country_code != '[pl]' AND mc.note LIKE '%(200%)%'
        ORDER BY title.production_year, title.title LIMIT 100""",
        "description": "JOB: Company Productions",
        "expected_rules": ["filter_into_join", "projection_pruning"],
    },
    {
        "id": "JOB-Q3",
        "query": """SELECT t.title, ct.kind, ch.name, ch.id AS char_id, n.name AS actor_name, n.id AS actor_id,
        t.id AS movie_id
        FROM char_name AS ch JOIN cast_info AS ci ON ch.id = ci.person_role_id
        JOIN name AS n ON ci.person_id = n.id
        JOIN title AS t ON ci.movie_id = t.id
        JOIN company_type AS ct ON ci.movie_companies IS NOT NULL
        WHERE t.production_year > 2005 AND n.gender = 'm'
        ORDER BY t.production_year, char_id LIMIT 50""",
        "description": "JOB: Actor Roles",
        "expected_rules": ["projection_pruning", "join_reordering"],
    },
]


# ============================================================
# Benchmark Runner
# ============================================================

def run_benchmark(
    use_llm: bool = False,
    max_candidates: int = 5,
    datasets: list = None,
) -> dict:
    """
    Run comprehensive benchmark across all test queries.
    Returns benchmark results with metrics.
    """
    if datasets is None:
        datasets = {
            "TPC-H": TPC_H_QUERIES,
            "DSB": DSB_QUERIES,
            "JOB": JOB_QUERIES,
        }

    pipeline = OptimizationPipeline(use_llm=use_llm)
    extractor = SQLFeatureExtractor()
    all_rules = get_all_rules()

    results = {
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "use_llm": use_llm,
            "max_candidates": max_candidates,
            "datasets": list(datasets.keys()),
            "total_queries": sum(len(qs) for qs in datasets.values()),
        },
        "dataset_results": {},
        "rule_stats": {},
        "summary": {},
    }

    # Initialize rule stats
    for rule_name in RULE_METADATA:
        results["rule_stats"][rule_name] = {
            "times_applied": 0,
            "times_correct": 0,
            "queries_eligible": 0,
            "rewrite_changed": 0,
        }

    all_rule_recalls = []
    all_rule_precisions = []

    for dataset_name, queries in datasets.items():
        dataset_results = {
            "queries": [],
            "stats": {
                "total": len(queries),
                "parsed": 0,
                "rule_accuracies": {},
                "avg_candidates": 0.0,
                "avg_rules_detected": 0.0,
            }
        }

        for q in queries:
            q_result = {
                "query_id": q["id"],
                "description": q["description"],
                "original_sql": q["query"],
            }

            try:
                # Feature extraction
                features = extractor.extract(q["query"])
                q_result["parsing_success"] = features.get("parsing", {}).get("success", False)

                if not q_result["parsing_success"]:
                    continue

                q_result["complexity"] = features.get("complexity", {})
                q_result["features"] = {
                    "tables": features.get("table_count", 0),
                    "joins": features.get("join_count", 0),
                    "subqueries": features.get("subquery_count", 0),
                    "has_aggregation": features.get("has_aggregation", False),
                }

                # Rule recommendation
                recs = pipeline.select_rules(q["query"])
                q_result["method"] = recs.get("method", "pattern")
                recommended_rules = {r["rule"] for r in recs.get("recommendations", [])}

                # Expected rules
                expected_rules = set(q.get("expected_rules", []))
                q_result["expected_rules"] = list(expected_rules)
                q_result["recommended_rules"] = list(recommended_rules)

                # Accuracy metrics
                # Recall: how many expected rules were recommended
                if expected_rules:
                    recall = len(recommended_rules & expected_rules) / len(expected_rules)
                    q_result["rule_recall"] = recall
                    all_rule_recalls.append(recall)
                else:
                    q_result["rule_recall"] = None

                # Precision: how many recommended rules were correct
                if recommended_rules:
                    if expected_rules:
                        precision = len(recommended_rules & expected_rules) / len(recommended_rules)
                    else:
                        precision = 0.0
                    q_result["rule_precision"] = precision
                    all_rule_precisions.append(precision)
                else:
                    q_result["rule_precision"] = None

                # Candidates
                candidates = pipeline.generate_rewrites(q["query"], max_candidates=max_candidates)
                q_result["num_candidates"] = len(candidates)
                q_result["num_rewrite_candidates"] = sum(1 for c in candidates if c.get("changed"))
                q_result["candidates"] = [
                    {
                        "id": c["id"],
                        "rules": c["rules_applied"],
                        "changed": c["changed"],
                    }
                    for c in candidates
                ]

                # Update rule stats
                for rule_name, meta in RULE_METADATA.items():
                    if rule_name in recommended_rules:
                        results["rule_stats"][rule_name]["times_applied"] += 1
                    if rule_name in expected_rules:
                        results["rule_stats"][rule_name]["queries_eligible"] += 1
                        if rule_name in recommended_rules:
                            results["rule_stats"][rule_name]["times_correct"] += 1

                for c in candidates:
                    for rule_name in c.get("rules_applied", []):
                        if c.get("changed"):
                            results["rule_stats"][rule_name]["rewrite_changed"] += 1

                dataset_results["stats"]["parsed"] += 1
                dataset_results["queries"].append(q_result)

            except Exception as e:
                q_result["error"] = str(e)
                dataset_results["queries"].append(q_result)

        # Compute dataset stats
        total = dataset_results["stats"]["total"]
        parsed = dataset_results["stats"]["parsed"]
        recalls = [q["rule_recall"] for q in dataset_results["queries"]
                   if q.get("rule_recall") is not None]
        precisions = [q["rule_precision"] for q in dataset_results["queries"]
                      if q.get("rule_precision") is not None]

        dataset_results["stats"]["avg_rule_recall"] = sum(recalls) / len(recalls) if recalls else 0.0
        dataset_results["stats"]["avg_rule_precision"] = sum(precisions) / len(precisions) if precisions else 0.0
        dataset_results["stats"]["avg_candidates"] = sum(
            q.get("num_candidates", 0) for q in dataset_results["queries"]
        ) / max(parsed, 1)
        dataset_results["stats"]["avg_rules_detected"] = sum(
            len(q.get("recommended_rules", [])) for q in dataset_results["queries"]
        ) / max(parsed, 1)
        dataset_results["stats"]["parse_rate"] = parsed / max(total, 1)

        results["dataset_results"][dataset_name] = dataset_results

    # Compute overall summary
    all_recalls = all_rule_recalls
    all_precisions = all_rule_precisions

    results["summary"] = {
        "avg_rule_recall": sum(all_recalls) / len(all_recalls) if all_recalls else 0.0,
        "avg_rule_precision": sum(all_precisions) / len(all_precisions) if all_precisions else 0.0,
        "total_queries": sum(ds["stats"]["total"] for ds in results["dataset_results"].values()),
        "total_parsed": sum(ds["stats"]["parsed"] for ds in results["dataset_results"].values()),
        "total_candidates_generated": sum(
            sum(q.get("num_candidates", 0) for q in ds["queries"])
            for ds in results["dataset_results"].values()
        ),
        "total_rewrite_candidates": sum(
            sum(q.get("num_rewrite_candidates", 0) for q in ds["queries"])
            for ds in results["dataset_results"].values()
        ),
        "rule_stats": results["rule_stats"],
    }

    return results


def generate_research_report(benchmark_results: dict, output_path: str = None) -> str:
    """Generate a comprehensive research report in Markdown format."""

    meta = benchmark_results["metadata"]
    summary = benchmark_results["summary"]
    ds_results = benchmark_results["dataset_results"]

    report = f"""# Research Report: LLM-R2-Enhanced
## Interactive SQL Optimization Advisor

**Generated:** {meta['timestamp']}
**Method:** {"LLM-Guided" if meta['use_llm'] else "Pattern-Based"}
**Datasets:** {', '.join(meta['datasets'])}
**Total Queries:** {meta['total_queries']}

---

## 1. Executive Summary

He thong LLM-R2-Enhanced duoc danh gia tren {meta['total_queries']} queries
tu {len(meta['datasets'])} datasets: {', '.join(meta['datasets'])}.

| Metric | Value |
|--------|-------|
| Total Queries | {summary['total_queries']} |
| Parsed Successfully | {summary['total_parsed']} |
| Parse Rate | {summary['total_parsed']/max(summary['total_queries'],1)*100:.1f}% |
| Avg Rule Recall | {summary['avg_rule_recall']*100:.1f}% |
| Avg Rule Precision | {summary['avg_rule_precision']*100:.1f}% |
| Total Candidates Generated | {summary['total_candidates_generated']} |
| Rewrite Candidates | {summary['total_rewrite_candidates']} |

---

## 2. Dataset-Level Results

"""

    for ds_name, ds_data in ds_results.items():
        stats = ds_data["stats"]
        report += f"""### 2.{list(ds_results.keys()).index(ds_name)+1} {ds_name}

| Metric | Value |
|--------|-------|
| Total Queries | {stats['total']} |
| Parsed | {stats['parsed']} ({stats['parse_rate']*100:.1f}%) |
| Avg Rule Recall | {stats['avg_rule_recall']*100:.1f}% |
| Avg Rule Precision | {stats['avg_rule_precision']*100:.1f}% |
| Avg Candidates/Query | {stats['avg_candidates']:.1f} |
| Avg Rules Detected/Query | {stats['avg_rules_detected']:.1f} |

**Query Details:**

| Query ID | Description | Complexity | Tables | Joins | Recall | Precision | Candidates | Rewrite |
|----------|-------------|------------|--------|-------|--------|-----------|------------|--------|
"""

        for q in ds_data["queries"]:
            if q.get("error"):
                continue
            recall = f"{q['rule_recall']*100:.0f}%" if q.get("rule_recall") is not None else "N/A"
            precision = f"{q['rule_precision']*100:.0f}%" if q.get("rule_precision") is not None else "N/A"
            complexity = q.get("complexity", {}).get("level", "N/A")
            features = q.get("features", {})
            report += f"| {q['query_id']} | {q['description'][:30]}... | {complexity} | {features.get('tables', 0)} | {features.get('joins', 0)} | {recall} | {precision} | {q.get('num_candidates', 0)} | {q.get('num_rewrite_candidates', 0)} |\n"

        report += "\n"

    report += """---

## 3. Rule-Level Statistics

| Rule | Times Recommended | Eligible Queries | Correct | Precision | Rewrite Changed |
|------|------------------|------------------|---------|-----------|----------------|
"""

    rule_stats = summary.get("rule_stats", {})
    for rule_name, meta in RULE_METADATA.items():
        stats = rule_stats.get(rule_name, {})
        times_rec = stats.get("times_applied", 0)
        eligible = stats.get("queries_eligible", 0)
        correct = stats.get("times_correct", 0)
        prec = f"{correct/max(times_rec,1)*100:.1f}%" if times_rec > 0 else "N/A"
        rewrite = stats.get("rewrite_changed", 0)
        report += f"| {meta.get('name_vi', rule_name)} | {times_rec} | {eligible} | {correct} | {prec} | {rewrite} |\n"

    report += """
---

## 4. Rule Definitions & Expected Benefits

### 4.1 Predicate Pushdown (Đẩy Điều Kiện Lọc Xuống)

**Mục tiêu:** Di chuyển WHERE từ query ngoài vào subquery trong FROM clause.

**Công thức lợi ích:**
```
Rows_after = Rows_before × selectivity(filter)
```

**Điều kiện an toàn:**
- Subquery không có DISTINCT
- Subquery không có GROUP BY
- Subquery không có aggregate (SUM/COUNT/AVG/MIN/MAX)
- Cột trong WHERE tồn tại trong inner projection

**Tại sao hiệu quả:** Giảm số dòng trung gian. Predicate selectivity càng thấp (filter chọn lọc càng cao) thì lợi ích càng lớn.

---

### 4.2 Projection Pruning (Loại Bỏ Cột Thừa)

**Mục tiêu:** Loại bỏ các cột không sử dụng trong SELECT.

**Công thức lợi ích:**
```
I/O_reduction = (unused_columns / total_columns) × 100%
```

**Điều kiện an toàn:** Cột bỏ không xuất hiện trong WHERE, GROUP BY, ORDER BY của subquery.

---

### 4.3 Join Reordering (Thay Đổi Thứ Tự JOIN)

**Mục tiêu:** Sắp xếp lại thứ tự JOIN để đặt bảng nhỏ hoặc bảng có filter nhiều lên trước.

**Công thức lợi ích:**
```
Intermediate_rows = Π(kích thước bảng giữa 2 JOIN)
```

**Thuật toán:** Greedy heuristic dựa trên kích thước bảng + filter selectivity.

**Điều kiện:** Chỉ INNER JOIN (không LEFT/RIGHT/FULL/CROSS).

---

### 4.4 Subquery Unnesting (Chuyển Subquery Thành JOIN)

**Mục tiêu:** Chuyển IN/EXISTS subquery thành JOIN để dùng Hash Join thay vì Nested Loop.

**Công thức lợi ích:**
```
Nested Loop: O(n × m) thời gian
Hash Join:   O(n + m) thời gian
```

**Điều kiện an toàn:**
- Subquery không correlated
- Subquery chỉ có 1 bảng
- Không phải NOT IN

---

### 4.5 Aggregation Pushdown (Đẩy Phép Tổng Hợp Xuống)

**Mục tiêu:** Đẩy GROUP BY/aggregate từ query ngoài vào subquery.

**Công thức lợi ích:**
```
Rows_reduced = N / cardinality(GROUP BY keys)
```

**Điều kiện:** Outer không có HAVING, không có DISTINCT aggregate.

---

### 4.6 Redundant Join Elimination (Loại Bỏ JOIN Dư Thừa)

**Mục tiêu:** Loại bỏ JOIN mà bảng được JOIN không được sử dụng.

**Công thức:**
```
Loại bỏ nếu: col(joined_table) ∉ (SELECT ∪ WHERE ∪ GROUP ∪ ORDER)
```

---

### 4.7 Filter Into Join (Đẩy Filter Vào JOIN)

**Mục tiêu:** Di chuyển WHERE filter vào JOIN ON clause.

**Công thức lợi ích:**
```
Rows_join = Rows × selectivity(filter)
```

---

### 4.8 Limit Pushdown (Đẩy LIMIT Xuống)

**Mục tiêu:** Đẩy LIMIT/OFFSET xuống subquery để tránh sort toàn bộ.

**Công thức lợi ích:**
```
Sort_rows_after = MIN(LIMIT, N) vs Sort_rows_before = N
Tiết kiệm: O(N log N) - O(LIMIT log LIMIT)
```

---

## 5. Research Gap Analysis

### Gap 1: Hardcoded KB không Generalizable

**Vấn đề hiện tại:** KB gán rules cho từng dataset cụ thể qua pattern matching cứng.

**Hướng giải quyết:** Dùng LLM làm rule selector thay vì pattern matching cứng.
LLM phân tích SQL AST → xác định optimization opportunities → đề xuất rules phù hợp dựa trên semantic.

**Validation:** KB động hoạt động với bất kỳ schema nào mà không cần hardcoded mapping.

### Gap 2: Thiếu Interactive What-If Analysis

**Vấn đề hiện tại:** Hệ thống chỉ xuất ra bảng số liệu, không cho phép user tương tác.

**Hướng giải quyết:** Hệ thống suggestion-driven: user nhập SQL → LLM đề xuất N candidates → user chọn hoặc điều chỉnh.

**Validation:** Multi-candidate generation với explanations, plan comparison, semantic verification.

### Gap 3: Không có Semantic Correctness Verification

**Vấn đề hiện tại:** Rewrite được apply nhưng không có cơ chế xác nhận kết quả có tương đương semantic.

**Hướng giải quyết:** Semantic checker chạy cả original và rewrite trên sample data → compare results.

**Validation:** Automated equivalence check với confidence score.

### Gap 4: Thiếu Explainability

**Vấn đề hiện tại:** LLM chỉ trả về rule names, không giải thích TẠI SAO.

**Hướng giải quyết:** Mỗi rule suggestion đi kèm: trigger reason, expected benefit, confidence score.

**Validation:** Human-readable explanations cho mỗi rule application.

---

## 6. Comparative Analysis

### So sánh với Nghiên cứu Liên quan

| Khía cạnh | LLM-R2 (Original) | LLM-R2-Enhanced (New) | Research Gap |
|---|---|---|---|
| Rule selection | Pattern matching cứng | LLM phân tích SQL semantics | → Generalizes beyond training |
| Output | Bảng số liệu thống kê | Interactive multi-candidate | → User-in-the-loop |
| Correctness | Không verify | Semantic equivalence check | → Automated validation |
| Explainability | Không có | Rule explanations + confidence | → Explainable AI |
| Schema dependency | Gắn dataset cụ thể | Schema-agnostic (đọc động) | → Generalizable optimization |
| Rewrite candidates | Single rewrite | N candidates với comparison | → What-if analysis |

### Research Contributions

1. **Dynamic Knowledge Base:** KB hoạt động với bất kỳ schema nào, không phụ thuộc dataset cụ thể.
2. **Interactive What-If:** User có thể thử N candidate rewrites trước khi commit.
3. **Explainable Rules:** Mỗi rule suggestion có explanation bằng ngôn ngữ tự nhiên.
4. **Semantic Verification:** Tự động verify correctness của mỗi rewrite.
5. **Multi-Candidate Generation:** Nhiều candidate rewrites với đầy đủ metadata.

---

## 7. Limitations & Future Work

### Limitations

1. **LLM API Dependency:** Khi không có API key, hệ thống fall back về pattern-based selection.
2. **PostgreSQL Only:** Semantic checker và plan comparator hiện chỉ hỗ trợ PostgreSQL.
3. **Limited Rule Coverage:** 8 rules chỉ cover một phần của SQL optimization landscape.
4. **No Cost Model:** Không có learned cost model — phụ thuộc vào PostgreSQL optimizer.
5. **Cross-DB Generalization:** Chưa test trên MySQL, Oracle, SQL Server.

### Future Work

1. **Multi-DB Support:** Mở rộng semantic checker và plan comparator cho MySQL, SQLite.
2. **Learned Cost Model:** Tích hợp learned cost estimation thay vì phụ thuộc DB optimizer.
3. **More Rules:** Thêm rules như: Common Table Expression optimization, Window function optimization.
4. **RAG for Rewrite Examples:** Xây dựng rewrite example pool cho retrieval-augmented generation.
5. **Fine-tuned LLM:** Fine-tune một LLM chuyên biệt cho SQL optimization.
6. **Cross-DB Benchmark:** Đánh giá trên nhiều DBMS khác nhau.

---

## 8. Conclusion

He thong LLM-R2-Enhanced mang lai:

1. **Knowledge Base động** — hoạt động với bất kỳ schema nào, không hardcode
2. **Interactive Advisor** — user nhập SQL, nhận N candidates với explanations
3. **Semantic Verification** — tự động kiểm tra tính đúng đắn của rewrites
4. **Explainable AI** — mỗi rule suggestion có TẠI SAO và LỢI ÍCH
5. **Research-Grade Metrics** — báo cáo nghiên cứu đầy đủ với benchmark results

---

*Report generated by LLM-R2-Enhanced Research Report Generator*
"""

    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"Report saved to: {output_path}")

    return report


# ============================================================
# Ablation Study
# ============================================================

def run_ablation_study():
    """
    Compare Pattern-based vs LLM-based rule selection.
    """
    print("\n" + "=" * 70)
    print("ABLATION STUDY: Pattern-Based vs LLM-Based")
    print("=" * 70)

    all_queries = TPC_H_QUERIES + DSB_QUERIES + JOB_QUERIES
    extractor = SQLFeatureExtractor()

    results = {"pattern": {}, "llm": {}}

    for method, use_llm in [("pattern", False), ("llm", True)]:
        pipeline = OptimizationPipeline(use_llm=use_llm)
        recalls, precisions = [], []

        for q in all_queries:
            try:
                features = extractor.extract(q["query"])
                if not features.get("parsing", {}).get("success"):
                    continue

                recs = pipeline.select_rules(q["query"])
                recommended = {r["rule"] for r in recs.get("recommendations", [])}
                expected = set(q.get("expected_rules", []))

                if expected:
                    recall = len(recommended & expected) / len(expected)
                    recalls.append(recall)

                if recommended:
                    precision = len(recommended & expected) / len(recommended) if expected else 0
                    precisions.append(precision)
            except Exception as e:
                pass

        results[method]["recall"] = sum(recalls) / len(recalls) if recalls else 0
        results[method]["precision"] = sum(precisions) / len(precisions) if precisions else 0
        results[method]["n_queries"] = len(recalls)

    print(f"\nPattern-Based: Recall={results['pattern']['recall']*100:.1f}%, "
          f"Precision={results['pattern']['precision']*100:.1f}%")
    print(f"LLM-Based: Recall={results['llm']['recall']*100:.1f}%, "
          f"Precision={results['llm']['precision']*100:.1f}%")

    return results


# ============================================================
# Main
# ============================================================

if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

    print("\n" + "#" * 70)
    print("#  LLM-R2 RESEARCH BENCHMARK")
    print("#" * 70)

    # Run benchmark
    print("\nRunning benchmark...")
    benchmark_results = run_benchmark(use_llm=False, max_candidates=5)

    # Save results
    results_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "results", "benchmarks", f"research_benchmark_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )
    os.makedirs(os.path.dirname(results_path), exist_ok=True)
    with open(results_path, 'w', encoding='utf-8') as f:
        json.dump(benchmark_results, f, indent=2, ensure_ascii=False)
    print(f"Benchmark results saved to: {results_path}")

    # Generate report
    report_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "results", "research", f"research_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    )
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    report = generate_research_report(benchmark_results, output_path=report_path)
    print(f"Research report saved to: {report_path}")

    # Ablation study
    ablation_results = run_ablation_study()

    print("\n" + "#" * 70)
    print("#  BENCHMARK COMPLETE")
    print("#" * 70)
    print(f"\nFiles generated:")
    print(f"  - {results_path}")
    print(f"  - {report_path}")
