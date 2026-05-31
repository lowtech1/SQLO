"""
Dataset loader cho multi-dataset evaluation (TPC-H, DSB, JOB).
Ho tro load schemas, queries, ground truth tu cac data files.
"""

import csv
import json
import os
from typing import Optional

BASE_DIR = os.path.join(os.path.dirname(__file__), '../../data/data_llmr2')


def load_schema(schema_name: str) -> dict:
    """Load schema definitions tu data/data_llmr2/schemas/{name}.json."""
    path = os.path.join(BASE_DIR, 'schemas', f'{schema_name}.json')
    if not os.path.exists(path):
        return {}
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def load_queries_csv(dataset: str, split: str = 'test') -> list:
    """Load queries tu data/data_llmr2/queries/queries_{dataset}_{split}.csv."""
    path = os.path.join(BASE_DIR, 'queries', f'queries_{dataset}_{split}.csv')
    results = []
    if not os.path.exists(path):
        return results
    with open(path, encoding='utf-8', errors='ignore') as f:
        for i, row in enumerate(csv.DictReader(f)):
            sql = (row.get('original_sql', '') or '').strip()
            if sql:
                results.append({
                    'query_id': row.get('db_id', f'{dataset}_q{i+1}'),
                    'name': f'{dataset.title()} Query {i+1}',
                    'sql': sql,
                    'target_rules': [],
                })
    return results


def build_dsb_schema_context() -> str:
    """Build schema context string cho DSB (in-memory, khong can database)."""
    return """DSB (Star Schema Benchmark) Schema:
  - store_sales: ss_sold_date_sk, ss_item_sk, ss_customer_sk, ss_cdemo_sk, ss_hdemo_sk, ss_addr_sk, ss_store_sk, ss_ticket_number, ss_quantity, ss_ext_sales_price, ss_ext_wholesale_cost, ss_net_profit, ss_list_price
  - store_returns: sr_returned_date_sk, sr_item_sk, sr_customer_sk, sr_cdemo_sk, ss_net_profit
  - catalog_sales: cs_sold_date_sk, cs_item_sk, cs_bill_customer_sk, cs_ship_customer_sk, cs_quantity, cs_ext_sales_price, cs_net_profit
  - catalog_returns: cr_item_sk, cr_customer_sk, cr_refunded_cash
  - web_sales: ws_sold_date_sk, ws_item_sk, ws_bill_customer_sk, ws_ship_customer_sk, ws_quantity, ws_ext_sales_price, ws_net_profit
  - web_returns: wr_item_sk, wr_order_sk, wr_refunded_cash
  - customer: c_customer_sk, c_current_addr_sk, c_current_cdemo_sk, c_birth_month
  - customer_address: ca_address_sk, ca_country, ca_state, ca_county
  - customer_demographics: cd_demo_sk, cd_gender, cd_marital_status, cd_education_status, cd_purchase_estimate, cd_credit_rating, cd_dep_count, cd_dep_employed_count, cd_dep_college_count
  - date_dim: d_date_sk, d_year, d_month, d_moy, d_day
  - item: i_item_sk, i_category, i_manager_id, i_item_sk
  - store: s_store_sk, s_store_name
  - household_demographics: hd_demo_sk, hd_dep_count
  - income_band: ib_income_band_sk, ib_lower_bound, ib_upper_bound
  - promotion: p_promo_sk, p_channel_email, p_channel_demo, p_channel_tv
  - time_dim: t_time_sk, t_hour, t_minute
  - warehouse: w_warehouse_sk, w_warehouse_sq_ft
  - ship_mode: sm_ship_mode_sk, sm_type
  - reason: r_reason_sk, r_reason_desc
  - web_page: wp_web_page_sk, wp_url
  - dbgen_version: dv_version, dv_create_date
"""


def build_job_schema_context() -> str:
    """Build schema context string cho JOB (IMDB)."""
    return """JOB (IMDB Join Order Benchmark) Schema:
  - title: id, title, imdb_index, kind_id, production_year, imdb_id, phonetic_code, episode_of_id, season_nr, episode_nr, series_rank, episode_of_id, md5sum, kind, production_year
  - movie_companies: movie_id, company_id, company_type_id, note
  - cast_info: movie_id, person_id, person_role_id, nr_order, role_id
  - movie_info_idx: movie_id, info_type_id, info, note
  - movie_info: movie_id, info_type_id, info, note
  - movie_keyword: movie_id, keyword_id
  (IMDB uses integer IDs for foreign key joins)
"""


def get_schema_context(dataset: str) -> str:
    """Get schema context string cho dataset."""
    if dataset == 'dsb':
        return build_dsb_schema_context()
    elif dataset == 'job':
        return build_job_schema_context()
    elif dataset == 'tpch':
        return "TPC-H Schema: customer, orders, lineitem, supplier, part, partsupp, nation, region"
    return ""


def load_test_cases(dataset: str, split: str = 'test') -> list:
    """Load test cases cho mot dataset.

    Uu tien:
    1. test_cases.json (TPC-H, 35 hand-crafted queries)
    2. test_cases_{dataset}.json (DSB/JOB, neu co)
    3. queries_{dataset}_{split}.csv (fallback, ko co ground truth)
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    # TPC-H: always use test_cases.json (35 hand-crafted with ground truth)
    if dataset == 'tpch':
        json_path = os.path.join(base_dir, 'my_exp', 'queries', 'test_cases.json')
    else:
        json_path = os.path.join(base_dir, 'my_exp', 'queries', f'test_cases_{dataset}.json')
    if os.path.exists(json_path):
        with open(json_path, encoding='utf-8') as f:
            return json.load(f)
    return load_queries_csv(dataset, split)
