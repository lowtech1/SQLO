# LLM-R2-Enhanced: Interactive SQL Optimization Advisor

He tro giai quyet SQL tuyen chon voi he co so tri thuc (Knowledge Base) va tro giup quyet dinh (Decision Support System).

---

## Kien truc He Thong

```
Nguoi dung nhap SQL
       |
       v
  [SQL Parser] --> Cay AST truc quan
       |
       v
  [SQL Analyzer] --> Feature extraction (tables, joins, subqueries, aggregates)
       |
       v
  [Rule Knowledge Base] --> 6 luat toi uu hoa
       |
       v
  [LLM / Pattern Selector] --> De xuat chuoi luat
       |
       v
  [Multi-Rewrite Engine] --> Sinh N candidates
       |
       v
  [Semantic Checker] --> Kiem tra tinh tuong duong
  [Plan Comparator]  --> So sanh execution plans
       |
       v
  [JSON Output] + [Streamlit UI] --> Ket qua truc quan
```

---

## Cau truc Du An

```
d:/DoAnTotNghiep/LLM-R2-1/
|--- my_exp/
|    |--- core/                    # Engine co so
|    |    |--- sql_parser.py       # SQL -> AST (sqlglot)
|    |    |--- sql_analyzer.py     # Feature extraction
|    |    |--- schema_loader.py   # Load schema dong
|    |    |--- multi_rewrite_engine.py  # Sinh N candidates
|    |    |--- run_tests.py       # 26 unit tests
|    |    |--- rules/             # 8 luat rewrite
|    |         |--- predicate_pushdown.py
|    |         |--- projection_pruning.py
|    |         |--- join_reordering.py
|    |         |--- subquery_unnesting.py
|    |         |--- aggregation_pushdown.py
|    |         |--- redundant_join_elimination.py
|    |         |--- filter_into_join.py
|    |         |--- limit_pushdown.py
|    |
|    |--- dss/                    # Decision Support System
|    |    |--- llm_rule_selector.py   # LLM + Pattern fallback
|    |    |--- semantic_checker.py    # Kiem tra tinh tuong duong
|    |    |--- plan_comparator.py      # So sanh EXPLAIN plans
|    |    |--- optimizer_pipeline.py   # Tong hop tat ca
|    |    |--- test_dss.py            # DSS tests
|    |
|    |--- ui/                     # Streamlit App
|    |    |--- app.py             # Main UI
|    |
|    |--- research_report.py      # Benchmark + Research Report
|    |--- evaluator/               # PostgreSQL tools
|    |--- queries/                # Test cases (TPC-H, DSB, JOB)
|
|--- archive/                     # File cu da duoc archive
|--- results/                     # Benchmark results
|--- SPEC.md                      # Specification day du
|--- requirements.txt
|--- run_app.py                   # Launcher script
```

---

## 6 Luat Trong Knowledge Base

| # | Ten | Mo ta | Cong thuc loi ich |
|---|-----|-------|-----------------|
| 1 | **Predicate Pushdown** | Day WHERE vao subquery | Rows_after = Rows × selectivity |
| 2 | **Projection Pruning** | Loai cot khong can thiet | I/O reduction = unused/total cols |
| 3 | **Join Reordering** | Sap xep lai thu tu JOIN | Intermediate_rows = Tich(kich thuoc) |
| 4 | **Subquery Unnesting** | Chuyen IN/EXISTS thanh JOIN | O(n×m) → O(n+m) |
| 5 | **Aggregation Pushdown** | Day GROUP BY xuong subquery | Rows_reduced = N / cardinality |
| 6 | **Redundant Join Elimination** | Loai bo JOIN du thua | Loai bo cost = hash + probe |

---

## Cai Dat

### 1. Cai dependencies

```bash
pip install sqlglot>=23.0.0
pip install psycopg2-binary
pip install anthropic
pip install streamlit
pip install pandas
pip install python-dotenv
```

Hoac:
```bash
pip install -r requirements.txt
```

### 2. Bien moi truong (neu su dung PostgreSQL)

```bash
export POSTGRES_DB=postgres
export POSTGRES_HOST=localhost
export POSTGRES_USER=postgres
export POSTGRES_PASSWORD=your_password

# Neu su dung LLM
export ANTHROPIC_API_KEY=sk-ant-...
```

Tao file `.env` trong thu muc goc:
```
POSTGRES_DB=postgres
POSTGRES_HOST=localhost
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password
ANTHROPIC_API_KEY=sk-ant-...
```

---

## Cach Chay

### Chay Streamlit UI (truc quan, de su dung nhat)

```bash
cd d:/DoAnTotNghiep/LLM-R2-1
streamlit run my_exp/ui/app.py
```

Hoac:
```bash
python run_app.py
```

**Noi dung UI:**
- Tab AST & Flow: Cay AST truc quan + luong toi uu hoa
- Tab Chi Tiet: Phan tich tung buoc, luat de xuat, chi tiet candidates
- Tab So Sanh: SQL goc vs rewrite, bang so sanh
- Tab JSON Output: Ket qua JSON day du theo format yeu cau

### Chay Research Benchmark

```bash
python run_app.py benchmark
```

Sinh:
- `results/benchmarks/benchmark_<timestamp>.json` - Du lieu so lieu
- `results/research/report_<timestamp>.md` - Bao cao nguyen cu

### Chay Unit Tests

```bash
python run_app.py tests    # Rule tests (26/26)
python run_app.py dss     # DSS tests
python run_app.py all     # Tat ca
```

Hoac truc tiep:
```bash
python my_exp/core/run_tests.py
python my_exp/dss/test_dss.py
```

---

## Vi Du Sử Dụng

### Vi du 1: Predicate Pushdown

```sql
SELECT a, b FROM (SELECT a, b, c FROM t) AS sub WHERE a > 10
```
**Phan tich:**
- Co subquery trong FROM
- Co WHERE ngoai tren subquery
- Subquery khong co DISTINCT/GROUP BY/AGG

**Luat duoc de xuat:** Predicate Pushdown
**SQL sau khi rewrite:**
```sql
SELECT a, b FROM (SELECT a, b, c FROM t WHERE a > 10) AS sub
```

### Vi du 2: Subquery Unnesting

```sql
SELECT c_name FROM customer WHERE c_custkey IN (
    SELECT o_custkey FROM orders WHERE o_totalprice > 100000
)
```
**Luat duoc de xuat:** Subquery Unnesting
**Loi ich:** Nested Loop O(n×m) → Hash Join O(n+m)

### Vi du 3: Multiple JOINs

```sql
SELECT * FROM orders o
JOIN lineitem l ON o.id = l.o_id
JOIN nation n ON o.n_id = n.id
WHERE o.total > 10000
```
**Luat duoc de xuat:** Join Reordering, Filter Into Join

---

## JSON Output Format

Khi nhap SQL, he thong tra ve JSON theo format:

```json
{
  "thought_process": {
    "ast_analysis": "SQL co 2 bang, 1 JOIN, 1 subquery. Do phuc tap: Trung binh.",
    "conflict_resolution": "SUBQUERY_UNNESTING phai chay truoc JOIN_REORDERING de mo duong."
  },
  "optimization_sequence": [
    {
      "step": 1,
      "rule_name": "Chuyen Subquery Thanh JOIN",
      "trigger_reason": "IN subquery trong WHERE",
      "why_this_order": "Don gian hoa cau truc truoc khi toi uu JOIN",
      "expected_benefit": "Nested Loop → Hash Join, giam O(n×m) thanh O(n+m)"
    },
    {
      "step": 2,
      "rule_name": "Day Dieu Kien Loc Xuong",
      "trigger_reason": "WHERE tren subquery sau khi unnest",
      "why_this_order": "Giam so dong trung gian truoc",
      "expected_benefit": "Giảm rows = N × selectivity"
    }
  ],
  "confidence_score": 0.95,
  "best_rewrite": "...",
  "rewritten_sql": "..."
}
```

---

## Tu Dien Luat (Rule KB)

| Luật | Khi nao ap dung? | Khi nao KHONG ap dung? |
|------|----------------|----------------------|
| Predicate Pushdown | WHERE tren subquery, subquery don gian | Subquery co DISTINCT, GROUP BY, hoac AGG |
| Projection Pruning | SELECT * hoac cot thua | Tat ca cot deu can thiet |
| Join Reordering | 2+ INNER JOINs | LEFT/RIGHT/FULL OUTER JOINs |
| Subquery Unnesting | IN/EXISTS subquery don gian | NOT IN, correlated subquery |
| Aggregation Pushdown | GROUP BY tren subquery, khong HAVING | HAVING, DISTINCT aggregate |
| Redundant Join Elimination | JOIN ma bang khong duoc dung | OUTER JOIN, co aggregate |

---

## Research Report

Chay benchmark de tao bao cao nguyen cu:

```bash
python my_exp/research_report.py
```

Hoac tu Streamlit: Tai file JSON tu tab JSON Output.

---

## Thu Tu Chuoi Luat (Chain of Thought)

He thong tu dong xac dinh thu tu toi uu:

```
1. SUBQUERY_UNNESTING  --> Don gian hoa, mo duong cho luat khac
2. PREDICATE_PUSHDOWN   --> Giam so dong trung gian
3. JOIN_REORDERING      --> Sau khi subquery da don gian
4. AGGREGATION_PUSHDOWN --> Day GROUP BY xuong truoc JOIN
5. PROJECTION_PRUNING   --> Loai cot thua cuoi cung
6. REDUNDANT_JOIN_ELIMINATION --> Loai JOIN du thua truoc cuoi
```

**Nguyen tac:** Don gian truoc, giam kich thuoc giua, cua cung la cuoi.

---

## Gioi han Hien Tai

1. **Chiem dung PostgreSQL** - Semantic checker va plan comparator chi ho tro PostgreSQL
2. **API key cho LLM** - Neu khong co ANTHROPIC_API_KEY, he thong tu dong fallback ve pattern-based
3. **Chi 8 rules** - Chua cover day du SQL optimization landscape
4. **Khong co Cost Model** - Phu thuoc vao PostgreSQL optimizer

---

## Huong Phat Trien

1. Mo rong nhieu DB: MySQL, SQLite, SQL Server
2. Them nhieu rules: CTE optimization, window function
3. Learned cost model: Thay vi phu thuoc vao DB optimizer
4. Fine-tuned LLM: Chuyen biet cho SQL optimization
5. Cross-DB benchmark: Danh gia tren nhieu DBMS khac nhau
