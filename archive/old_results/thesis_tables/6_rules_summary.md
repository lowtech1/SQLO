# Bang Phan Tich Thuc Nghiem — LLM-R2

*Duoc tao tu dong vao: 2026-05-16 13:36:05*

## 1. Bang Tom Tat 6 Luat Rewrite

| STT | Ten Luat | Mo ta | So Rules | Muc tieu |

|-----|---------|-------|---------|---------|

| 1 | **Predicate Pushdown** | Đẩy điều kiện lọc (filter) càng sâu trong cây truy vấn để giảm kích thước dữ liệ... | 4 rules | Giảm số dòng xử lý tại các node phía dưới, giảm I/... |
| 2 | **Projection Pruning** | Loại bỏ các cột không cần thiết khỏi projection để giảm lượng dữ liệu xử lý và t... | 4 rules | Giảm băng thông mạng, giảm memory khi xử lý interm... |
| 3 | **Join Reordering** | Thay đổi thứ tự các bảng trong phép nối để giảm chi phí thực thi, kết hợp đẩy fi... | 5 rules | Giảm kích thước intermediate results bằng cách thự... |
| 4 | **Subquery Unnesting** | Chuyển đổi truy vấn con (subquery) thành các phép nối (JOIN) hoặc Correlate để đ... | 4 rules | Loại bỏ overhead của subquery engine, cho phép opt... |
| 5 | **Aggregation Pushdown** | Thực hiện phép tổng hợp (aggregate) càng sớm càng tốt trong câu truy vấn để giảm... | 4 rules | Giảm số dòng cần aggregate bằng cách lọc trước rồi... |
| 6 | **Redundant Join Elimination** | Phát hiện và loại bỏ các phép nối không cần thiết hoặc thay thế bằng semi-join đ... | 5 rules | Tránh các phép nối tốn kém không cần thiết trong k... |

## 2. Bang Chi Tiet Tung Luat

### 1. Predicate Pushdown

**Mo ta:** Đẩy điều kiện lọc (filter) càng sâu trong cây truy vấn để giảm kích thước dữ liệu trung gian

**Muc tieu:** Giảm số dòng xử lý tại các node phía dưới, giảm I/O và memory


**Cac Rules trong nhom:**

1. `FILTER_INTO_JOIN`

2. `JOIN_CONDITION_PUSH`

3. `FILTER_MULTI_JOIN_MERGE`

4. `FILTER_PROJECT_TRANSPOSE`


**Vi du:**

- Input: `Filter(Join(store_sales, date_dim))`

- Output: `Join(Filter(store_sales, d_year=2001), date_dim)`

- Cong thuc: `cardinality(Filter(Join)) >> cardinality(Join(Filter))`


**Uu diem:**

- Giảm đáng kể số dòng xử lý tại các node phía dưới

- Giảm I/O vì đọc ít dữ liệu hơn

- Giảm memory footprint của intermediate results

- Đặc biệt hiệu quả với filter có selectivity cao


**Nhuoc diem:**

- Chi phí CPU cho việc đẩy và kiểm tra điều kiện

- Có thể làm chậm nếu filter không giảm được nhiều dữ liệu

- LLM có thể đề xuất sai vị trí đẩy, gây rewrite không hiệu quả


---

### 2. Projection Pruning

**Mo ta:** Loại bỏ các cột không cần thiết khỏi projection để giảm lượng dữ liệu xử lý và truyền tải

**Muc tieu:** Giảm băng thông mạng, giảm memory khi xử lý intermediate results


**Cac Rules trong nhom:**

1. `PROJECT_REMOVE`

2. `PROJECT_MERGE`

3. `PROJECT_REDUCE_EXPRESSIONS`

4. `FILTER_PROJECT_TRANSPOSE`


**Vi du:**

- Input: `SELECT * FROM orders, customer WHERE ...`

- Output: `SELECT c_customer_id, c_first_name FROM orders, customer WHERE ...`

- Cong thuc: `data_transfer = Σ(columns_selected / columns_total) × rows`


**Uu diem:**

- Giảm băng thông mạng (ít dữ liệu truyền tải)

- Giảm memory khi xử lý intermediate results

- Tăng tốc độ đọc từ disk nếu có covering indexes

- Giảm chi phí network transfer


**Nhuoc diem:**

- LLM khó xác định chính xác cột nào không cần thiết

- Thường ít impact hơn Predicate Pushdown vì DBMS đã tối ưu sẵn

- Có thể gây lỗi nếu LLM hiểu sai semantic của query


---

### 3. Join Reordering

**Mo ta:** Thay đổi thứ tự các bảng trong phép nối để giảm chi phí thực thi, kết hợp đẩy filter/project xuống

**Muc tieu:** Giảm kích thước intermediate results bằng cách thực hiện join có selectivity cao trước


**Cac Rules trong nhom:**

1. `JOIN_PROJECT_BOTH_TRANSPOSE`

2. `JOIN_PROJECT_LEFT_TRANSPOSE`

3. `JOIN_PROJECT_RIGHT_TRANSPOSE`

4. `JOIN_EXTRACT_FILTER`

5. `JOIN_REDUCE_EXPRESSIONS`


**Vi du:**

- Input: `Join(Project(A), Project(B)) → Join(A, B)`

- Output: `Project(Join(A, B)) → Filter đẩy xuống từng nhánh`

- Cong thuc: `cost(join) = Σ cost(intermediate_i) + cost(join_final)`


**Uu diem:**

- Giảm kích thước intermediate results đáng kể

- Cho phép filter được áp dụng sớm hơn

- Biến đổi cấu trúc quanh join để CBO hoạt động tốt hơn


**Nhuoc diem:**

- Không thay đổi được thứ tự bảng gốc thực sự

- LLM chỉ đề xuất biến đổi cấu trúc, không thực hiện join reordering thực sự

- Chi phí planning tăng khi có nhiều bảng


---

### 4. Subquery Unnesting

**Mo ta:** Chuyển đổi truy vấn con (subquery) thành các phép nối (JOIN) hoặc Correlate để đơn giản hóa kế hoạch truy vấn

**Muc tieu:** Loại bỏ overhead của subquery engine, cho phép optimizer tìm better join order


**Cac Rules trong nhom:**

1. `PROJECT_SUB_QUERY_TO_CORRELATE`

2. `AGGREGATE_ANY_PULL_UP_CONSTANTS`

3. `FILTER_CORRELATE`

4. `AGGREGATE_UNION_TRANSPOSE`


**Vi du:**

- Input: `SELECT * FROM A WHERE x IN (SELECT y FROM B WHERE A.id = B.id)`

- Output: `SELECT * FROM A SemiJoin (A.id = B.id) B`

- Cong thuc: `scan(A) + (scan(B) × n_A) → scan(A) + scan(B) [neu correlated]`


**Uu diem:**

- Loại bỏ execution overhead của subquery execution engine

- Cho phép optimizer tìm better join order

- Giảm số lần quét bảng (1 lần thay vì n lần với correlated subquery)

- Đặc biệt hiệu quả với IN/EXISTS subqueries


**Nhuoc diem:**

- Correlated subqueries có thể sinh ra lượng lớn intermediate rows

- Không phải lúc nào cũng nhanh hơn — execution engine subquery đôi khi tốt hơn

- Rủi ro explosion khi LLM đề xuất unnesting không phù hợp


---

### 5. Aggregation Pushdown

**Mo ta:** Thực hiện phép tổng hợp (aggregate) càng sớm càng tốt trong câu truy vấn để giảm lượng dữ liệu cần xử lý

**Muc tieu:** Giảm số dòng cần aggregate bằng cách lọc trước rồi mới tổng hợp, giảm memory cho aggregation


**Cac Rules trong nhom:**

1. `FILTER_AGGREGATE_TRANSPOSE`

2. `AGGREGATE_JOIN_TRANSPOSE_EXTENDED`

3. `AGGREGATE_PROJECT_MERGE`

4. `AGGREGATE_EXPAND_DISTINCT_AGGREGATES`


**Vi du:**

- Input: `SELECT SUM(amount) FROM sales, date WHERE date_id = id AND year = 2024 GROUP BY category`

- Output: `SELECT SUM(amount) FROM (SELECT * FROM date WHERE year = 2024) d JOIN sales ON ... GROUP BY category`

- Cong thuc: `rows_agg = rows × selectivity(filter) × 1/group_by_cardinality`


**Uu diem:**

- Giảm số dòng cần aggregate: lọc trước rồi mới tổng hợp

- Đặc biệt hiệu quả với GROUP BY trên large tables

- Giảm memory cho aggregation vì input nhỏ hơn

- Tối ưu COUNT(DISTINCT) qua AGGREGATE_EXPAND_DISTINCT


**Nhuoc diem:**

- Có thể không hiệu quả nếu aggregate function không distributive

- LLM khó xác định khi nào pushdown aggregate là tối ưu

- Một số aggregate function (MEDIAN) không thể pushdown


---

### 6. Redundant Join Elimination

**Mo ta:** Phát hiện và loại bỏ các phép nối không cần thiết hoặc thay thế bằng semi-join để tránh tạo cartesian product không cần thiết

**Muc tieu:** Tránh các phép nối tốn kém không cần thiết trong kế hoạch truy vấn


**Cac Rules trong nhom:**

1. `SEMI_JOIN_REMOVE`

2. `UNION_REMOVE`

3. `AGGREGATE_REMOVE`

4. `PROJECT_REMOVE`

5. `SORT_REMOVE`


**Vi du:**

- Input: `SELECT * FROM A JOIN B ON A.id = B.id WHERE EXISTS (SELECT 1 FROM C WHERE C.id = A.id)`

- Output: `SELECT A.* FROM A SemiJoin (A.id = C.id) C`

- Cong thuc: `rows_full_join = rows_A × rows_B → rows_semi_join = rows_A × selectivity(C)`


**Uu diem:**

- Giảm I/O và memory rõ rệt

- Có thể tận dụng covering indexes

- Giảm chi phí network transfer

- Semi-join tránh tạo cartesian product không cần thiết


**Nhuoc diem:**

- Yêu cầu phân tích semantic chính xác của query

- LLM có thể loại sai — giữ lại cột thực sự cần thiết

- Khó phát hiện join thực sự dư thừa (cần column provenance analysis)


---

## 3. Bang dau vao — dau ra cua 6 Luat

| STT | Luat | Dau vao | Dau ra | Cong thuc xu ly |
|-----|------|---------|--------|------------------|

| 1 | Predicate Pushdown | `Filter(Join(store_sales, date_dim))` | `Join(Filter(store_sales, d_year=2001), date_dim)` | `cardinality(Filter(Join)) >> cardinality(Join(Filter))` |

| 2 | Projection Pruning | `SELECT * FROM orders, customer WHERE ...` | `SELECT c_customer_id, c_first_name FROM orders, customer WHERE ...` | `data_transfer = Σ(columns_selected / columns_total) × rows` |

| 3 | Join Reordering | `Join(Project(A), Project(B)) → Join(A, B)` | `Project(Join(A, B)) → Filter đẩy xuống từng nhánh` | `cost(join) = Σ cost(intermediate_i) + cost(join_final)` |

| 4 | Subquery Unnesting | `SELECT * FROM A WHERE x IN (SELECT y FROM B WHERE A.id = B.id)` | `SELECT * FROM A SemiJoin (A.id = B.id) B` | `scan(A) + (scan(B) × n_A) → scan(A) + scan(B) [neu correlated]` |

| 5 | Aggregation Pushdown | `SELECT SUM(amount) FROM sales, date WHERE date_id = id AND year = 2024 GROUP BY category` | `SELECT SUM(amount) FROM (SELECT * FROM date WHERE year = 2024) d JOIN sales ON ... GROUP BY category` | `rows_agg = rows × selectivity(filter) × 1/group_by_cardinality` |

| 6 | Redundant Join Elimination | `SELECT * FROM A JOIN B ON A.id = B.id WHERE EXISTS (SELECT 1 FROM C WHERE C.id = A.id)` | `SELECT A.* FROM A SemiJoin (A.id = C.id) C` | `rows_full_join = rows_A × rows_B → rows_semi_join = rows_A × selectivity(C)` |


## 4. Bang So Sanh Uu/Nhuoc Diem

| STT | Luat | Uu diem | Nhuoc diem | Dieu kien ap dung tot |
|-----|------|---------|------------|--------------------|

| 1 | Predicate Pushdown | Giam I/O, reduce memory, filter selectivity cao | Chi phi CPU cho phep day, selectivity thap thi cham hon | Filter co selectivity > 50%, nhieu bang JOIN |

| 2 | Projection Pruning | Giam bandwidth, tan dung covering indexes | LLM kho xac dinh cot can thiet, co the gay loi | Projection chon > 50% cot, nhieu bang |

| 3 | Join Reordering | Giam intermediate rows, filter som hon | Khong doi duoc thu tu bang goc, phu thuoc CBO | Nhieu hon 3 bang JOIN, co filter tren cac bang |

| 4 | Subquery Unnesting | Loai overhead subquery, giam so lan quet bang | Correlated subquery co the explosion rows | Co IN/EXISTS/ANY subquery, correlated subquery |

| 5 | Aggregation Pushdown | Giam rows aggregate, tot voi GROUP BY lon | Aggregate khong distributive thi khong pushdown duoc | Co GROUP BY tren bang lon, co filter truoc aggregate |

| 6 | Redundant Join Elimination | Tranh cartesian product, giam network transfer | Yeu cau phan tich semantic, co the loai sai cot | Co EXISTS/IN subquery, cot chi dung trong filter |


## 5. Bang Mapping Rules theo De cuong

| Luật theo đề tài | Rules tuong ung | Mo ta |
|-------------------|---------------|-------|

| Predicate Pushdown | FILTER_INTO_JOIN, JOIN_CONDITION_PUSH, FILTER_MULTI_JOIN_MERGE | Day filter xuong truoc JOIN de loc som |

| Projection Pruning | PROJECT_REMOVE, PROJECT_MERGE, PROJECT_REDUCE_EXPRESSIONS | Loai bo columns/cot khong can thiet |

| Join Reordering | JOIN_PROJECT_*_TRANSPOSE, JOIN_EXTRACT_FILTER | Day project qua join, tach filter khoi join condition |

| Subquery Unnesting | PROJECT_SUB_QUERY_TO_CORRELATE, AGGREGATE_ANY_PULL_UP_CONSTANTS | Chuyen subquery thanh JOIN/Correlate |

| Aggregation Pushdown | FILTER_AGGREGATE_TRANSPOSE, AGGREGATE_JOIN_TRANSPOSE_EXTENDED | Day aggregate qua filter/join de loc truoc |

| Redundant Join Elimination | SEMI_JOIN_REMOVE, UNION_REMOVE, AGGREGATE_REMOVE | Loai bo semi-join thua, union/aggregate khong can thiet |
