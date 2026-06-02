# -*- coding: utf-8 -*-
"""
my_exp.ui.text
==============
All UI strings in Vietnamese with proper UTF-8 encoding.
Import from this module to avoid encoding issues.
"""
APP_TITLE = "LLM-R2: Interactive SQL Optimizer"
APP_SUBTITLE = "Phân tích SQL | Đề xuất luật | Sinh candidates | So sánh plans"
APP_WELCOME = "Chào mừng đến với LLM-R2"
APP_WELCOME_DESC = "Nhập SQL và nhấn Optimize để bắt đầu tối ưu hóa."
APP_WELCOME_DB = "Kết nối PostgreSQL từ sidebar để sử dụng đầy đủ tính năng."

# Sidebar
SIDEBAR_TITLE = "LLM-R2 Enhanced"
SIDEBAR_SUBTITLE = "Interactive SQL Optimizer"
DB_CONN_TITLE = "Kết nối Database"
DB_STATUS = "Trạng thái"
DB_CONNECTED = "Đã kết nối"
DB_DISCONNECTED = "Chưa kết nối"
DB_HOST = "Host"
DB_PORT = "Port"
DB_NAME = "Database"
DB_USER = "User"
DB_PASSWORD = "Password"
BTN_CONNECT = "Kết nối"
BTN_DISCONNECT = "Ngắt kết nối"

# Schema
SCHEMA_TITLE = "Schema Explorer"
SCHEMA_TABLES = "bảng"
SCHEMA_VIEW = "Xem cấu trúc"
SCHEMA_LOADING = "Đang tải schema..."
SCHEMA_NO_CONN = "Kết nối DB để xem schema"
SCHEMA_ERR = "Lỗi kết nối"
SCHEMA_ROWS = "dòng"
SCHEMA_COLS = "cột"
SCHEMA_BTN_SELECT = "SELECT *"
SCHEMA_BTN_COUNT = "COUNT(*)"
SCHEMA_BTN_COPY = "Copy"
SCHEMA_COL_PK = "PK"
SCHEMA_COL_FK = "FK"
SCHEMA_COL_NOT_NULL = "NOT NULL"
SCHEMA_REFERENCES = "References"

# KB
KB_TITLE = "Hệ Cơ Sở Tri Thức"
KB_TOTAL = "Tổng luật"
KB_APPLICABLE = "Có thể áp dụng"
KB_RECOMMENDED = "Được đề xuất"
KB_LEGEND_APPLIED = "Áp dụng"
KB_LEGEND_AVAILABLE = "Có sẵn"
KB_LEGEND_NA = "Không áp dụng"
KB_BENEFIT = "Lợi ích"
KB_RISK = "Rủi ro"
KB_TRIGGER = "Trigger"
KB_SAFETY = "Kiểm tra an toàn"
KB_THU_TU = "Thứ tự tối ưu"
KB_VI_DU = "Ví dụ"
KB_INPUT = "Input"
KB_OUTPUT = "Output"

# Rules
RULE_001_NAME = "Đẩy Điều Kiện Lọc Xuống"
RULE_002_NAME = "Loại Bỏ Cột Thừa"
RULE_003_NAME = "Đổi Thứ Tự JOIN"
RULE_004_NAME = "Chuyển Subquery Thành JOIN"
RULE_005_NAME = "Đẩy Phép Tổng Hợp Xuống"
RULE_006_NAME = "Loại Bỏ JOIN Dư Thừa"

RULE_001_DESC = "Đẩy WHERE từ query ngoài vào subquery trong FROM clause"
RULE_002_DESC = "Loại bỏ cột không cần thiết khỏi SELECT"
RULE_003_DESC = "Sắp xếp lại thứ tự JOIN theo kích thước bảng"
RULE_004_DESC = "Chuyển IN/EXISTS subquery thành JOIN để dùng Hash Join"
RULE_005_DESC = "Đẩy GROUP BY từ query ngoài vào subquery"
RULE_006_DESC = "Loại bỏ JOIN mà bảng được JOIN không được sử dụng"

RULE_BENEFIT_HIGH = "Cao - Giảm số dòng trung gian"
RULE_BENEFIT_MED = "Trung bình - Giảm I/O bandwidth"
RULE_RISK_LOW = "Thấp"
RULE_RISK_MED = "Trung bình"

RULE_ORDER_HINTS = {
    "predicate_pushdown": "Thứ tự: 2 (sau khi unnest subquery)",
    "projection_pruning": "Thứ tự: 6 (cuối cùng)",
    "join_reordering": "Thứ tự: 3 (sau khi unnest)",
    "subquery_unnesting": "Thứ tự: 1 (trước tiên, mở đường)",
    "aggregation_pushdown": "Thứ tự: 4 (trước JOIN)",
    "redundant_join_elimination": "Thứ tự: 5 (trước cuối)",
}

# Query Editor
EDITOR_PLACEHOLDER = "SELECT * FROM orders WHERE o_totalprice > 100000"
BTN_RUN = "Run Query"
BTN_OPTIMIZE = "Optimize"
BTN_CLEAR = "Clear"
BTN_EXPORT = "Export"
BTN_HISTORY = "Lịch sử"
BTN_USE_EXAMPLE = "Dùng ví dụ này"

HISTORY_TITLE = "Lịch sử query"
HISTORY_EMPTY = "(Trống)"
NO_DB_WARNING = "Kết nối database trước (sidebar) để chạy SQL."

# Results
RESULTS_TITLE = "Kết Qủa Query"
RESULTS_COLS = "Cột"
RESULTS_ROWS = "Dòng"
RESULTS_TIME = "Thời gian"
RESULTS_DETAIL = "Chi tiết"
RESULTS_MORE = "Hiển thị"

# Optimization
OPT_TITLE = "Phân Tích Chi Tiết Từng Bước"
OPT_METHOD = "Phương pháp"
OPT_FLOW_TITLE = "Luồng Tối Ưu Hóa (6 bước)"
OPT_FLOW_STEP1 = "INPUT"
OPT_FLOW_STEP2 = "PARSE"
OPT_FLOW_STEP3 = "ANALYZE"
OPT_FLOW_STEP4 = "DETECT"
OPT_FLOW_STEP5 = "RECOMMEND"
OPT_FLOW_STEP6 = "OUTPUT"
OPT_FLOW_SQL_CHARS = "ký tự SQL"
OPT_FLOW_PARSE_OK = "Parse thành công!"
OPT_FLOW_PARSE_ERR = "Parse thất bại!"
OPT_FLOW_TABLES = "bảng"
OPT_FLOW_JOINS = "JOIN"
OPT_FLOW_SUBQUERIES = "subquery"
OPT_FLOW_AGG = "AGG"
OPT_FLOW_GROUP = "GROUP BY"
OPT_FLOW_OPPS_DETECTED = "cơ hội được phát hiện"
OPT_FLOW_RULES_RECOM = "luật được đề xuất"
OPT_FLOW_CANDIDATES = "candidates"
OPT_FLOW_CHANGED = "đã đổi"

# Tabs
TAB_AST = "1. AST & Flow"
TAB_STEPS = "2. Chi Tiết Luật"
TAB_COMPARE = "3. So Sánh Plans"
TAB_JSON = "4. JSON Output"
TAB_TABLE = "5. Bảng So Sánh"

# AST
AST_TITLE = "Cây AST"
AST_DETAIL = "Chi tiết cây AST"
AST_TABLES = "bảng"
AST_COMPLEXITY = "Độ phức tạp"
AST_FACTORS = "Yếu tố"

# Steps
STEPS_TITLE = "Chi Tiết Luật Đề Xuất"
STEPS_BUOC = "Bước"
STEPS_LY_DO = "Lý do"
STEPS_LOI_ICH = "Lợi ích"
STEPS_CANH_BAO = "Cảnh báo"
STEPS_CHI_TIET = "Chi tiết luật"

# Compare
COMPARE_TITLE = "So Sánh Plans"
COMPARE_BEST = "Phiên Bản Được Chọn"
COMPARE_ORIG = "SQL Gốc"
COMPARE_REW = "SQL Rewrite"
COMPARE_ORIG_COST = "Cost (Gốc)"
COMPARE_REW_COST = "Cost (Rewrite)"
COMPARE_IMPROVE = "Cải thiện"
COMPARE_CANDIDATES = "Tất Cả Candidates"
COMPARE_EQUIV = "Tương đương"
COMPARE_NOT_EQUIV = "Không tương đương"
COMPARE_EQUIV_CONF = "Tương đương (độ tin:"

# JSON
JSON_TITLE = "JSON Output Đầy Đủ"
JSON_DOWNLOAD = "Tải JSON"
JSON_THINK = "Quá trình suy luận"
JSON_AST_ANALYSIS = "Phân tích AST"
JSON_CONFLICT = "Giải quyết xung đột"
JSON_SEQUENCE = "Chuỗi tối ưu"
JSON_CONFIDENCE = "Độ tin cậy"

# Table
TABLE_TITLE = "Bảng So Sánh Candidates"
TABLE_NUM = "#"
TABLE_TYPE = "Loại"
TABLE_ORIG = "Gốc"
TABLE_REWRITE = "Rewrite"
TABLE_RULES = "Luật"
TABLE_CHANGED = "Đã đổi"
TABLE_EQUIV = "Tương đương"
TABLE_COST_ORIG = "Cost(Gốc)"
TABLE_COST_REW = "Cost(Rewrite)"
TABLE_IMPROVE = "Cải thiện%"
TABLE_HIGHLIGHT = "Dòng xanh lá là lựa chọn được đề xuất bởi hệ thống"

# Stats
STATS_QUERY_ID = "Query ID"
STATS_COMPLEXITY = "Độ phức tạp"
STATS_CANDIDATES = "Candidates"
STATS_CHANGED = "Đã đổi"
STATS_EQUIV = "Tương đương"
STATS_UNKNOWN = "?"

# Quick examples
EXAMPLES_TITLE = "Ví dụ nhanh"
EXAMPLES = {
    "Predicate Pushdown": "SELECT a FROM (SELECT a, b, c FROM t) AS sub WHERE a > 10",
    "Subquery Unnesting": "SELECT c_name FROM customer WHERE c_custkey IN (SELECT o_custkey FROM orders);",
    "Multiple JOINs": "SELECT * FROM orders o JOIN lineitem l ON o.id=l.o_id JOIN nation n ON o.n_id=n.id",
    "Aggregation Pushdown": "SELECT sub.a, SUM(sub.b) FROM (SELECT a, b FROM t) AS sub GROUP BY sub.a",
    "Filter Into Join": "SELECT * FROM a JOIN b ON a.id = b.a_id WHERE b.status = 'ACTIVE'",
    "Limit Pushdown": "SELECT * FROM (SELECT * FROM orders ORDER BY o_totalprice DESC) AS sub LIMIT 10",
    "Projection Pruning": "SELECT c_name FROM (SELECT * FROM customer) AS sub",
    "Complex Mixed": "SELECT c_name, SUM(o_totalprice) FROM customer c JOIN orders o ON c.c_custkey = o.o_custkey WHERE c.c_mktsegment='AUTOMOBILE' AND o.o_orderdate > '1998-01-01' AND c.c_custkey IN (SELECT o2.o_custkey FROM orders o2 WHERE o2.o_totalprice > 500000) GROUP BY c_name ORDER BY SUM(o_totalprice) DESC LIMIT 20",
}

# System Status
SYS_STATUS = "Trạng thái hệ thống"
SYS_LLM_READY = "Sẵn sàng"
SYS_LLM_FALLBACK = "Fallback pattern-based"
SYS_LLM_MODE = "Chế độ"
SYS_MODE_LLM = "LLM"
SYS_MODE_PATTERN = "Pattern-based"

# Errors
ERR_DB_CONN = "Lỗi: {}"
ERR_PARSE = "Parse thất bại!"
ERR_TIMEOUT = "Query timeout"
ERR_SYNTAX = "Lỗi cú pháp: {}"
ERR_NO_RESULT = "Query chạy thành công nhưng không có kết quả."

# Language
LANG_ORIGINAL = "Gốc"
LANG_REWRITE = "Đã đổi"
LANG_CO = "Có"
LANG_KHONG = "Không"
LANG_DANG_CHAY = "Đang chạy..."
LANG_DANG_PHAN_TICH = "Đang phân tích và tối ưu hóa..."
