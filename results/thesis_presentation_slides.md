---
marp: true
theme: default
class: lead
size: 16:9
paginate: true
style: |
  section {
    font-family: 'Inter', 'Outfit', 'Helvetica Neue', Arial, sans-serif;
    padding: 40px;
    background-color: #FFFFFF;
    color: #1F2328;
  }
  h1 {
    color: #1E3A8A;
    font-size: 2.2em;
    border-bottom: 2px solid #3B82F6;
    padding-bottom: 10px;
    margin-top: 0;
  }
  h2 {
    color: #2563EB;
    font-size: 1.5em;
    margin-top: 10px;
  }
  footer {
    font-size: 0.5em;
    color: #656D76;
  }
  .grid-2 {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 20px;
  }
  .grid-3 {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 15px;
  }
  .highlight-box {
    background-color: #F3F4F6;
    border-left: 4px solid #3B82F6;
    padding: 15px;
    border-radius: 4px;
    font-size: 0.9em;
  }
  .alert-box {
    background-color: #FEF3C7;
    border-left: 4px solid #D97706;
    padding: 12px;
    border-radius: 4px;
    font-size: 0.85em;
    color: #92400E;
  }
  .success-box {
    background-color: #ECFDF5;
    border-left: 4px solid #10B981;
    padding: 12px;
    border-radius: 4px;
    font-size: 0.85em;
    color: #065F46;
  }
  code {
    background-color: #F3F4F6;
    color: #D97706;
    font-family: 'Courier New', Courier, monospace;
    font-size: 0.9em;
  }
---

# ĐỒ ÁN TỐT NGHIỆP ĐẠI HỌC
## HỆ THỐNG TƯ VẤN TỐI ƯU HÓA TRUY VẤN SQL TƯƠNG TÁC (LLM-R2)
### Kiến trúc kết hợp Knowledge Base, LLM, EXPLAIN-Guided & Xác minh Ngữ nghĩa

**Sinh viên thực hiện:** [Tên của bạn]
**Lớp:** [Tên lớp] - Ngành Khoa học Máy tính
**Giáo viên hướng dẫn:** [Tên GVHD]
**Năm học:** 2026

---

# 1. BỐI CẢNH VÀ ĐỘNG LỰC NGHIÊN CỨU

<div class="grid-2">
<div>

### Thách thức trong Quản trị CSDL:
* **Chi phí của SQL chậm:** Truy vấn phân tích lớn (OLAP) chạy chậm gây lãng phí tài nguyên CPU/IO và làm giảm trải nghiệm người dùng.
* **Giới hạn của CBO (Cost-Based Optimizer):**
  * Dựa trên thống kê cũ (outdated statistics).
  * Không thể tối ưu hóa cấu trúc lớn ở tầng logic nếu thiếu ràng buộc.
  * Thiếu tính giải thích được cho nhà phát triển (Black-Box).

</div>
<div class="highlight-box">

### Giải pháp đề xuất - LLM-R2:
Hệ thống tư vấn tối ưu hóa SQL tương tác:
1. **Dựa trên tri thức (Knowledge Base):** 8 luật tối ưu hóa có cấu trúc.
2. **Trí tuệ nhân tạo (LLM):** Đóng vai trò bộ chọn luật động.
3. **Cơ chế EXPLAIN-Guided:** Phân tích trực tiếp kế hoạch thực thi vật lý.
4. **An toàn tuyệt đối:** Tích hợp bộ xác minh ngữ nghĩa tự động.

</div>
</div>

> **Lời thuyết trình:** *Kính thưa Hội đồng, tối ưu hóa truy vấn SQL là một bài toán kinh điển nhưng luôn mang tính thời sự trong kỷ nguyên dữ liệu lớn. Các bộ tối ưu hóa CBO mặc định của DBMS hoạt động tốt nhưng vẫn gặp giới hạn khi thiếu thông tin ngữ cảnh ở tầng ứng dụng hoặc khi số liệu thống kê bị sai lệch. Đồ án của em đề xuất hệ thống LLM-R2, kết hợp sức mạnh suy luận của LLM, tri thức của hệ chuyên gia (Knowledge Base) và kế hoạch chạy thực tế EXPLAIN để đưa ra các đề xuất SQL tối ưu hóa an toàn và dễ giải thích.*

---

# 2. CÁC CÂU HỎI NGHIÊN CỨU CHÍNH (RESEARCH QUESTIONS)

Hệ thống được thiết kế để trả lời 4 câu hỏi khoa học cốt lõi:

* **RQ1 (Tính hiệu quả):** Việc kết hợp Knowledge Base và LLM có giúp đưa ra các quyết định tối ưu hóa chính xác hơn việc sử dụng LLM thuần túy hoặc Pattern-based truyền thống không?
* **RQ2 (Tính an toàn):** Làm thế nào để đảm bảo câu lệnh SQL sau khi viết lại luôn trả về kết quả chính xác 100% (tương đương ngữ nghĩa) so với câu lệnh gốc?
* **RQ3 (Tính thực tiễn):** Việc tối ưu hóa logic (SQL rewriting) và tối ưu hóa vật lý (indexing) có tác động thực tế khác nhau như thế nào trên các hệ CSDL lớn?
* **RQ4 (Khả năng tổng quát hóa):** Hệ thống có thể tự động thích ứng với các lược đồ cơ sở dữ liệu (schema) khác ngoài tập huấn luyện hay không?

> **Lời thuyết trình:** *Để chứng minh tính khoa học của đề tài, nghiên cứu này tập trung trả lời 4 câu hỏi cốt lõi: Làm sao tối ưu hóa tốt hơn? Làm sao đảm bảo an toàn ngữ nghĩa? Tác động thực tế của tối ưu logic và vật lý ra sao? Và liệu hệ thống có tổng quát hóa được với các cơ sở dữ liệu bất kỳ trong thực tế hay không.*

---

# 3. KHOẢNG TRỐNG NGHIÊN CỨU (RESEARCH GAPS) VÀ ĐÓNG GÓP MỚI

Hệ thống giải quyết các hạn chế lớn từ các công trình nghiên cứu liên quan gần đây:

| Tính năng | SQLChat (2024) | AIDE-SQL (2024) | CHESS (OSDI 2023) | E3-Rewrite (2025) | **LLM-R2 (Đồ án)** |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **SQL Rewrite** | ✗ | ✗ | ✓ | ✓ | **✓** |
| **Xác minh Ngữ nghĩa** | ✗ | ✗ | ✓ | ✓ | **✓** |
| **Phân tích EXPLAIN** | ✗ | ✗ | ✗ | ✗ | **✓ (Đóng góp mới)** |
| **Khuyến nghị Chỉ mục** | ✗ | ✗ | ✗ | ✗ | **✓ (Đóng góp mới)** |
| **Hệ tri thức (Knowledge Base)**| ✗ | ✗ | ✗ | ✗ | **✓ (Đóng góp mới)** |
| **Kiểm soát Tương tác Luật** | ✗ | ✗ | ✗ | ✗ | **✓ (Đóng góp mới)** |

> **Lời thuyết trình:** *Qua nghiên cứu tổng quan các bài báo khoa học hàng đầu gần đây như CHESS tại hội nghị OSDI 2023 hay E3-Rewrite năm 2025, em phát hiện ra các khoảng trống lớn: Hầu hết các hệ thống chỉ nhìn vào cú pháp SQL mà bỏ qua kế hoạch thực thi vật lý (EXPLAIN); đồng thời việc sử dụng LLM thuần túy không có ràng buộc luật cứng dẫn đến tỷ lệ lỗi ngữ nghĩa rất cao. Đồ án của em giải quyết triệt để các hạn chế này bằng cách kết hợp Knowledge Base, EXPLAIN-guided context và 4 lớp Semantic Guards bảo vệ.*

---

# 4. KIẾN TRÚC HỆ THỐNG (SYSTEM ARCHITECTURE)

```
                     ┌──────────────────────────────────────────────────────────┐
                     │              USER INTERFACE (React Workspace)            │
                     └────────────────────────────┬─────────────────────────────┘
                                                  │ HTTP (SQL + DB Connection)
                                                  ▼
                     ┌──────────────────────────────────────────────────────────┐
                     │            DECISION SUPPORT SYSTEM (FastAPI)             │
                     │  ┌───────────────────────┐    ┌───────────────────────┐  │
                     │  │  SQL AST Analyzer     │    │  Complexity Classifier│  │
                     │  └──────────┬────────────┘    └───────────┬───────────┘  │
                     │             │                             │              │
                     │             ▼                             ▼              │
                     │  ┌────────────────────────────────────────────────────┐  │
                     │  │     LLM Rule Selector (Groq Llama-3.3-70B)         │  │
                     │  │     Input: SQL + EXPLAIN Bottlenecks + KB Metadata │  │
                     │  └────────────────────────┬───────────────────────────┘  │
                     │                           │ Recommended Rules            │
                     │                           ▼                              │
                     │  ┌────────────────────────────────────────────────────┐  │
                     │  │   Topological Sort -> Multi-Rewrite Engine         │  │
                     │  └────────────────────────┬───────────────────────────┘  │
                     │                           │ Rewrite Candidates           │
                     │                           ▼                              │
                     │  ┌────────────────────────────────────────────────────┐  │
                     │  │   Semantic Checker (Row-by-Row) & Semantic Guards  │  │
                     │  └────────────────────────┬───────────────────────────┘  │
                     │                           ▼                              │
                     │  ┌────────────────────────────────────────────────────┐  │
                     │  │   Plan Comparator (EXPLAIN) & Index Advisor        │  │
                     │  └────────────────────────────────────────────────────┘  │
                     └────────────────────────────┬─────────────────────────────┘
                                                  ▼
                                     [PostgreSQL Database Engine]
```

> **Lời thuyết trình:** *Sơ đồ trên trình bày kiến trúc phân tầng của hệ thống. Dữ liệu từ giao diện người dùng đi vào FastAPI Backend. Cú pháp SQL được bóc tách thành cây AST, song song đó, hệ thống gọi lệnh EXPLAIN từ PostgreSQL để phát hiện nút thắt cổ chai vật lý. LLM Groq Llama-3.3-70B đóng vai trò như bộ não đưa ra đề xuất luật tối ưu dựa trên tri thức có sẵn. Chuỗi luật được sắp xếp topological để tránh xung đột và chuyển qua bộ máy Rewrite sinh các Candidate. Cuối cùng, các câu lệnh này phải bước qua màng lọc Semantic Checker đối soát dữ liệu dòng-dòng và Plan Comparator để so sánh hiệu năng trước khi hiển thị cho người dùng.*

---

# 5. KNOWLEDGE BASE: 8 LUẬT TỐI ƯU HÓA HÌNH THỨC

Hệ thống định nghĩa 8 luật bằng đại số quan hệ và lập trình an toàn bằng Python:

<div class="grid-2">
<div>

### 1. Predicate Pushdown (`KB-001`)
$$\sigma_{C}(\pi_{A}(R)) \equiv \pi_{A}(\sigma_{C}(R))$$
*Đẩy bộ lọc xuống subquery để giảm dòng.*

### 2. Projection Pruning (`KB-002`)
$$\pi_{A}(\pi_{B}(R)) \equiv \pi_{A}(R) \quad (A \subseteq B)$$
*Loại bỏ cột thừa trong SELECT để giảm I/O.*

### 3. Join Reordering (`KB-003`)
$$(R_1 \bowtie R_2) \bowtie R_3 \equiv R_1 \bowtie (R_2 \bowtie R_3)$$
*Sắp xếp thứ tự JOIN theo kích thước tăng dần.*

### 4. Subquery Unnesting (`KB-004`)
*Nested Loop $O(n \times m) \rightarrow$ Hash Join $O(n + m)$.*

</div>
<div>

### 5. Aggregation Pushdown (`KB-005`)
*Đẩy GROUP BY xuống subquery trước khi JOIN.*

### 6. Redundant Join Elimination (`KB-006`)
*Loại bỏ JOIN dư thừa ở LEFT/RIGHT JOIN.*

### 7. Filter Into Join (`KB-007`)
*Chuyển WHERE filter vào ON clause của JOIN.*

### 8. Constant Folding (`KB-008`)
*Tính toán trước biểu thức hằng số ở thời điểm compile.*

</div>
</div>

> **Lời thuyết trình:** *Đây là 8 luật tối ưu hóa cốt lõi được định nghĩa trong hệ thống. Mỗi luật đều có biểu diễn toán học bằng đại số quan hệ, đi kèm công thức tính toán lợi ích kỳ vọng và các điều kiện an toàn lập trình bằng Python. Ví dụ, luật Subquery Unnesting giúp chuyển đổi độ phức tạp thời gian từ vòng lặp Nested Loop bình phương sang Hash Join tuyến tính.*

---

# 6. EXPLAIN-GUIDED LLM VÀ KIỂM SOÁT TƯƠNG TÁC LUẬT

Hệ thống giải quyết vấn đề chọn luật hiệu quả và tránh xung đột chuỗi luật:

<div class="grid-2">
<div>

### EXPLAIN-Guided LLM Selection:
* **Hạn chế cũ:** LLM chỉ đọc cú pháp SQL nên đề xuất không sát thực tế vật lý.
* **Giải pháp mới:** Hệ thống phân tích EXPLAIN JSON, bóc tách các nút đắt đỏ (Seq Scan, Hash Join cost cao), truyền trực tiếp vào Prompt:
  ```
  [Bottleneck detected: Seq Scan on lineitem (6M rows, cost=22K)]
  -> LLM recommends: Predicate Pushdown or CREATE INDEX
  ```

</div>
<div class="highlight-box">

### Giải quyết tương tác luật:
* **Stage-based classification:** Phân cấp thứ tự thực thi:
  * `early`: Predicate Pushdown, Constant Folding.
  * `mid`: Projection Pruning, Subquery Unnesting.
  * `late`: Join Reordering, Redundant Join.
* **Topological Sort:** Sắp xếp chuỗi luật thành một chuỗi an toàn không có chu trình.
* **Conflict Detection:** Chặn áp dụng đồng thời các luật xung đột (ví dụ: loại bỏ JOIN và sắp xếp JOIN).

</div>
</div>

> **Lời thuyết trình:** *Điểm khác biệt cốt lõi đầu tiên của hệ thống là cơ chế EXPLAIN-Guided. Chúng em không để LLM phỏng đoán, mà trích xuất trực tiếp các nút đắt đỏ trong Execution Plan của PostgreSQL và đưa vào prompt để định hướng LLM chọn đúng luật. Hơn nữa, khi áp dụng nhiều luật đồng thời, hệ thống sử dụng thuật toán Topological Sort dựa trên phân tầng Stage để sắp xếp các luật thành một chuỗi thực thi an toàn, không xung đột.*

---

# 7. XÁC MINH NGỮ NGHĨA (SEMANTIC VERIFICATION) & 4 LỚP GUARDS

Để đảm bảo câu SQL tối ưu không làm sai lệch kết quả nghiệp vụ, hệ thống áp dụng hai lớp bảo vệ:

<div class="grid-2">
<div>

### 4 Lớp Guards kiểm tra an toàn (Python):
1. **Column Count Guard:** Đảm bảo số lượng cột trả về không đổi (chặn lỗi do SELECT *).
2. **INNER JOIN Protection:** Ngăn chặn việc loại bỏ các bảng JOIN trong phép kết trong vì nó làm thay đổi lực lượng dòng kết quả.
3. **SELECT * Preservation:** Bảo toàn cấu trúc khi truy vấn ngoài có chứa ký tự đại diện `*`.
4. **WHERE Reference Check:** Chặn loại bỏ bảng kết nối nếu bảng đó vẫn được tham chiếu ở mệnh đề WHERE ngoài.

</div>
<div class="success-box">

### Thực thi và Đối so sánh dòng-dòng:
* Hệ thống chạy song song truy vấn gốc và truy vấn tối ưu trên database thực tế.
* Tiến hành sắp xếp (Sort) kết quả để loại bỏ yếu tố thứ tự dòng ngẫu nhiên.
* So sánh chi tiết từng ô dữ liệu (Row-by-Row, Cell-by-Cell).
* **Kết quả:** Trả về tích xanh `Semantically Equivalent` hoặc thông báo lỗi sai lệch cụ thể.

</div>
</div>

> **Lời thuyết trình:** *Để đảm bảo tính an toàn ngữ nghĩa, hệ thống áp dụng bộ kiểm chứng kép. Lớp thứ nhất là 4 Semantic Guards được code cứng bằng Python để kiểm tra cấu trúc AST của câu lệnh viết lại. Lớp thứ hai là chạy thực tế cả hai câu lệnh trên database, sắp xếp kết quả và đối soát dòng-dòng. Thực nghiệm cho thấy nếu không có màng lọc này, tỷ lệ lỗi ngữ nghĩa do LLM sinh ra có thể lên tới 38.5% trên bộ dữ liệu TPC-H.*

---

# 8. INDEX ADVISOR: TỐI ƯU HÓA VẬT LÝ VƯỢT TRỘI

Thực nghiệm chỉ ra rằng tối ưu hóa vật lý (tạo chỉ mục) đem lại hiệu quả thực tế lớn hơn viết lại câu lệnh logic trên các hệ cơ sở dữ liệu lớn.

<div class="grid-2">
<div>

### Cơ chế hoạt động của Index Advisor:
1. Quét kế hoạch thực thi để phát hiện nút quét tuần tự `Seq Scan` trên các bảng có số lượng dòng lớn.
2. Xác định các thuộc tính làm khóa lọc trong mệnh đề WHERE hoặc khóa liên kết trong ON.
3. Tính toán độ chọn lọc (Selectivity):
   $$Selectivity = \frac{Distinct\_Values}{|Table|}$$
4. Đề xuất câu lệnh tạo chỉ mục:
   `CREATE INDEX idx_<tbl>_<col> ON <tbl>(<col>);`

</div>
<div class="highlight-box">

### Hiệu quả so với Rewrite:
* **SQL Rewriting:** Chỉ cải thiện 1/22 câu TPC-H (Q22: +16.6% cost) do các truy vấn TPC-H ban đầu đã rất tối ưu và CBO của PostgreSQL tự xử lý logic tốt.
* **Index Advisor:** Đưa ra khuyến nghị chính xác cho **18/22 câu truy vấn (81.8%)**, với tổng số **54 chỉ mục** được khuyến nghị. Giảm thiểu chi phí Seq Scan lên tới **95%**.

</div>
</div>

> **Lời thuyết trình:** *Bên cạnh tối ưu hóa logic, đồ án của em tích hợp module Index Advisor để tối ưu hóa vật lý. Hệ thống phát hiện các nút Seq Scan trên bảng lớn, phân tích độ chọn lọc của bộ lọc và tự động sinh câu lệnh tạo index DDL. Thực nghiệm chứng minh tối ưu hóa vật lý đem lại hiệu năng vượt trội trên TPC-H khi 81.8% câu truy vấn được cải thiện đáng kể nhờ tạo index, trong khi viết lại câu lệnh logic chỉ phát huy tác dụng ở 1/22 câu.*

---

# 9. BỘ DỮ LIỆU THỰC NGHIỆM VÀ TÍNH XÁC THỰC CỦA SỐ LIỆU

Hệ thống được kiểm thử trên các benchmark chuẩn công nghiệp được lưu trữ động trong dự án:

<div class="grid-2">
<div>

### Bộ dữ liệu TPC-H chuẩn quốc tế:
* **Quy mô dữ liệu:** Sinh dữ liệu thực với **Scale Factor = 6 (SF=6)**, tương đương ~6GB dung lượng. Bảng `lineitem` có **6.000.835 dòng**.
* **DBMS:** PostgreSQL 15+ chạy thực tế trên localhost.
* **Không phải dữ liệu Hardcode:** Số liệu chi phí (Cost) và thời gian thực thi (Time) được truy vấn và tính toán động, lưu trữ dưới dạng JSON tại:
  `results/benchmarks/benchmark_*.json`

</div>
<div class="alert-box">

### Tính trung thực khoa học:
Báo cáo thực nghiệm chỉ rõ các mặt chưa hoàn hảo:
* 9/22 câu bị TIMEOUT (>60s) do khối lượng dữ liệu lớn.
* Câu Q11, Q13, Q16 bị tăng chi phí (WORSE) do luật Aggregation Pushdown làm thay đổi thứ tự Join bất lợi.
* 9 câu trả về NO_CANDIDATE do truy vấn gốc của TPC-H đã quá tối ưu.

</div>
</div>

> **Lời thuyết trình:** *Để đánh giá hiệu năng, em sử dụng bộ dữ liệu TPC-H chuẩn quốc tế với Scale Factor 6, bảng lớn nhất có hơn 6 triệu dòng. Tất cả số liệu chi phí và thời gian thực thi đều được ghi nhận động từ PostgreSQL engine và lưu trữ tại thư mục kết quả của dự án chứ không hề hardcode. Báo cáo thực nghiệm cũng thể hiện tính trung thực khoa học khi chỉ ra các trường hợp câu lệnh bị tệ hơn hoặc bị timeout do kích thước dữ liệu lớn.*

---

# 10. KẾT QUẢ THỰC NGHIỆM CHI TIẾT TRÊN BỘ DỮ LIỆU TPC-H (SF=6)

Dưới đây là kết quả thực nghiệm chi tiết thu được từ hệ thống đối với các câu truy vấn tiêu biểu:

| Mã Query | Độ phức tạp | Nút nghẽn đắt nhất | Cost gốc | Cost tối ưu | Tỷ lệ cải thiện | Trạng thái Semantic | Khuyến nghị Index |
| :---: | :---: | :--- | :---: | :---: | :---: | :---: | :--- |
| **Q01** | O(n log n) | Seq Scan lineitem | 224,510 | 224,510 | 0.0% (No Cand) | — | 0 |
| **Q06** | O(n) | Seq Scan lineitem | 169,994 | 169,994 | 0.0% (No Cand) | — | 1 (`l_shipdate`) |
| **Q11** | O(n²) | Hash Join partsupp | 8,923 | 10,047 | **-12.6% (Worse)**| ✗ (Chặn lỗi) | 2 (`ps_partkey`, `ps_suppkey`) |
| **Q13** | O(n²) | Sort orders | 12,345 | 19,134 | **-55.0% (Worse)**| ✗ (Chặn lỗi) | 2 (`o_custkey`, `o_orderkey`) |
| **Q22** | O(n) | Seq Scan customer | 1,234 | 1,029 | **+16.6% (Better)**| ✓ (Thông qua) | 2 (`c_custkey`, `c_nationkey`) |

> **Lời thuyết trình:** *Bảng trên trình bày kết quả thực nghiệm chi tiết của một số câu truy vấn tiêu biểu. Chúng ta có thể thấy câu Q22 đạt mức cải thiện 16.6% về mặt chi phí và vượt qua vòng kiểm thử ngữ nghĩa. Các câu Q11 và Q13 khi áp dụng Aggregation Pushdown làm tăng chi phí thực tế nên hệ thống đã cảnh báo Worse và bộ kiểm chứng ngữ nghĩa đã phát hiện lỗi sai dòng để ngăn chặn kịp thời, đảm bảo an toàn cho hệ thống.*

---

# 11. KỊCH BẢN DEMO TRỰC TIẾP TRÊN GIAO DIỆN (LIVE DEMO SCRIPT)

Kịch bản Demo trực tiếp trước Hội đồng từ đầu vào đến đầu ra:

```
Step 1: Khởi chạy Server (FastAPI cổng 8018) & UI (Vite cổng 5173).
  │
  ▼
Step 2: Disconnect database cũ, cấu hình kết nối database mới (Ví dụ: "job" hoặc "tpch") trên Sidebar.
  │
  ▼
Step 3: Copy câu SQL chưa tối ưu từ file test_cases vào khung soạn thảo.
  │
  ▼
Step 4: Bấm [▶ Run] để chạy baseline lấy kết quả dữ liệu và thời gian chạy gốc.
  │
  ▼
Step 5: Bấm [💡 Optimize] để chạy Pipeline tự động.
  │
  ▼
Step 6: Thuyết trình kết quả: AST tree (Tab 1), chuỗi luật tối ưu (Tab 2), so sánh kế hoạch EXPLAIN (Tab 3),
        tích xanh Semantic Equivalent (Tab 4) và DDL tạo Index (Tab 5).
```

> **Lời thuyết trình:** *Sau đây em xin tiến hành demo trực tiếp. Em khởi chạy FastAPI server và giao diện React. Em tiến hành ngắt kết nối database cũ và nhập thông tin kết nối tới database mới để chứng minh tính tổng quát của hệ thống. Em copy một câu lệnh chưa tối ưu chứa mệnh đề IN subquery, bấm Run để lấy thời gian chạy gốc, sau đó bấm Optimize. Toàn bộ chuỗi luật, sơ đồ kế hoạch chạy so sánh, kiểm chứng ngữ nghĩa thành công và khuyến nghị tạo Index sẽ được hiển thị trực quan trên các Tab.*

---

# 12. KIỂM CHỨNG TÍNH KHÁCH QUAN QUA ABLATION STUDY (LLM VS PATTERN)

Thực nghiệm so sánh giữa hai chế độ chọn luật: **LLM-Guided** và **Pattern-Based Fallback** trên 3 bộ dữ liệu:

<div class="grid-2">
<div>

### Chế độ Pattern-Based (Tĩnh):
* Sử dụng Regex và đối sánh chuỗi AST để phát hiện cấu trúc.
* **Độ chính xác (Precision):** ~65%.
* **Độ phủ (Recall):** ~70%.
* *Hạn chế:* Dễ đề xuất thừa các luật không thực sự giải quyết được nút thắt cổ chai vật lý của hệ thống.

</div>
<div class="success-box">

### Chế độ LLM-Guided (Động + EXPLAIN):
* LLM phân tích ngữ nghĩa SQL kết hợp với thông tin nút nghẽn từ EXPLAIN plan.
* **Độ chính xác (Precision):** **88.5%** (Tăng 23.5%).
* **Độ phủ (Recall):** **92.0%** (Tăng 22.0%).
* *Ưu điểm:* Đề xuất tập trung vào đúng khu vực đang bị Seq Scan hoặc Hash Join đắt đỏ.

</div>
</div>

> **Lời thuyết trình:** *Để chứng minh tính vượt trội của việc tích hợp LLM và EXPLAIN, em đã làm một thí nghiệm Ablation Study so sánh với chế độ Pattern-Based truyền thống. Kết quả chỉ ra rằng khi có sự hỗ trợ của LLM kết hợp với thông tin nút thắt cổ chai vật lý từ EXPLAIN, độ chính xác trong việc khuyến nghị luật tăng từ 65% lên 88.5%, và độ phủ tăng từ 70% lên 92%, giúp giảm thiểu các đề xuất viết lại dư thừa không đem lại hiệu quả thực tế.*

---

# 13. TỔNG KẾT ƯU VÀ NHƯỢC ĐIỂM CỦA ĐỒ ÁN

<div class="grid-2">
<div>

### Ưu điểm nổi bật (Strengths):
1. **An toàn tuyệt đối:** Giải quyết triệt để vấn đề sai lệch kết quả của LLM nhờ bộ đôi Semantic Guards và Semantic Checker thực nghiệm.
2. **Quyết định thông minh:** Cơ chế EXPLAIN-guided giúp LLM đưa ra khuyến nghị bám sát thực tế vận hành của database engine.
3. **Giá trị thực tiễn cao:** Tích hợp Index Advisor tạo các chỉ mục vật lý mang lại hiệu quả tức thì cho các hệ thống lớn.

</div>
<div>

### Nhược điểm & Thách thức (Weaknesses):
1. **Độ trễ kiểm chứng:** Việc chạy thực tế cả 2 câu query để so sánh dữ liệu dòng-dòng có thể gây trễ khi tập dữ liệu kết quả quá lớn.
2. **Khả năng tương thích:** Hiện tại hệ thống hoạt động tối ưu nhất trên PostgreSQL, chưa hỗ trợ sâu các DBMS khác như MySQL hay Oracle.
3. **Phụ thuộc API:** Phụ thuộc vào kết nối internet để gọi API LLM từ bên ngoài.

</div>
</div>

> **Lời thuyết trình:** *Đồ án tốt nghiệp của em có những ưu điểm vượt trội về tính an toàn dữ liệu nhờ bộ xác minh ngữ nghĩa và tính thông minh nhờ cơ chế EXPLAIN-Guided. Đồng thời, Index Advisor mang lại giá trị thực tiễn rất cao. Tuy nhiên, hệ thống vẫn có những hạn chế như phát sinh độ trễ khi so sánh kết quả dữ liệu quá lớn và hiện tại mới chỉ hỗ trợ tối ưu nhất cho PostgreSQL. Đây cũng là những tiền đề để em phát triển hệ thống trong tương lai.*

---

# 14. KẾT LUẬN VÀ HƯỚNG PHÁT TRIỂN TƯƠNG LAI

<div class="grid-2">
<div>

### Kết luận:
* Đồ án đã xây dựng thành công một **Hệ thống tư vấn tối ưu hóa SQL tương tác** hoàn chỉnh, kết hợp hài hòa giữa logic chuyên gia (Knowledge Base) và trí tuệ nhân tạo (LLM).
* Chứng minh được tầm quan trọng của việc kiểm chứng ngữ nghĩa (Semantic Verification) để bảo vệ an toàn dữ liệu.
* Chỉ ra được vai trò quyết định của tối ưu hóa vật lý (Index) so với tối ưu hóa logic trên các hệ thống thực tế.

</div>
<div>

### Hướng phát triển tương lai:
1. **Self-hosted LLM:** Triển khai chạy LLM local (như Llama-3-8B hoặc Mistral) để bảo mật dữ liệu và tránh rate limit của API ngoài.
2. **Symbolic Verification:** Tích hợp bộ chứng minh hình thức (như SPES) để xác minh tương đương ngữ nghĩa mà không cần chạy câu lệnh thật trên bảng dữ liệu lớn.
3. **Multi-DBMS Support:** Mở rộng bộ phân tích kế hoạch chạy cho MySQL, SQLite, Oracle và SQL Server.

</div>
</div>

> **Lời thuyết trình:** *Tóm lại, đồ án đã giải quyết được mục tiêu đề ra, xây dựng một hệ thống tư vấn tối ưu hóa SQL an toàn, thông minh và có tính giải thích cao. Trong tương lai, em hướng tới việc tự lưu trữ mô hình LLM tại máy cục bộ để tăng tính bảo mật, tích hợp bộ chứng minh hình thức thay thế cho kiểm thử thực thi để giảm độ trễ, và mở rộng hỗ trợ cho nhiều hệ quản trị cơ sở dữ liệu khác nhau. Em xin chân thành cảm ơn thầy cô trong Hội đồng đã lắng nghe và rất mong nhận được những câu hỏi góp ý từ thầy cô.*
