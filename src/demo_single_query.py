# ============================================================
# demo_single_query.py
# Demo trực tiếp: Chạy 1 query mẫu và so sánh
# ============================================================
import os
from dotenv import load_dotenv
load_dotenv()

import sys
sys.path.insert(0, '.')
from LLM_R2_Claude import *

# Câu query mẫu DSB - chạy nhanh để demo
demo_query = """select avg(ss_quantity), avg(ss_ext_sales_price)
from store_sales, store, customer_demographics, household_demographics,
     customer_address, date_dim
where s_store_sk = ss_store_sk and ss_sold_date_sk = d_date_sk and d_year = 2001
and ((ss_hdemo_sk=hd_demo_sk and cd_demo_sk = ss_cdemo_sk
      and cd_marital_status = 'D' and cd_education_status = '4 yr Degree'
      and ss_sales_price between 100.00 and 150.00 and hd_dep_count = 3)
     or (ss_hdemo_sk=hd_demo_sk and cd_demo_sk = ss_cdemo_sk
      and cd_marital_status = 'S' and cd_education_status = 'Advanced Degree'
      and ss_sales_price between 50.00 and 100.00 and hd_dep_count = 1))"""

print("=" * 60)
print("  LLM-R2 + Claude Opus 4.6 — Demo Truc Tiep")
print("=" * 60)
print()
print("QUERY GOC:")
print("-" * 60)
print(demo_query)
print("-" * 60)

# Buoc 1: Tao prompt cho Claude
schema = []
logical_plan = []
promo = []

prompt = generate_claude_prompt_light(schema, demo_query, logical_plan, promo)
print()
print("PROMPT GUI CHO CLAUDE:")
print("-" * 60)
# Chi in system prompt (ngan gon)
for msg in prompt:
    if msg['role'] == 'system':
        print(msg['content'][:300] + "...")
print("-" * 60)

# Buoc 2: Goi Claude
print()
print("DANG GOI CLAUDE OPUS 4.6...")
trys = 0
claude_output = query_claude_attempts(prompt, trys)
print(f"CLAUDE TRA LOI: {claude_output}")
print()

# Buoc 3: Filter rules
rules = filter_gpt_output(claude_output)
print(f"RULES HUƯ LE: {rules}")
print()

# Buoc 4: Rewrite
print("SQL SAU KHI REWRITE:")
print("-" * 60)
rewrite_sql = call_rewriter('dsb', demo_query, rules)
print(rewrite_sql if rewrite_sql != 'NA' else "[Rewrite that bai]")
print("-" * 60)

print()
print("=" * 60)
print("  KET THUC DEMO")
print("=" * 60)
