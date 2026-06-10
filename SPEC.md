# LLM-R2-Enhanced: Interactive SQL Optimization Advisor
## Project Specification — v2.0

> **Vision:** A true "Interactive Database Workspace & Optimization Dashboard" that connects users directly to their live database, visualizes schema structure, executes queries with live results, and provides transparent, explainable SQL optimization through a Knowledge-Based Decision Support System.

---

## 1. Project Overview

**Project Name:** LLM-R2-Enhanced — Interactive SQL Optimization Knowledge-Based Decision Support System

**Core Functionality:** A web-based workspace that connects to a live PostgreSQL database, allows users to write and execute SQL queries, visualizes the schema structure and query execution plans, analyzes SQL queries through AST-based feature extraction, recommends optimization rules from a dynamic Knowledge Base, generates multiple rewrite candidates with explanations, verifies semantic equivalence, and presents results in a transparent interactive dashboard where users can see exactly *what* changed, *why* rules were applied, and *how* the database responds.

**Target Users:** Database administrators, developers, researchers, and anyone who needs to optimize SQL queries without deep knowledge of query optimization theory.

**Key Distinction from v1.0:**
- v1.0: User pastes a single SQL string into a text area — disconnected from any database context
- v2.0: User connects to a live database, browses schema visually, writes queries in an interactive editor, executes them to see real results, and triggers optimization on those live queries with real plan comparisons

---

## 2. Architecture Overview (v2.0)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                              USER LAYER                                       │
│                                                                              │
│  ┌─────────────────────────┐  ┌──────────────────────────────────────────┐  │
│  │  LEFT PANEL (250px)    │  │           MAIN WORKSPACE                  │  │
│  │                         │  │  ┌──────────────────────────────────────┐ │  │
│  │  ┌─────────────────┐   │  │  │  QUERY EDITOR (CodeMirror-style)   │ │  │
│  │  │ Schema Explorer  │   │  │  │  - SQL syntax highlighting          │ │  │
│  │  │ - Tables tree    │   │  │  │  - Auto-complete from schema        │ │  │
│  │  │ - Columns        │   │  │  │  - Execute button [▶ Run]          │ │  │
│  │  │ - FK/PK links    │   │  │  │  - Sample data preview (100 rows)  │ │  │
│  │  └─────────────────┘   │  │  └──────────────────────────────────────┘ │  │
│  │  ┌─────────────────┐   │  │  ┌──────────────────────────────────────┐ │  │
│  │  │ KB Directory     │   │  │  │  OPTIMIZATION OUTPUT (Tabs)         │ │  │
│  │  │ - Rules tree    │   │  │  │  [AST & Flow] [Steps] [Compare]     │ │  │
│  │  │ - Applied vs    │   │  │  │  [JSON] [Schema] [History]           │ │  │
│  │  │   Available     │   │  │  │                                      │ │  │
│  │  └─────────────────┘   │  │  │  - Rule cards with explanations      │ │  │
│  │  ┌─────────────────┐   │  │  │  - Before/After SQL side-by-side     │ │  │
│  │  │ System Status    │   │  │  │  - Execution plan trees               │ │  │
│  │  │ - DB connected  │   │  │  │  - Semantic check results             │ │  │
│  │  │ - LLM ready    │   │  │  └──────────────────────────────────────┘ │  │
│  │  └─────────────────┘   │  │                                            │  │
│  └─────────────────────────┘  └──────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────────┘

                            ↓ All panels update reactively ↓

┌──────────────────────────────────────────────────────────────────────────────┐
│                    DECISION SUPPORT LAYER (DSS)                               │
│                                                                              │
│  ┌────────────────┐  ┌────────────────┐  ┌──────────────────────────────────┐ │
│  │ LLM Rule      │  │ Multi-Version │  │ Semantic Equivalence            │ │
│  │ Selector       │  │ Rewrite Engine │  │ Checker                         │ │
│  │ (Claude API)  │  │ (N candidates) │  │ (PostgreSQL + Row Compare)     │ │
│  └────────────────┘  └────────────────┘  └──────────────────────────────────┘ │
│  ┌────────────────┐  ┌────────────────┐  ┌──────────────────────────────────┐ │
│  │ Plan           │  │ Rule          │  │ Research Report                  │ │
│  │ Comparator    │  │ Explainer     │  │ Generator                       │ │
│  │ (EXPLAIN ANALYZE)│             │  │                                │ │
│  └────────────────┘  └────────────────┘  └──────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│                       CORE ENGINE LAYER                                        │
│                                                                              │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────────────────────┐  │
│  │ Schema Loader  │  │ SQL Analyzer  │  │ Rule Knowledge Base            │  │
│  │ (PostgreSQL + │  │ (sqlglot AST) │  │ (6 rules, dynamic, explainable)│  │
│  │  JSON/PG info_schema)│            │  │                                │  │
│  └────────────────┘  └────────────────┘  └────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────────────────┐    │
│  │  6 Rewrite Rules (safe, ordered, explainable)                        │    │
│  │  1. Predicate Pushdown     4. Subquery Unnesting                  │    │
│  │  2. Projection Pruning     5. Aggregation Pushdown                  │    │
│  │  3. Join Reordering         6. Redundant Join Elimination          │    │
│  └──────────────────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│                    INFRASTRUCTURE LAYER                                        │
│  ┌──────────────────┐  ┌──────────────────────────────────────────────┐   │
│  │ PostgreSQL       │  │ Anthropic Claude API                        │   │
│  │ (pg_catalog +   │  │ (Rule Selection + Natural Language           │   │
│  │  information_schema)│  │  Explanations + Chain-of-Thought)          │   │
│  └──────────────────┘  └──────────────────────────────────────────────┘   │
│  ┌──────────────────┐  ┌──────────────────────────────────────────────┐   │
│  │ TPC-H / DSB /JOB│  │ JSON Schema Configs                          │   │
│  │ Test Datasets    │  │ (user-provided schema definitions)           │   │
│  └──────────────────┘  └──────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. UI/UX Layout Specification (v2.0)

### 3.1 Overall Layout

The application uses a **2-column workspace layout** with a collapsible left panel and a responsive main area:

```
┌─────────────┬──────────────────────────────────────────────────────────────┐
│  LEFT       │  MAIN WORKSPACE                                             │
│  PANEL      │                                                             │
│  (250px)    │  ┌─────────────────────────────────────────────────────┐  │
│             │  │  TOOLBAR: [▶ Execute] [💡 Optimize] [🗑 Clear] [⚙]  │  │
│ ┌─────────┐ │  └─────────────────────────────────────────────────────┘  │
│ │🔌 DB    │ │  ┌─────────────────────────────────────────────────────┐  │
│ │ Status  │ │  │                                                      │  │
│ └─────────┘ │  │  QUERY EDITOR (top 40%)                            │  │
│ ┌─────────┐ │  │  - SQL syntax highlighting                           │  │
│ │📊 Schema│ │  │  - Line numbers                                     │  │
│ │ Explorer│ │  │  - Schema auto-complete                              │  │
│ │         │ │  │  - Error markers for invalid SQL                     │  │
│ │ ├─t1    │ │  │                                                      │  │
│ │ │ ├─col1│ │  └─────────────────────────────────────────────────────┘  │
│ │ │ ├─col2│ │  ┌─────────────────────────────────────────────────────┐  │
│ │ └─t2    │ │  │                                                      │  │
│ │   ├─col1│ │  │  OPTIMIZATION OUTPUT (bottom 60%)                   │  │
│ └─────────┘ │  │  ┌─[AST & Flow]─[Steps]─[Compare]─[JSON]─────────┐ │  │
│ ┌─────────┐ │  │  │                                                  │ │  │
│ │📚 KB    │ │  │  Tab content here                                  │ │  │
│ │ Rules   │ │  │                                                  │ │  │
│ │         │ │  │                                                  │ │  │
│ │ ├─PP    │ │  │                                                  │ │  │
│ │ ├─Proj  │ │  │                                                  │ │  │
│ │ └─JOIN  │ │  └──────────────────────────────────────────────────┘ │  │
│ └─────────┘ │  └─────────────────────────────────────────────────────┘  │
│ ┌─────────┐ │                                                             │
│ │📁 Files │ │  ┌─────────────────────────────────────────────────────┐  │
│ │ Project │ │  │  RESULTS PANEL (collapsible, 200px)                │  │
│ │ Struct  │ │  │  - Original query result preview                     │  │
│ └─────────┘ │  │  - Rewritten query result preview                     │  │
└─────────────┴──────────────────────────────────────────────────────────────┘
```

### 3.2 Left Panel Components

#### 3.2.1 Database Connection Status
- Connection indicator (green/red dot)
- Current database name
- Connected user
- Table count
- Quick disconnect/reconnect button

#### 3.2.2 Schema Explorer (Tree View)
- Expandable tree: **Database → Schema → Tables → Columns**
- Each column shows: name, data type, PK/FK badge
- Each table shows: row count estimate, column count
- Foreign key relationships shown as connecting lines or badges
- Click on table → inserts `SELECT * FROM table LIMIT 100` into editor
- Click on column → inserts column name into editor at cursor
- Search/filter box at top of panel
- Right-click context menu: "Preview table", "Copy name", "Generate SELECT"

#### 3.2.3 KB Directory (Knowledge Base Tree)
- Tree view of all 6 optimization rules
- Each rule shows: name, benefit level (colored dot), applicability status
- When analyzing a query: applied rules highlighted green, available rules blue, not-applicable grayed
- Click on rule → opens rule detail card
- Expand rule → shows: description, preconditions, trigger keywords, example

#### 3.2.4 System Status
- LLM connection status (Ready / Fallback / Disconnected)
- PostgreSQL connection
- Active query history count
- Memory/cache usage (optional)

### 3.3 Main Workspace: Query Editor

- **Code editor** with SQL syntax highlighting (using `st.text_area` enhanced with CodeMirror via `streamlit-elements` or custom HTML/JS, or fallback to `streamlit-code` patterns)
- **Toolbar buttons:**
  - `[▶ Run]` — Execute query against live DB, show results in bottom panel
  - `[💡 Optimize]` — Run optimization pipeline on current query
  - `[🗑 Clear]` — Clear editor
  - `[⚙ Settings]` — Open settings panel
- **Auto-completion:** As user types, suggest table names and column names from loaded schema
- **Sample data preview:** After running, show first 100 rows in a scrollable table below editor
- **Execution time:** Show actual execution time after running
- **Query history:** Dropdown of recent queries (session state)

### 3.4 Main Workspace: Optimization Output (Tabs)

#### Tab 1: AST & Flow (Visual)
- **Query Flow Diagram:** Visual representation of the optimization pipeline
  - Node 1: Input SQL (code block)
  - Arrow: "Parse →"
  - Node 2: AST Tree (collapsible, color-coded by node type)
  - Arrow: "Analyze →"
  - Node 3: Feature Vector (tables, joins, subqueries, complexity score)
  - Arrow: "Rules Detected →"
  - Node 4: Rule Sequence (cards showing each rule with confidence)
  - Arrow: "Rewrite →"
  - Node 5: Output SQL (side-by-side: before / after)
- **AST Tree Visualization:** sqlglot AST rendered as interactive tree
  - Color-coded nodes: SELECT=blue, JOIN=orange, WHERE=yellow, FROM=green, SUBQUERY=purple
  - Click node to expand/collapse
  - Hover for details (data type, alias, etc.)

#### Tab 2: Step-by-Step Analysis
- **Step cards** — one per optimization step, showing:
  - Step number with rule name
  - Trigger reason (what in the SQL triggered this rule)
  - Why this order (explanation of rule sequencing)
  - Expected benefit (quantified where possible)
  - Safety checks (what was verified before applying)
  - Warning if any (semantic change risk, etc.)
- **Each step expandable** to show:
  - SQL before this step
  - SQL after this step
  - Difference highlighted

#### Tab 3: Plan Comparison
- **Side-by-side execution plan trees:**
  - Left: Original query plan (tree view)
  - Right: Rewritten query plan (tree view)
- **Plan metrics table:**
  | Metric | Original | Rewritten | Change |
  |--------|----------|-----------|--------|
  | Total Cost | 500.0 | 120.0 | -76% |
  | Est. Rows | 10000 | 1000 | -90% |
  | Exec Time (ms) | 45.5 | 12.2 | -73% |
- **Node-by-node comparison:** Expandable rows for each plan node

#### Tab 4: Semantic Verification
- **Equivalence check results** for each candidate:
  - Green checkmark + "Semantically Equivalent" (confidence %)
  - Red X + "Not Equivalent" + reason
- **Row count comparison:** Original vs rewritten row counts
- **Sample data diff:** Show first 10 differing rows (if any)

#### Tab 5: JSON Output
- Full JSON response in copyable code block
- Download button (`.json` file)
- Collapsible sections for each major key

#### Tab 6: Schema Info
- Shows loaded schema details for current database
- Table list with row estimates
- Relationship diagram (optional, for small schemas)

### 3.5 Bottom Panel: Query Results

- Scrollable data table (first 100 rows)
- Column headers with data types
- Row count and execution time
- Export options: CSV, copy

### 3.6 Interaction Model

```
User Action                          System Response
─────────────────────────────────────────────────────────────────
Connect to DB (sidebar)        →  Load schema → Populate Schema Explorer
Click table in explorer        →  Insert SELECT INTO editor
Click [▶ Run]                   →  Execute on DB → Show results below editor
Click [💡 Optimize]             →  Run pipeline → Show all 6 tabs
Click rule in KB tree          →  Open rule detail card
Click step card                →  Expand to show before/after SQL
Hover over AST node             →  Show tooltip with details
Click "Download JSON"           →  Download optimization result
Switch query in history         →  Reload query into editor
```

### 3.7 Color System & Visual Language

| Element | Color | Hex |
|---------|-------|-----|
| Primary (headers, buttons) | Deep Blue | #1e3a5f |
| Success / Equivalent | Green | #28a745 |
| Warning / Medium benefit | Orange | #fd7e14 |
| Error / Not Equivalent | Red | #dc3545 |
| Info / Low benefit | Blue | #17a2b8 |
| JOIN nodes | Orange | #fd7e14 |
| WHERE nodes | Yellow | #ffc107 |
| FROM nodes | Green | #28a745 |
| SELECT nodes | Blue | #1e3a5f |
| SUBQUERY nodes | Purple | #6f42c1 |
| Rule Applied (KB tree) | Green | #28a745 |
| Rule Available (KB tree) | Blue | #17a2b8 |
| Rule Not Applicable (KB tree) | Gray | #6c757d |

---

## 4. Six Core Rewrite Rules (Knowledge Base)

All rules are defined with full metadata for the Knowledge Base. Rules are numbered 1-6 to match the 6 rules specified in the research proposal.

### Rule 1: Predicate Pushdown (Đẩy điều kiện lọc xuống)
- **ID:** KB-001
- **Mục tiêu:** Đẩy WHERE từ query ngoài vào subquery trong FROM clause
- **Trigger patterns:** `WHERE on outer query + subquery in FROM`, `WHERE on subquery alias`
- **Điều kiện an toàn:**
  - Subquery không có DISTINCT
  - Subquery không có GROUP BY hoặc aggregate
  - Tất cả cột trong WHERE tồn tại trong inner projection
- **Công thức lợi ích:** `Rows_sau = Rows_truoc × selectivity(filter)`
- **Rủi ro:** Thấp (low) — an toàn nếu preconditions được kiểm tra
- **Ví dụ:**
  - Input: `SELECT a FROM (SELECT a,b FROM t) AS sub WHERE a > 10`
  - Output: `SELECT a FROM (SELECT a,b FROM t WHERE a > 10) AS sub`

### Rule 2: Projection Pruning (Loại bỏ cột không cần thiết)
- **ID:** KB-002
- **Mục tiêu:** Loại bỏ cột không sử dụng khỏi SELECT
- **Trigger patterns:** `SELECT *`, `unused columns in subquery projection`
- **Điều kiện an toàn:** Cột bỏ không xuất hiện trong WHERE, GROUP BY, ORDER BY của subquery
- **Công thức lợi ích:** `I/O giảm = (cot_bỏ / tong_cot) × bandwidth_reduction`
- **Rủi ro:** Thấp (low)
- **Ví dụ:**
  - Input: `SELECT c_name FROM (SELECT * FROM customer) AS sub`
  - Output: `SELECT c_name FROM (SELECT c_name FROM customer) AS sub`

### Rule 3: Join Reordering (Thay đổi thứ tự JOIN)
- **ID:** KB-003
- **Mục tiêu:** Đặt bảng nhỏ trước bảng lớn trong JOIN chain
- **Trigger patterns:** `2+ JOINs in sequence`, `JOIN chain without ordering`
- **Điều kiện:** Chỉ INNER JOIN; không LEFT/RIGHT/FULL/CROSS
- **Thuật toán:** Greedy heuristic dựa trên row count estimates từ information_schema
- **Công thức lợi ích:** `Intermediate_rows = Tích(kich_thuoc_bang_giua_2_JOIN)`
- **Rủi ro:** Trung bình (medium) — phụ thuộc vào accuracy của row estimates

### Rule 4: Subquery Unnesting (Chuyển subquery thành JOIN)
- **ID:** KB-004
- **Mục tiêu:** Chuyển IN/EXISTS subquery thành JOIN để dùng Hash Join
- **Trigger patterns:** `IN (SELECT ...)`, `EXISTS (SELECT ...)`
- **Điều kiện an toàn:**
  - Subquery không correlated
  - Không phải NOT IN (NULL handling phức tạp)
  - Subquery chỉ có 1 bảng
- **Công thức lợi ích:** `Nested Loop O(n×m) → Hash Join O(n+m)`
- **Rủi ro:** Trung bình (medium) — cần verify semantic equivalence
- **Ví dụ:**
  - Input: `SELECT * FROM t1 WHERE t1.id IN (SELECT t2.id FROM t2)`
  - Output: `SELECT DISTINCT t1.* FROM t1 JOIN (SELECT DISTINCT id FROM t2) _sq ON t1.id=_sq.id`

### Rule 5: Aggregation Pushdown (Đẩy phép tổng hợp xuống)
- **ID:** KB-005
- **Mục tiêu:** Đẩy GROUP BY từ query ngoài vào subquery
- **Trigger patterns:** `GROUP BY over subquery`, `aggregate on subquery result`
- **Điều kiện an toàn:**
  - Outer không có HAVING
  - Outer không có DISTINCT aggregate
  - Inner không có GROUP BY/LIMIT/OFFSET sẵn
- **Công thức lợi ích:** `Rows_sau = Rows_truoc / cardinality(group_keys)`
- **Rủi ro:** Trung bình (medium)

### Rule 6: Redundant Join Elimination (Loại bỏ JOIN dư thừa)
- **ID:** KB-006
- **Mục tiêu:** Loại bỏ JOIN mà bảng được JOIN không được sử dụng
- **Trigger patterns:** `JOIN without referencing joined table columns in SELECT/WHERE/GROUP`
- **Điều kiện an toàn:**
  - Không phải OUTER/LEFT/RIGHT/FULL JOIN
  - Bảng JOIN thực sự không được tham chiếu ở đâu
- **Công thức:** `Loại bỏ nếu: col(joined_table) ∉ SELECT ∪ WHERE ∪ GROUP ∪ ORDER`
- **Rủi ro:** Thấp (low) — an toàn nếu column usage được kiểm tra kỹ
- **Ví dụ:**
  - Input: `SELECT a.x FROM t1 a JOIN t2 b ON a.id = b.id WHERE a.x > 10`
  - Output: `SELECT a.x FROM t1 a WHERE a.x > 10`

---

## 5. LLM Integration Strategy

### Strategy 1: Pattern-Based (Baseline — No API Key Required)
- Dùng regex + AST analysis để detect rule triggers
- Score mỗi rule theo heuristic confidence
- Fallback khi LLM không khả dụng

### Strategy 2: LLM-Guided (Claude Opus 4.6)
- Phân tích SQL bằng LLM với full AST context
- LLM đề xuất top-3 rules với confidence score
- LLM giải thích Chain-of-Thought: TẠI SAO chọn rule này, THỨ TỰ ra sao, LỢI ÍCH gì
- Mỗi suggestion đi kèm: rule name, trigger reason, expected benefit, confidence, warning

### Strategy 3: Multi-Candidate Generation
- Tạo N candidate rewrites (individual rules + rule combinations)
- Mỗi candidate có: rewritten SQL, rules applied, plan comparison, semantic check

---

## 6. Decision Support Output Format

```json
{
  "query_id": "uuid",
  "original_sql": "SELECT ...",
  "db_connection": {
    "database": "dsb",
    "host": "localhost",
    "tables_queried": ["customer", "orders"],
    "total_rows_accessed": 125000
  },
  "thought_process": {
    "ast_analysis": "SQL co 2 bang, 1 JOIN, 1 subquery IN. Do phuc tap: Phuc tap.",
    "conflict_resolution": "SUBQUERY_UNNESTING phai chay truoc de don gian cau truc. JOIN_REORDERING chay sau khi subquery da unnest. PROJECTION_PRUNING chay cuoi de loai cot thua."
  },
  "optimization_sequence": [
    {
      "step": 1,
      "rule_name": "Subquery Unnesting",
      "rule_id": "KB-004",
      "trigger_reason": "IN (SELECT ...) trong WHERE clause",
      "why_this_order": "Phai don gian hoa cau truc truoc — chuyen IN subquery thanh JOIN de mo duong cho luat tiep theo",
      "expected_benefit": "Nested Loop O(n×m) -> Hash Join O(n+m), giam tu 5000ms xuong 200ms",
      "safety_checks_passed": ["Subquery khong correlated", "Chi 1 bang trong subquery", "Khong phai NOT IN"],
      "warnings": null,
      "sql_before": "SELECT ... WHERE c_custkey IN (SELECT o_custkey FROM orders ...)",
      "sql_after": "SELECT ... FROM customer c JOIN (SELECT DISTINCT o_custkey FROM orders ...) _sq ON c.c_custkey = _sq.o_custkey"
    },
    {
      "step": 2,
      "rule_name": "Predicate Pushdown",
      "rule_id": "KB-001",
      "trigger_reason": "WHERE sau subquery sau khi unnest",
      "why_this_order": "Sau khi unnest, WHERE co the day xuong bang don vi",
      "expected_benefit": "Giam rows = N × selectivity(filter)",
      "safety_checks_passed": ["Subquery khong co DISTINCT", "Khong co GROUP BY"],
      "warnings": null,
      "sql_before": "SELECT ... FROM customer WHERE c_mktsegment = 'AUTOMOBILE'",
      "sql_after": "SELECT ... FROM (SELECT * FROM customer WHERE c_mktsegment = 'AUTOMOBILE') AS c"
    }
  ],
  "candidates": [
    {
      "id": 0,
      "is_original": true,
      "rules_applied": [],
      "sql": "SELECT ...",
      "execution_plan": { "total_cost": 500.0, "estimated_time_ms": 45.5 },
      "semantic_check": { "equivalent": true, "confidence": 1.0 },
      "result_rows": 1234
    },
    {
      "id": 1,
      "is_original": false,
      "rules_applied": ["KB-004", "KB-001"],
      "sql": "SELECT ...",
      "execution_plan": { "total_cost": 120.0, "estimated_time_ms": 12.2 },
      "semantic_check": { "equivalent": true, "confidence": 0.98 },
      "result_rows": 1234,
      "improvement_pct": 76.0
    }
  ],
  "recommendation": {
    "best_candidate_id": 1,
    "confidence": 0.92,
    "reasoning": "Candidate 1 co cost thap nhat (120) va semantic equivalent voi confidence 98%. Improvement 76%."
  }
}
```

---

## 7. Research Contribution Points

1. **Dynamic KB:** KB hoạt động với bất kỳ schema nào — không hardcode dataset cụ thể
2. **Interactive What-If:** User nhập SQL kết nối live DB → nhận N candidates → thử trước khi commit
3. **Explainable Rules:** Mỗi rule suggestion có Chain-of-Thought: TẠI SAO, THỨ TỰ, LỢI ÍCH
4. **Semantic Verification:** Tự động verify correctness của mỗi rewrite bằng row-level comparison
5. **Real-time Plan Comparison:** EXPLAIN ANALYZE trực tiếp trên live DB, không mock
6. **Schema-Aware Optimization:** Row count estimates từ information_schema được dùng cho Join Reordering

---

## 8. File Structure (v2.0)

```
d:/DoAnTotNghiep/LLM-R2-1/
├── SPEC.md                          # This file
├── README.md                        # User-facing documentation
├── requirements.txt                # Dependencies
├── .env                            # Environment variables
│
├── my_exp/                         # Main package
│   ├── __init__.py
│   │
│   ├── core/                       # Core Engine Layer
│   │   ├── __init__.py
│   │   ├── sql_parser.py           # SQL → AST via sqlglot
│   │   ├── sql_analyzer.py         # Feature extraction + pattern detection
│   │   ├── schema_loader.py        # PostgreSQL schema loader (pg_catalog)
│   │   ├── schema_visualizer.py    # Schema → tree data structure for UI
│   │   ├── multi_rewrite_engine.py  # N-candidate rewrite generator
│   │   ├── rule_knowledge_base.py   # KB metadata (6 rules, descriptions)
│   │   ├── run_tests.py             # Unit tests (26/26)
│   │   │
│   │   └── rules/                  # Rule implementations
│   │       ├── __init__.py
│   │       ├── predicate_pushdown.py      # KB-001
│   │       ├── projection_pruning.py       # KB-002
│   │       ├── join_reordering.py          # KB-003
│   │       ├── subquery_unnesting.py      # KB-004
│   │       ├── aggregation_pushdown.py     # KB-005
│   │       └── redundant_join_elimination.py  # KB-006
│   │
│   ├── dss/                       # Decision Support System Layer
│   │   ├── __init__.py
│   │   ├── llm_rule_selector.py    # LLM (Claude) + Pattern fallback
│   │   ├── semantic_checker.py     # Row-level equivalence verification
│   │   ├── plan_comparator.py      # EXPLAIN ANALYZE comparison
│   │   ├── optimizer_pipeline.py    # Main orchestration pipeline
│   │   ├── json_builder.py         # Build structured JSON output
│   │   └── test_dss.py             # DSS component tests
│   │
│   ├── ui/                        # User Interface Layer (NEW v2.0)
│   │   ├── __init__.py
│   │   ├── app.py                  # Main Streamlit app
│   │   ├── app_old.py              # Previous version (archived)
│   │   │
│   │   ├── components/             # Reusable UI components
│   │   │   ├── __init__.py
│   │   │   ├── schema_explorer.py   # Left panel: DB schema tree
│   │   │   ├── kb_directory.py       # Left panel: KB rules tree
│   │   │   ├── query_editor.py      # SQL editor with autocomplete
│   │   │   ├── ast_viewer.py        # AST tree visualizer
│   │   │   ├── flow_diagram.py      # Optimization flow diagram
│   │   │   ├── rule_card.py         # Rule detail card
│   │   │   ├── plan_tree.py         # Execution plan tree renderer
│   │   │   ├── comparison_table.py  # Before/after comparison table
│   │   │   ├── results_table.py     # Query result table
│   │   │   └── json_viewer.py       # JSON output viewer + download
│   │   │
│   │   └── pages/                 # Streamlit multipage (optional)
│   │       ├── 1_workspace.py        # Main workspace
│   │       ├── 2_knowledge_base.py  # Standalone KB explorer
│   │       ├── 3_benchmark.py        # Research benchmark runner
│   │       └── 4_settings.py         # Settings & configuration
│   │
│   ├── evaluator/                 # PostgreSQL evaluation tools
│   │   ├── postgres_runner.py
│   │   ├── explain_parser.py
│   │   ├── dataset_loader.py
│   │   └── result_checker.py
│   │
│   ├── queries/                   # Test query suites
│   │   ├── test_cases.json         # Mixed queries
│   │   ├── test_cases_dsb.json     # DSB dataset
│   │   └── test_cases_job.json     # JOB dataset
│   │
│   └── research_report.py         # Benchmark & research report generator
│
├── archive/                        # Archived from v1.0
│   ├── src/                        # Old LLM_R2 pipeline
│   ├── my_exp_llm/               # Old LLM selector
│   ├── old_rules/                # Old rule implementations
│   └── old_results/              # Old benchmark results
│
├── results/                        # Generated outputs
│   ├── benchmarks/                # Benchmark JSON data
│   └── research/                  # Markdown research reports
│
├── src/                            # Active backend utilities
│   ├── rewriter.py                # Java rewriter wrapper
│   ├── __init__.py
│   └── calcite_core_main_jar/     # Apache Calcite JAR
│
└── data/                          # Test data & schemas
    ├── data_llmr2/               # Original pool & schema files
    └── schemas/                   # JSON schema definitions
```

---

## 9. Evaluation Metrics

| Metric | Description | Target | Measurement |
|--------|------------|--------|-------------|
| Rule Accuracy | % queries where recommended rules match expected rules | > 70% | Benchmark on TPC-H, DSB, JOB |
| Plan Improvement | % queries where rewritten cost < original cost | > 60% | PostgreSQL EXPLAIN ANALYZE |
| Semantic Equivalence | % rewrites producing identical results | > 95% | Row-level comparison |
| Schema Generalization | Rule accuracy on unseen schemas | > 60% | Cross-dataset validation |
| Response Time | SQL input → recommendation | < 10s | Benchmark timer |
| Parse Success Rate | % queries successfully parsed | > 90% | Benchmark on 11+ queries |
| LLM Explanation Quality | Human evaluation of explanations | > 4/5 | Survey (optional) |

---

## 10. Test Cases

### 10.1 Rule Unit Tests (26 test cases)

Each rule has dedicated test cases covering:
- **Safe patterns:** Rules that should apply and produce correct output
- **Unsafe patterns:** Rules that should NOT apply (preconditions not met)
- **Edge cases:** Empty queries, single-table, complex nesting

### 10.2 Integration Tests

- **Pipeline E2E:** SQL → Parse → Analyze → Rules → Rewrite → Compare → Verify
- **Cross-dataset:** TPC-H Q1-Q17, DSB (3+ queries), JOB (3+ queries)
- **LLM Fallback:** When ANTHROPIC_API_KEY missing → verify pattern-based still works
- **DB Disconnect:** When PostgreSQL unreachable → graceful error handling
- **Multi-candidate:** Verify all N candidates are generated and distinct

### 10.3 UI Interaction Tests

- **Schema Load:** Verify schema explorer populates within 5s of connection
- **Query Execute:** Verify results table shows within timeout
- **Optimization Trigger:** Verify all 6 output tabs populate after [Optimize]
- **JSON Download:** Verify downloaded JSON matches displayed output
- **Rule Click:** Verify clicking rule in KB tree shows detail card

### 10.4 Research Tests

- **KB Generalizability:** Load schema not in training data → rules still applicable
- **Ablation Study:** Pattern-only vs LLM-guided on same queries
- **Multi-Candidate Quality:** Verify candidates are distinct and semantically valid

---

## 11. Component Specifications

### 11.1 Schema Explorer (`schema_explorer.py`)

**Input:** PostgreSQL connection
**Output:** Nested tree data structure for Streamlit tree rendering

```
Database: dsb (10 tables)
├── customer (150,000 rows, 25 cols)
│   ├── c_custkey [PK, integer]
│   ├── c_name [varchar]
│   └── c_address [varchar]
│       └── c_customer_sk [FK → customer.c_custkey]
├── orders (1,500,000 rows, 10 cols)
│   ├── o_orderkey [PK, integer]
│   ├── o_custkey [FK, integer] → customer.c_custkey
│   └── o_totalprice [decimal]
└── ...
```

### 11.2 AST Viewer (`ast_viewer.py`)

Renders sqlglot AST as collapsible tree with color-coded node types:
- SELECT nodes: Blue (#1e3a5f)
- JOIN nodes: Orange (#fd7e14)
- WHERE nodes: Yellow (#ffc107)
- FROM nodes: Green (#28a745)
- SUBQUERY nodes: Purple (#6f42c1)

### 11.3 Flow Diagram (`flow_diagram.py`)

Renders 5-node optimization pipeline:
```
[SQL Input] → [AST Parser] → [Feature Analyzer] → [Rule Selector] → [Rewrite Engine]
     ↓              ↓               ↓                    ↓                ↓
  text area    tree view     metrics card        rule cards      before/after
```

### 11.4 Plan Comparator (`plan_comparator.py`)

Uses PostgreSQL `EXPLAIN (ANALYZE, FORMAT JSON, COSTS, TIMING, BUFFERS)` to get real execution plans, then:
- Extracts: total cost, execution time, rows processed, node count
- Compares: original vs rewritten node-by-node
- Renders: collapsible tree view of both plans side-by-side

---

## 12. Improvement Roadmap (Level 1-3)

### Research Gap Analysis — Key Finding from Benchmark

After running the full TPC-H benchmark (22 queries), the system revealed:

**LLM-based SQL rewriting via sqlglot has fundamental limitations:**
- Only 1/18 completed queries improved (Q22: +26.7%)
- 8/18 queries became WORSE after rewriting
- Root cause: sqlglot rewriters don't produce meaningfully different SQL for well-written TPC-H queries
- The TPC-H queries are already optimized by design — rewriting them doesn't help

**Index Recommendations are the real value:**
- The system successfully identifies 1-4 index opportunities per query
- Example: Q1 → `CREATE INDEX idx_lineitem_l_shipdate ON lineitem(l_shipdate);`
- This is actionable: users can create these indexes and re-test
- This aligns with real-world DBA practice

**The thesis contribution shifts to:**
1. **LLM as EXPLAIN-analyzer**: LLM reasons about execution plans to identify bottlenecks
2. **Index Advisor**: Detects Seq Scan on large tables and recommends concrete indexes
3. **Rule-based guardrails**: Semantic checks prevent incorrect rewrites (INNER JOIN never removed, SELECT * preserves columns)
4. **Explainable optimization**: Every recommendation has `reason`, `before_snippet`, `after_snippet`

### Research Gap Analysis

Based on survey of related work (SPA/LASER/Larch/Octo/SQLChat/AIDE-SQL), the following gaps exist:

| Gap | Existing Systems | LLM-R2 Addresses |
|-----|-----------------|-----------------|
| No semantic verification | SQLChat, AIDE-SQL, Octo | ✅ Column count + row-level check |
| No rule-based safety | Most LLM-only systems | ✅ 6 rules with preconditions |
| No EXPLAIN-guided rewrite | All systems except SPA (requires RL training) | ⚠️ Partial (manual EXPLAIN parsing) |
| No explainable output | SPA, LASER (black-box RL) | ✅ Rule reasons + before/after snippets |
| No lightweight deployment | SPA needs RL infrastructure; LASER needs MCTS | ✅ Single API call via Groq |
| No TPC-H benchmark | Most academic systems | ✅ 22 TPC-H queries |
| No multi-candidate comparison | Most systems | ✅ N candidates with semantic check |

**Core differentiator**: LLM-R2 achieves **explainable rule-based SQL optimization with semantic correctness guarantees** at minimal infrastructure cost — positioning it between pure LLM tools (unreliable) and full RL training pipelines (expensive).

---

### Level 1: Core System Completion (1-2 weeks)

**Goal**: Make the system reliable, complete, and thesis-demonstrable.

#### L1.1: TPC-H Benchmark Suite
- Run all 22 TPC-H queries through the pipeline
- Generate comparison table: Query | Original Cost | Optimized Cost | Improvement % | Rules Applied | Semantic OK
- Export as markdown table for thesis
- Value: Provides empirical evidence of optimization effectiveness

#### L1.2: Index Recommendation from EXPLAIN
- Parse EXPLAIN JSON → detect Seq Scan on large tables
- Generate: `CREATE INDEX idx_<table>_<column> ON <table>(<column>);`
- Explain why: "Seq Scan detected on 6M-row lineitem table — index on l_shipdate would reduce cost"
- Value: Actionable recommendations beyond rule rewriting

#### L1.3: EXPLAIN-Guided LLM Rule Selection
- Feed EXPLAIN JSON output into LLM prompt (not just SQL)
- LLM sees: which nodes are expensive, which operations dominate
- Prompt: "Based on this plan, which rules would reduce the Seq Scan cost?"
- Value: Rule selection guided by actual plan bottlenecks, not just SQL structure

#### L1.4: Side-by-Side Plan Display
- Show original vs optimized EXPLAIN plans as two collapsible trees
- Highlight changed nodes in green/red
- Value: Visual proof of optimization for thesis presentation

#### L1.5: Fix Remaining UI Issues
- SQL output formatting (multi-line, word-wrap)
- Metrics display (opt > orig = red, opt < orig = green)
- Block Analyze until DB connected
- Value: Usable thesis demo

---

### Level 2: Enhanced Accuracy (2-4 weeks)

**Goal**: Improve optimization quality through better LLM integration and A/B testing.

#### L2.1: Multi-Run Performance Testing
- Run each query 5 times → report p50/p95/p99 latency
- Current: single-run (unstable for fast queries)
- Value: Reliable performance numbers for thesis

#### L2.2: Query Complexity Scoring
- Classify queries: O(n), O(n log n), O(n²), O(n³)
- Based on: join count, subquery depth, aggregation complexity
- Value: Justify rule recommendations with complexity analysis

#### L2.3: Cost Breakdown Analysis
- Parse EXPLAIN nodes → separate I/O cost, CPU cost, startup cost
- Show which component dominates
- Value: Targeted optimization recommendations

#### L2.4: Cross-Rule Interaction Detection
- Detect when rules conflict (e.g., Join Reordering + Subquery Unnesting order matters)
- Add ordering constraints to rule engine
- Value: Safer multi-rule optimization

#### L2.5: Learned Rule Preference Log
- Store which rules are approved/rejected by users
- Build implicit preference model over time
- Value: Adaptive rule selection based on feedback

---

### Level 3: Research Contributions (4-8 weeks)

**Goal**: Original research contributions beyond implementation.

#### L3.1: EXPLAIN-Guided LLM (Full Implementation)
- Complete the feedback loop: Rewrite → EXPLAIN → LLM sees plan → Refine rewrite
- Compare: LLM rule selection WITH vs WITHOUT EXPLAIN context
- Value: Answers "Does seeing the plan improve rule selection accuracy?"
- **Research question**: Can LLM improve rule selection by observing actual execution bottlenecks?

#### L3.2: Ablation Study
- Compare: LLM-guided vs Pattern-only on same TPC-H queries
- Measure: Improvement rate, semantic error rate, explanation quality
- Value: Quantify the LLM contribution over heuristics

#### L3.3: Cross-DB Generalization
- Test on PostgreSQL (tpch) vs MySQL (tpch-mysql) vs SQLite
- Measure: Portability of rule-based approach
- Value: Does the method generalize beyond PostgreSQL?

#### L3.4: Visual EXPLAIN Tree
- Render EXPLAIN JSON as interactive tree (similar to pgAdmin)
- Color-coded by node type (Seq Scan=red, Index Scan=green, Hash Join=orange)
- Value: Better thesis visualization

#### L3.5: Comparative Evaluation Report
- Compare LLM-R2 against: SQLChat, AIDE-SQL, PostgreSQL native optimizer
- Metrics: Semantic error rate, improvement rate, response time
- Value: Independent evaluation for thesis defense

---

### Implementation Priority Matrix

| Priority | Feature | Effort | Research Value | Status |
|----------|---------|--------|----------------|--------|
| P0 | TPC-H Benchmark | 2h | VERY HIGH | TODO |
| P0 | L1.5 UI fixes (done) | 2h | MEDIUM | DONE |
| P1 | Index recommendation | 4h | HIGH | TODO |
| P1 | EXPLAIN-guided LLM | 6h | VERY HIGH | TODO |
| P1 | Multi-run A/B testing | 3h | HIGH | TODO |
| P2 | Query complexity scoring | 4h | MEDIUM | TODO |
| P2 | Cross-rule interaction | 3h | MEDIUM | TODO |
| P2 | Learned preference log | 8h | HIGH | TODO |
| P3 | Cross-DB generalization | 8h | HIGH | TODO |
| P3 | Visual EXPLAIN tree | 6h | MEDIUM | TODO |
| P3 | Ablation study | 4h | VERY HIGH | TODO |

---

## 13. Environment Configuration

```bash
# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=tpch
POSTGRES_USER=postgres
POSTGRES_PASSWORD=nhanpro12

# LLM Provider (Groq — priority)
GROQ_API_KEY=gsk_...          # Primary LLM
# Gemini (fallback)
GEMINI_API_KEY=...             # Secondary LLM
# Anthropic (fallback)
ANTHROPIC_API_KEY=sk-ant-...  # Tertiary LLM

# App Settings
API_PORT=8008
VITE_PORT=5173
MAX_QUERY_ROWS=100
QUERY_TIMEOUT_SEC=30
```
