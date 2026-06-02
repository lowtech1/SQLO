"""
Setup DSB (Star Schema Benchmark) synthetic data in PostgreSQL.
Creates schemas + generates realistic synthetic data for all 24 tables.
Scale: 100-1000 rows per table (small scale for thesis evaluation).
"""
import os
import sys
import random
import psycopg2
from datetime import datetime, timedelta

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))


def get_conn(dbname='dsb'):
    return psycopg2.connect(
        host='localhost', port=5432, dbname=dbname,
        user='postgres', password='nhanpro12'
    )


def setup_dsb_schema(conn):
    """Create DSB schema in PostgreSQL."""
    cur = conn.cursor()

    # Drop existing tables
    tables = [
        'store_sales', 'store_returns', 'catalog_sales', 'catalog_returns',
        'web_sales', 'web_returns', 'customer', 'customer_address',
        'customer_demographics', 'date_dim', 'item', 'store',
        'household_demographics', 'income_band', 'promotion',
        'time_dim', 'warehouse', 'ship_mode', 'reason',
        'web_page', 'dbgen_version', 'inventory', 'catalog_page',
        'call_center'
    ]
    for t in tables:
        cur.execute(f"DROP TABLE IF EXISTS {t} CASCADE")

    # ---- Dimension Tables ----

    # date_dim: 73049 rows but we generate 365 (1 year)
    cur.execute("""
    CREATE TABLE date_dim (
        d_date_sk SERIAL PRIMARY KEY,
        d_date_id VARCHAR(20),
        d_date DATE,
        d_month_seq INTEGER,
        d_month VARCHAR(20),
        d_month_name VARCHAR(20),
        d_year INTEGER,
        d_yearmonth_seq INTEGER,
        d_day_name VARCHAR(20),
        d_day_since_1980 INTEGER,
        d_day_since_2000 INTEGER,
        d_quarter_name VARCHAR(20),
        d_dom INTEGER,
        d_dow INTEGER,
        d_doy INTEGER,
        d_week_seq INTEGER,
        d_week_since_year INTEGER,
        d_moy INTEGER,
        d_qoy INTEGER,
        d_fy_year INTEGER,
        d_fy_quarter_seq INTEGER,
        d_fy_week_seq INTEGER,
        d_quarter_seq INTEGER,
        d_same_day_year INTEGER,
        d_same_day_lq INTEGER,
        d_same_day_ly INTEGER,
        d_current_week VARCHAR(5),
        d_current_month VARCHAR(5),
        d_current_quarter VARCHAR(5),
        d_current_year VARCHAR(5),
        d_holiday VARCHAR(5),
        d_weekend VARCHAR(5),
        d_following_holiday VARCHAR(5)
    )
    """)

    # time_dim: 86400 rows but we generate 1440 (24h * 60min)
    cur.execute("""
    CREATE TABLE time_dim (
        t_time_sk SERIAL PRIMARY KEY,
        t_time_id VARCHAR(20),
        t_time INTEGER,
        t_hour INTEGER,
        t_minute INTEGER,
        t_second INTEGER,
        t_am_pm VARCHAR(5),
        t_shift VARCHAR(20),
        t_sub_shift VARCHAR(20),
        t_meal_time VARCHAR(20)
    )
    """)

    # customer_demographics: 1920800 but generate 1000
    cd_genders = ['M', 'F']
    cd_marital = ['M', 'S', 'D', 'W']
    cd_education = ['Advanced Degree', ' Bachelors', ' Masters', ' College', ' High School', ' 2 yr Degree', ' Primary', ' Partial High School', ' Partial College', ' Unknown']
    cd_credit = ['Good', 'HighIQ', 'Premium', 'Medium', 'LowRisk', 'HighRisk', 'Average']
    cur.execute("""
    CREATE TABLE customer_demographics (
        cd_demo_sk SERIAL PRIMARY KEY,
        cd_gender VARCHAR(5),
        cd_marital_status VARCHAR(5),
        cd_education_status VARCHAR(30),
        cd_purchase_estimate INTEGER,
        cd_credit_rating VARCHAR(20),
        cd_dep_count INTEGER,
        cd_dep_employed_count INTEGER,
        cd_dep_college_count INTEGER
    )
    """)

    # customer_address: 250000 -> 500
    ca_states = ['AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA',
                 'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
                 'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
                 'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
                 'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY']
    cur.execute("""
    CREATE TABLE customer_address (
        ca_address_sk SERIAL PRIMARY KEY,
        ca_address_id VARCHAR(20),
        ca_street_number VARCHAR(10),
        ca_street_name VARCHAR(100),
        ca_street_type VARCHAR(10),
        ca_suite_number VARCHAR(10),
        ca_city VARCHAR(60),
        ca_county VARCHAR(60),
        ca_state VARCHAR(5),
        ca_zip VARCHAR(10),
        ca_country VARCHAR(20),
        ca_location_type VARCHAR(20),
        ca_gmt_offset NUMERIC(5,2)
    )
    """)

    # household_demographics: 7200 -> 200
    cur.execute("""
    CREATE TABLE household_demographics (
        hd_demo_sk SERIAL PRIMARY KEY,
        hd_income_band_sk INTEGER,
        hd_buy_potential VARCHAR(30),
        hd_vehicle_count INTEGER
    )
    """)

    # income_band: 20 rows
    cur.execute("""
    CREATE TABLE income_band (
        ib_income_band_sk SERIAL PRIMARY KEY,
        ib_lower_bound INTEGER,
        ib_upper_bound INTEGER
    )
    """)

    # item: 102000 -> 500
    i_category = ['Books', 'Electronics', 'Men', 'Women', 'Home', 'Shoes', 'Sports', 'Jewelry', 'Music', 'Movies', 'Toys', 'Food']
    i_class = ['pop', 'rock', 'jazz', 'classical', 'Action', 'Drama', 'Comedy', 'Romance', 'SciFi']
    cur.execute("""
    CREATE TABLE item (
        i_item_sk SERIAL PRIMARY KEY,
        i_item_id VARCHAR(20),
        i_rec_start_date DATE,
        i_rec_end_date DATE,
        i_item_desc VARCHAR(200),
        i_current_price NUMERIC(10,2),
        i_wholesale_cost NUMERIC(10,2),
        i_brand_id INTEGER,
        i_class_id INTEGER,
        i_category_id INTEGER,
        i_manager_id INTEGER,
        i_class VARCHAR(50),
        i_category VARCHAR(50),
        i_brand VARCHAR(50),
        i_color VARCHAR(50),
        i_units VARCHAR(20),
        i_size VARCHAR(20),
        i_formulation VARCHAR(50),
        i_product_name VARCHAR(200)
    )
    """)

    # store: 102 -> 20
    cur.execute("""
    CREATE TABLE store (
        s_store_sk SERIAL PRIMARY KEY,
        s_store_id VARCHAR(20),
        s_rec_start_date DATE,
        s_rec_end_date DATE,
        s_store_name VARCHAR(100),
        s_tax_precentage NUMERIC(5,4),
        s_tax_rate NUMERIC(5,4),
        s_number_employees INTEGER,
        s_floor_space INTEGER,
        s_manager VARCHAR(100),
        s_street_number VARCHAR(10),
        s_street_name VARCHAR(100),
        s_street_type VARCHAR(10),
        s_suite_number VARCHAR(10),
        s_city VARCHAR(60),
        s_county VARCHAR(60),
        s_state VARCHAR(5),
        s_zip VARCHAR(10),
        s_country VARCHAR(30),
        s_market_id INTEGER,
        s_market_desc VARCHAR(200),
        s_division_id INTEGER,
        s_division_name VARCHAR(100),
        s_company_id INTEGER,
        s_company_name VARCHAR(100),
        s_geography_class VARCHAR(50),
        s_gmt_offset NUMERIC(5,2),
        s_closed_date_sk INTEGER
    )
    """)

    # ship_mode: 20 rows
    cur.execute("""
    CREATE TABLE ship_mode (
        sm_ship_mode_sk SERIAL PRIMARY KEY,
        sm_ship_mode_id VARCHAR(20),
        sm_type VARCHAR(100),
        sm_code VARCHAR(20),
        sm_carrier VARCHAR(100),
        sm_contract VARCHAR(20)
    )
    """)

    # reason: 45 rows
    r_reason_desc = [
        'Not available', 'Wrong color', 'Wrong size', 'Did not like',
        'Too expensive', 'Defective', 'Wrong item shipped', 'Customer changed mind',
        'Late delivery', 'Better price found', 'Quality issues', 'Missing parts'
    ]
    cur.execute("""
    CREATE TABLE reason (
        r_reason_sk SERIAL PRIMARY KEY,
        r_reason_id VARCHAR(20),
        r_reason_desc VARCHAR(200)
    )
    """)

    # warehouse: 10 rows
    cur.execute("""
    CREATE TABLE warehouse (
        w_warehouse_sk SERIAL PRIMARY KEY,
        w_warehouse_id VARCHAR(20),
        w_warehouse_name VARCHAR(100),
        w_warehouse_sq_ft INTEGER,
        w_street_number VARCHAR(10),
        w_street_name VARCHAR(100),
        w_street_type VARCHAR(10),
        w_suite_number VARCHAR(10),
        w_city VARCHAR(60),
        w_county VARCHAR(60),
        w_state VARCHAR(5),
        w_zip VARCHAR(10),
        w_country VARCHAR(30),
        w_gmt_offset NUMERIC(5,2)
    )
    """)

    # call_center: 24 rows
    cur.execute("""
    CREATE TABLE call_center (
        cc_call_center_sk SERIAL PRIMARY KEY,
        cc_call_center_id VARCHAR(20),
        cc_rec_start_date DATE,
        cc_rec_end_date DATE,
        cc_closed_date_sk INTEGER,
        cc_open_date_sk INTEGER,
        cc_name VARCHAR(100),
        cc_class VARCHAR(100),
        cc_employees INTEGER,
        cc_sq_ft INTEGER,
        cc_manager VARCHAR(100),
        cc_mkt_id INTEGER,
        cc_mkt_class VARCHAR(200),
        cc_mkt_desc VARCHAR(200),
        cc_division INTEGER,
        cc_division_name VARCHAR(100),
        cc_company INTEGER,
        cc_company_name VARCHAR(100),
        cc_street_number VARCHAR(10),
        cc_street_name VARCHAR(100),
        cc_street_type VARCHAR(10),
        cc_suite_number VARCHAR(10),
        cc_city VARCHAR(60),
        cc_county VARCHAR(60),
        cc_state VARCHAR(5),
        cc_zip VARCHAR(10),
        cc_country VARCHAR(30),
        cc_gmt_offset NUMERIC(5,2),
        cc_tax_percentage NUMERIC(5,4),
        cc_hours VARCHAR(200)
    )
    """)

    # web_page: 200 -> 30
    cur.execute("""
    CREATE TABLE web_page (
        wp_web_page_sk SERIAL PRIMARY KEY,
        wp_web_page_id VARCHAR(20),
        wp_rec_start_date DATE,
        wp_rec_end_date DATE,
        wp_creation_date_sk INTEGER,
        wp_access_date_sk INTEGER,
        wp_autogen_flag VARCHAR(5),
        wp_customer_sk INTEGER,
        wp_url VARCHAR(500),
        wp_type VARCHAR(50),
        wp_char_count INTEGER,
        wp_link_count INTEGER,
        wp_image_count INTEGER,
        wp_max_ad_count INTEGER
    )
    """)

    # promotion: 500 -> 50
    p_channel = ['P', 'N', 'E', 'T', 'C']
    p_purpose = ['P', 'G', 'N', 'C']
    cur.execute("""
    CREATE TABLE promotion (
        p_promo_sk SERIAL PRIMARY KEY,
        p_promo_id VARCHAR(20),
        p_start_date_sk INTEGER,
        p_end_date_sk INTEGER,
        p_item_sk INTEGER,
        p_cost NUMERIC(10,2),
        p_response_target INTEGER,
        p_promo_name VARCHAR(200),
        p_channel_email VARCHAR(5),
        p_channel_demo VARCHAR(5),
        p_channel_tv VARCHAR(5),
        p_channel_details VARCHAR(200),
        p_purpose VARCHAR(20),
        p_channel VARCHAR(20)
    )
    """)

    # dbgen_version: 1 row
    cur.execute("""
    CREATE TABLE dbgen_version (
        dv_version VARCHAR(20),
        dv_create_date DATE,
        dv_create_time TIME
    )
    """)

    # ---- Fact Tables ----

    # customer: 500000 -> 2000
    cur.execute("""
    CREATE TABLE customer (
        c_customer_sk SERIAL PRIMARY KEY,
        c_customer_id VARCHAR(20),
        c_current_hdemo_sk INTEGER REFERENCES household_demographics(hd_demo_sk),
        c_current_addr_sk INTEGER REFERENCES customer_address(ca_address_sk),
        c_first_shipto_date_sk INTEGER,
        c_first_sales_date_sk INTEGER,
        c_salutation VARCHAR(10),
        c_first_name VARCHAR(50),
        c_last_name VARCHAR(50),
        c_preferred_cust_flag VARCHAR(5),
        c_birth_day INTEGER,
        c_birth_month INTEGER,
        c_birth_year INTEGER,
        c_birth_country VARCHAR(60),
        c_login VARCHAR(20),
        c_email_address VARCHAR(100),
        c_last_review_date_sk INTEGER
    )
    """)

    # catalog_page: 12000 -> 200
    cur.execute("""
    CREATE TABLE catalog_page (
        cp_catalog_page_sk SERIAL PRIMARY KEY,
        cp_catalog_page_id VARCHAR(20),
        cp_start_date_sk INTEGER,
        cp_end_date_sk INTEGER,
        cp_catalog_number INTEGER,
        cp_catalog_page_number INTEGER,
        cp_department VARCHAR(100),
        cp_description VARCHAR(200),
        cp_type VARCHAR(100)
    )
    """)

    # inventory: 133110000 -> 5000
    cur.execute("""
    CREATE TABLE inventory (
        inv_date_sk INTEGER REFERENCES date_dim(d_date_sk),
        inv_item_sk INTEGER REFERENCES item(i_item_sk),
        inv_warehouse_sk INTEGER REFERENCES warehouse(w_warehouse_sk),
        inv_quantity_on_hand INTEGER
    )
    """)

    # store_sales: ~28800991 -> 5000
    cur.execute("""
    CREATE TABLE store_sales (
        ss_sold_date_sk INTEGER REFERENCES date_dim(d_date_sk),
        ss_sold_time_sk INTEGER REFERENCES time_dim(t_time_sk),
        ss_item_sk INTEGER REFERENCES item(i_item_sk),
        ss_customer_sk INTEGER REFERENCES customer(c_customer_sk),
        ss_cdemo_sk INTEGER REFERENCES customer_demographics(cd_demo_sk),
        ss_hdemo_sk INTEGER REFERENCES household_demographics(hd_demo_sk),
        ss_addr_sk INTEGER REFERENCES customer_address(ca_address_sk),
        ss_store_sk INTEGER REFERENCES store(s_store_sk),
        ss_promo_sk INTEGER REFERENCES promotion(p_promo_sk),
        ss_ticket_number INTEGER,
        ss_quantity INTEGER,
        ss_wholesale_cost NUMERIC(10,2),
        ss_list_price NUMERIC(10,2),
        ss_sales_price NUMERIC(10,2),
        ss_ext_discount_amt NUMERIC(10,2),
        ss_ext_sales_price NUMERIC(10,2),
        ss_ext_wholesale_cost NUMERIC(10,2),
        ss_ext_list_price NUMERIC(10,2),
        ss_ext_tax NUMERIC(10,2),
        ss_coupon_amt NUMERIC(10,2),
        ss_ext_ship_cost NUMERIC(10,2),
        ss_net_paid NUMERIC(10,2),
        ss_net_paid_inc_tax NUMERIC(10,2),
        ss_net_paid_inc_ship NUMERIC(10,2),
        ss_net_paid_inc_ship_tax NUMERIC(10,2),
        ss_net_profit NUMERIC(10,2)
    )
    """)

    # store_returns: 2875432 -> 1000
    cur.execute("""
    CREATE TABLE store_returns (
        sr_returned_date_sk INTEGER,
        sr_return_time_sk INTEGER,
        sr_item_sk INTEGER REFERENCES item(i_item_sk),
        sr_customer_sk INTEGER REFERENCES customer(c_customer_sk),
        sr_cdemo_sk INTEGER REFERENCES customer_demographics(cd_demo_sk),
        sr_hdemo_sk INTEGER REFERENCES household_demographics(hd_demo_sk),
        sr_addr_sk INTEGER REFERENCES customer_address(ca_address_sk),
        sr_store_sk INTEGER REFERENCES store(s_store_sk),
        sr_reason_sk INTEGER REFERENCES reason(r_reason_sk),
        sr_ticket_number INTEGER,
        sr_return_quantity INTEGER,
        sr_return_amt NUMERIC(10,2),
        sr_return_tax NUMERIC(10,2),
        sr_return_amt_inc_tax NUMERIC(10,2),
        sr_fee NUMERIC(10,2),
        sr_return_ship_cost NUMERIC(10,2),
        sr_refunded_cash NUMERIC(10,2),
        sr_reversed_charge NUMERIC(10,2),
        sr_store_credit NUMERIC(10,2),
        sr_net_loss NUMERIC(10,2)
    )
    """)

    # catalog_sales: 14401261 -> 3000
    cur.execute("""
    CREATE TABLE catalog_sales (
        cs_sold_date_sk INTEGER REFERENCES date_dim(d_date_sk),
        cs_sold_time_sk INTEGER REFERENCES time_dim(t_time_sk),
        cs_ship_date_sk INTEGER,
        cs_bill_customer_sk INTEGER REFERENCES customer(c_customer_sk),
        cs_bill_cdemo_sk INTEGER REFERENCES customer_demographics(cd_demo_sk),
        cs_bill_hdemo_sk INTEGER REFERENCES household_demographics(hd_demo_sk),
        cs_bill_addr_sk INTEGER REFERENCES customer_address(ca_address_sk),
        cs_ship_customer_sk INTEGER,
        cs_ship_cdemo_sk INTEGER,
        cs_ship_hdemo_sk INTEGER,
        cs_ship_addr_sk INTEGER,
        cs_call_center_sk INTEGER REFERENCES call_center(cc_call_center_sk),
        cs_catalog_page_sk INTEGER REFERENCES catalog_page(cp_catalog_page_sk),
        cs_ship_mode_sk INTEGER REFERENCES ship_mode(sm_ship_mode_sk),
        cs_warehouse_sk INTEGER REFERENCES warehouse(w_warehouse_sk),
        cs_item_sk INTEGER REFERENCES item(i_item_sk),
        cs_promo_sk INTEGER REFERENCES promotion(p_promo_sk),
        cs_order_number INTEGER,
        cs_quantity INTEGER,
        cs_wholesale_cost NUMERIC(10,2),
        cs_list_price NUMERIC(10,2),
        cs_sales_price NUMERIC(10,2),
        cs_ext_discount_amt NUMERIC(10,2),
        cs_ext_sales_price NUMERIC(10,2),
        cs_ext_wholesale_cost NUMERIC(10,2),
        cs_ext_list_price NUMERIC(10,2),
        cs_ext_tax NUMERIC(10,2),
        cs_coupon_amt NUMERIC(10,2),
        cs_ext_ship_cost NUMERIC(10,2),
        cs_net_paid NUMERIC(10,2),
        cs_net_paid_inc_tax NUMERIC(10,2),
        cs_net_paid_inc_ship NUMERIC(10,2),
        cs_net_paid_inc_ship_tax NUMERIC(10,2),
        cs_net_profit NUMERIC(10,2)
    )
    """)

    # catalog_returns: 1439749 -> 500
    cur.execute("""
    CREATE TABLE catalog_returns (
        cr_returned_date_sk INTEGER,
        cr_returned_time_sk INTEGER,
        cr_item_sk INTEGER REFERENCES item(i_item_sk),
        cr_refunded_customer_sk INTEGER REFERENCES customer(c_customer_sk),
        cr_refunded_cdemo_sk INTEGER REFERENCES customer_demographics(cd_demo_sk),
        cr_refunded_hdemo_sk INTEGER REFERENCES household_demographics(hd_demo_sk),
        cr_refunded_addr_sk INTEGER REFERENCES customer_address(ca_address_sk),
        cr_returning_customer_sk INTEGER,
        cr_returning_cdemo_sk INTEGER,
        cr_returning_hdemo_sk INTEGER,
        cr_returning_addr_sk INTEGER,
        cr_call_center_sk INTEGER REFERENCES call_center(cc_call_center_sk),
        cr_catalog_page_sk INTEGER REFERENCES catalog_page(cp_catalog_page_sk),
        cr_catalog_page_sk2 INTEGER,
        cr_ship_mode_sk INTEGER REFERENCES ship_mode(sm_ship_mode_sk),
        cr_warehouse_sk INTEGER REFERENCES warehouse(w_warehouse_sk),
        cr_reason_sk INTEGER REFERENCES reason(r_reason_sk),
        cr_order_number INTEGER,
        cr_return_quantity INTEGER,
        cr_return_amount NUMERIC(10,2),
        cr_return_tax NUMERIC(10,2),
        cr_return_amt_inc_tax NUMERIC(10,2),
        cr_fee NUMERIC(10,2),
        cr_return_ship_cost NUMERIC(10,2),
        cr_refunded_cash NUMERIC(10,2),
        cr_reversed_charge NUMERIC(10,2),
        cr_account_credit NUMERIC(10,2),
        cr_net_loss NUMERIC(10,2)
    )
    """)

    # web_sales: 7197566 -> 3000
    cur.execute("""
    CREATE TABLE web_sales (
        ws_sold_date_sk INTEGER REFERENCES date_dim(d_date_sk),
        ws_sold_time_sk INTEGER REFERENCES time_dim(t_time_sk),
        ws_ship_date_sk INTEGER,
        ws_item_sk INTEGER REFERENCES item(i_item_sk),
        ws_bill_customer_sk INTEGER REFERENCES customer(c_customer_sk),
        ws_bill_cdemo_sk INTEGER REFERENCES customer_demographics(cd_demo_sk),
        ws_bill_hdemo_sk INTEGER REFERENCES household_demographics(hd_demo_sk),
        ws_bill_addr_sk INTEGER REFERENCES customer_address(ca_address_sk),
        ws_ship_customer_sk INTEGER,
        ws_ship_cdemo_sk INTEGER,
        ws_ship_hdemo_sk INTEGER,
        ws_ship_addr_sk INTEGER,
        ws_web_page_sk INTEGER REFERENCES web_page(wp_web_page_sk),
        ws_web_site_sk INTEGER,
        ws_ship_mode_sk INTEGER REFERENCES ship_mode(sm_ship_mode_sk),
        ws_warehouse_sk INTEGER REFERENCES warehouse(w_warehouse_sk),
        ws_promo_sk INTEGER REFERENCES promotion(p_promo_sk),
        ws_order_number INTEGER,
        ws_quantity INTEGER,
        ws_wholesale_cost NUMERIC(10,2),
        ws_list_price NUMERIC(10,2),
        ws_sales_price NUMERIC(10,2),
        ws_ext_discount_amt NUMERIC(10,2),
        ws_ext_sales_price NUMERIC(10,2),
        ws_ext_wholesale_cost NUMERIC(10,2),
        ws_ext_list_price NUMERIC(10,2),
        ws_ext_tax NUMERIC(10,2),
        ws_coupon_amt NUMERIC(10,2),
        ws_ext_ship_cost NUMERIC(10,2),
        ws_net_paid NUMERIC(10,2),
        ws_net_paid_inc_tax NUMERIC(10,2),
        ws_net_paid_inc_ship NUMERIC(10,2),
        ws_net_paid_inc_ship_tax NUMERIC(10,2),
        ws_net_profit NUMERIC(10,2)
    )
    """)

    # web_returns: 719217 -> 500
    cur.execute("""
    CREATE TABLE web_returns (
        wr_returned_date_sk INTEGER,
        wr_returned_time_sk INTEGER,
        wr_item_sk INTEGER REFERENCES item(i_item_sk),
        wr_refunded_customer_sk INTEGER REFERENCES customer(c_customer_sk),
        wr_refunded_cdemo_sk INTEGER REFERENCES customer_demographics(cd_demo_sk),
        wr_refunded_hdemo_sk INTEGER REFERENCES household_demographics(hd_demo_sk),
        wr_refunded_addr_sk INTEGER REFERENCES customer_address(ca_address_sk),
        wr_returning_customer_sk INTEGER,
        wr_returning_cdemo_sk INTEGER,
        wr_returning_hdemo_sk INTEGER,
        wr_returning_addr_sk INTEGER,
        wr_web_page_sk INTEGER REFERENCES web_page(wp_web_page_sk),
        wr_reason_sk INTEGER REFERENCES reason(r_reason_sk),
        wr_order_number INTEGER,
        wr_return_quantity INTEGER,
        wr_return_amt NUMERIC(10,2),
        wr_return_tax NUMERIC(10,2),
        wr_return_amt_inc_tax NUMERIC(10,2),
        wr_fee NUMERIC(10,2),
        wr_return_ship_cost NUMERIC(10,2),
        wr_refunded_cash NUMERIC(10,2),
        wr_reversed_charge NUMERIC(10,2),
        wr_account_credit NUMERIC(10,2),
        wr_net_loss NUMERIC(10,2)
    )
    """)

    conn.commit()
    print("[OK] DSB schema created")
    return {
        'cd_genders': cd_genders,
        'cd_marital': cd_marital,
        'cd_education': cd_education,
        'cd_credit': cd_credit,
        'ca_states': ca_states,
        'i_category': i_category,
        'i_class': i_class,
        'p_channel': p_channel,
        'p_purpose': p_purpose,
    }


def generate_date_dim(conn, n=730):
    """Generate date_dim: n days"""
    cur = conn.cursor()
    start = datetime(2001, 1, 1)
    months = ['January', 'February', 'March', 'April', 'May', 'June',
              'July', 'August', 'September', 'October', 'November', 'December']
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    quarters = ['Q1', 'Q2', 'Q3', 'Q4']
    for i in range(n):
        d = start + timedelta(days=i)
        dow = d.weekday()
        dom = d.day
        moy = d.month
        qoy = (moy - 1) // 3 + 1
        fy = 2001 + (i // 365)
        cur.execute("""
            INSERT INTO date_dim (d_date_sk, d_date_id, d_date, d_month_seq, d_month, d_month_name,
                d_year, d_yearmonth_seq, d_day_name, d_day_since_1980, d_day_since_2000,
                d_quarter_name, d_dom, d_dow, d_doy, d_week_seq, d_week_since_year,
                d_moy, d_qoy, d_fy_year, d_fy_quarter_seq, d_fy_week_seq, d_quarter_seq,
                d_same_day_year, d_same_day_lq, d_same_day_ly, d_current_week, d_current_month,
                d_current_quarter, d_current_year, d_holiday, d_weekend, d_following_holiday
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            i+1, f'd{i+1:05d}', d.date(), i//30, months[moy-1], months[moy-1],
            d.year, i//30, days[dow], i, 365+i,
            quarters[qoy-1], dom, dow, d.timetuple().tm_yday, i//7, i//7,
            moy, qoy, fy, qoy, i//7, i//90,
            i % 365,
            (i-90) % 365 if i >= 90 else 365+(i-90),
            (i-365) if i >= 365 else i,
            'Y' if dow < 5 else 'N', 'Y', 'Y', 'Y', i//7,
            'N', 'N' if dow < 5 else 'Y', 'N'
        ))
    conn.commit()
    print(f"[OK] date_dim: {n} rows")


def generate_time_dim(conn, n=1440):
    """Generate time_dim: n minutes in a day"""
    cur = conn.cursor()
    for h in range(24):
        for m in range(60):
            t = h * 3600 + m * 60
            ampm = 'AM' if h < 12 else 'PM'
            shift = 'morning' if 6 <= h < 12 else ('afternoon' if 12 <= h < 18 else ('evening' if 18 <= h < 22 else 'night'))
            cur.execute("""
                INSERT INTO time_dim (t_time_sk, t_time_id, t_time, t_hour, t_minute, t_second, t_am_pm, t_shift, t_sub_shift, t_meal_time)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (h*60+m+1, f't{h*60+m+1:05d}', t, h, m, 0, ampm, shift, shift, 'breakfast' if h == 8 else ('lunch' if h == 12 else ('dinner' if h == 18 else ''))))
    conn.commit()
    print(f"[OK] time_dim: {n} rows")


def generate_customer_demographics(conn, n=1000, seed=42):
    random.seed(seed)
    cur = conn.cursor()
    genders = ['M', 'F']
    marital = ['M', 'S', 'D', 'W']
    education = ['Advanced Degree', ' Bachelors', ' Masters', ' College', ' High School', ' 2 yr Degree', ' Primary', ' Partial High School', ' Partial College', ' Unknown']
    credit = ['Good', 'HighIQ', 'Premium', 'Medium', 'LowRisk', 'HighRisk', 'Average']
    for i in range(n):
        cur.execute("""
            INSERT INTO customer_demographics (cd_gender, cd_marital_status, cd_education_status,
                cd_purchase_estimate, cd_credit_rating, cd_dep_count, cd_dep_employed_count, cd_dep_college_count)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            random.choice(genders), random.choice(marital), random.choice(education),
            random.randint(100, 50000), random.choice(credit),
            random.randint(0, 5), random.randint(0, 4), random.randint(0, 4)
        ))
    conn.commit()
    print(f"[OK] customer_demographics: {n} rows")


def generate_customer_address(conn, n=500, seed=43):
    random.seed(seed)
    cur = conn.cursor()
    states = ['AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA',
              'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
              'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
              'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
              'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY']
    streets = ['Main', 'Oak', 'Maple', 'Cedar', 'Pine', 'Elm', 'Washington', 'Park', 'Lake', 'Hill',
               'First', 'Second', 'Third', 'Fourth', 'Fifth', 'Market', 'Sunset', 'Broadway', 'Center', 'River']
    street_types = ['St', 'Ave', 'Rd', 'Blvd', 'Dr', 'Ln', 'Way', 'Ct']
    cities = ['New York', 'Los Angeles', 'Chicago', 'Houston', 'Phoenix', 'Philadelphia', 'San Antonio', 'San Diego',
              'Dallas', 'San Jose', 'Austin', 'Jacksonville', 'Fort Worth', 'Columbus', 'Charlotte',
              'San Francisco', 'Indianapolis', 'Seattle', 'Denver', 'Boston']
    counties = ['Los Angeles County', 'Cook County', 'Harris County', 'Maricopa County', 'Orange County',
                'Clark County', 'King County', 'San Diego County', 'Orange County', 'Miami-Dade County']
    for i in range(n):
        cur.execute("""
            INSERT INTO customer_address (ca_address_id, ca_street_number, ca_street_name, ca_street_type,
                ca_suite_number, ca_city, ca_county, ca_state, ca_zip, ca_country, ca_location_type, ca_gmt_offset)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            f'a{i+1:06d}', str(random.randint(1, 9999)), random.choice(streets), random.choice(street_types),
            f'{random.randint(1,200)}', random.choice(cities), random.choice(counties), random.choice(states),
            f'{random.randint(10000,99999)}', 'United States', random.choice(['urban', 'suburban', 'rural']),
            round(random.uniform(-8.0, -5.0), 2)
        ))
    conn.commit()
    print(f"[OK] customer_address: {n} rows")


def generate_household_demographics(conn, n=200, seed=44):
    random.seed(seed)
    cur = conn.cursor()
    potentials = ['0-500', '1001-2000', '5001-10000', '1001-2000', '5000-10000', '10000+', 'unknown', '0']
    for i in range(n):
        cur.execute("""
            INSERT INTO household_demographics (hd_income_band_sk, hd_buy_potential, hd_vehicle_count)
            VALUES (%s,%s,%s)
        """, (i+1, random.choice(potentials), random.randint(0, 4)))
    conn.commit()
    print(f"[OK] household_demographics: {n} rows")


def generate_income_band(conn):
    cur = conn.cursor()
    bands = [(0, 10000), (10001, 20000), (20001, 30000), (30001, 40000), (40001, 50000),
             (50001, 60000), (60001, 70000), (70001, 80000), (80001, 90000), (90001, 100000),
             (100001, 110000), (110001, 120000), (120001, 130000), (130001, 140000), (140001, 150000),
             (150001, 160000), (160001, 170000), (170001, 180000), (180001, 190000), (190001, 200000)]
    for lb, ub in bands:
        cur.execute("INSERT INTO income_band (ib_lower_bound, ib_upper_bound) VALUES (%s,%s)", (lb, ub))
    conn.commit()
    print("[OK] income_band: 20 rows")


def generate_item(conn, n=500, seed=45):
    random.seed(seed)
    cur = conn.cursor()
    category = ['Books', 'Electronics', 'Men', 'Women', 'Home', 'Shoes', 'Sports', 'Jewelry', 'Music', 'Movies', 'Toys', 'Food']
    item_class = ['pop', 'rock', 'jazz', 'classical', 'Action', 'Drama', 'Comedy', 'Romance', 'SciFi', 'Horror', 'Thriller', 'Documentary']
    brands = ['Brand#1', 'Brand#2', 'Brand#3', 'Brand#4', 'Brand#5', 'Generic', 'Premium', 'Economy']
    colors = ['white', 'black', 'red', 'blue', 'green', 'yellow', 'brown', 'grey', 'pink', 'purple']
    units = ['CASE', 'BOX', 'PKG', 'UNIT', 'SET', 'DOZ']
    for i in range(n):
        price = round(random.uniform(5.0, 500.0), 2)
        cost = round(price * random.uniform(0.4, 0.8), 2)
        cur.execute("""
            INSERT INTO item (i_item_id, i_rec_start_date, i_rec_end_date, i_item_desc,
                i_current_price, i_wholesale_cost, i_brand_id, i_class_id, i_category_id, i_manager_id,
                i_class, i_category, i_brand, i_color, i_units, i_size, i_formulation, i_product_name)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            f'P{random.randint(1,500):09d}',
            datetime(2000, 1, 1).date(), datetime(2025, 12, 31).date(),
            f'Product description for item {i+1}',
            price, cost, random.randint(1, 1000), random.randint(1, 50),
            random.randint(1, 50), random.randint(1, 10),
            random.choice(item_class), random.choice(category), random.choice(brands),
            random.choice(colors), random.choice(units),
            random.choice(['S', 'M', 'L', 'XL', 'ONE SIZE']),
            random.choice(['liquid', 'solid', 'gas', 'powder', 'tablet']),
            f'Product Name {i+1}'
        ))
    conn.commit()
    print(f"[OK] item: {n} rows")


def generate_store(conn, n=20, seed=46):
    random.seed(seed)
    cur = conn.cursor()
    store_names = ['Store#' + str(i+1) for i in range(n)]
    for i in range(n):
        cur.execute("""
            INSERT INTO store (s_store_id, s_rec_start_date, s_rec_end_date, s_store_name,
                s_tax_precentage, s_number_employees, s_floor_space, s_manager,
                s_street_number, s_street_type, s_suite_number,
                s_city, s_county, s_state, s_zip, s_country, s_market_id,
                s_market_desc, s_division_id, s_division_name, s_company_id, s_company_name,
                s_geography_class, s_gmt_offset)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            f'S{random.randint(1,50):04d}', datetime(1998, 1, 1).date(), datetime(2025, 12, 31).date(),
            store_names[i], round(random.uniform(0.001, 0.10), 4),
            random.randint(50, 500), random.randint(30000, 150000), f'Manager {i+1}',
            str(random.randint(1, 9999)),
            random.choice(['St', 'Ave', 'Blvd']), f'{random.randint(1,200)}',
            random.choice(['New York', 'Los Angeles', 'Chicago', 'Houston', 'Phoenix']),
            'County', random.choice(['NY', 'CA', 'IL', 'TX', 'AZ']),
            f'{random.randint(10000,99999)}', 'USA',
            i+1, f'Market description {i+1}', i+1, f'Division {i+1}',
            i+1, f'Company {i+1}', 'class A', round(random.uniform(-8.0, -5.0), 2)
        ))
    conn.commit()
    print(f"[OK] store: {n} rows")


def generate_ship_mode(conn):
    cur = conn.cursor()
    sm_types = ['REG AIR', 'EXPRESS AIR', 'SHIP', 'POST', 'RAIL', 'TRUCK', 'COURIER', 'FOB']
    carriers = ['AAAAVACUUUM', 'BBBB2 EXPRESS', 'CCCC3 AIR', 'UPS', 'FEDEX', 'DHL', 'USPS', 'ROYAL']
    for i, (t, c) in enumerate(zip(sm_types, carriers)):
        cur.execute("""
            INSERT INTO ship_mode (sm_ship_mode_id, sm_type, sm_code, sm_carrier, sm_contract)
            VALUES (%s,%s,%s,%s,%s)
        """, (f'SM{i+1:02d}', t, t[:2], c, random.choice(['YES', 'NO', 'MONTHLY', 'ANNUAL'])))
    conn.commit()
    print("[OK] ship_mode: 20 rows")


def generate_reason(conn):
    cur = conn.cursor()
    descs = ['Not available', 'Wrong color', 'Wrong size', 'Did not like', 'Too expensive',
             'Defective', 'Wrong item shipped', 'Customer changed mind', 'Late delivery',
             'Better price found', 'Quality issues', 'Missing parts', 'Exceeded deadline',
             'Damaged in shipping', 'Wrong address', 'Out of stock refund']
    for i, d in enumerate(descs):
        cur.execute("INSERT INTO reason (r_reason_id, r_reason_desc) VALUES (%s,%s)",
                    (f'R{i+1:02d}', d))
    conn.commit()
    print("[OK] reason: 16 rows")


def generate_warehouse(conn):
    cur = conn.cursor()
    for i in range(10):
        cur.execute("""
            INSERT INTO warehouse (w_warehouse_id, w_warehouse_name, w_warehouse_sq_ft,
                w_street_name, w_city, w_state, w_zip, w_country, w_gmt_offset)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (f'W{i+1:03d}', f'Warehouse {i+1}', random.randint(100000, 500000),
              random.choice(['Main St', 'Industrial Blvd', 'Commerce Way']),
              random.choice(['New York', 'Los Angeles', 'Chicago', 'Dallas', 'Seattle']),
              random.choice(['NY', 'CA', 'IL', 'TX', 'WA']),
              f'{random.randint(10000,99999)}', 'USA', round(random.uniform(-8.0, -5.0), 2)))
    conn.commit()
    print("[OK] warehouse: 10 rows")


def generate_call_center(conn):
    cur = conn.cursor()
    cc_names = [f'CallCenter#{i+1}' for i in range(24)]
    for i in range(24):
        cur.execute("""
            INSERT INTO call_center (cc_call_center_id, cc_rec_start_date, cc_rec_end_date,
                cc_name, cc_class, cc_employees, cc_sq_ft, cc_manager, cc_mkt_id,
                cc_mkt_class, cc_mkt_desc, cc_division, cc_division_name, cc_company, cc_company_name,
                cc_street_name, cc_city, cc_county, cc_state, cc_zip, cc_country, cc_gmt_offset,
                cc_tax_percentage, cc_hours)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            f'CC{i+1:02d}', datetime(1998, 1, 1).date(), datetime(2025, 12, 31).date(),
            cc_names[i], random.choice(['small', 'medium', 'large', 'extra large']),
            random.randint(10, 200), random.randint(5000, 50000), f'Manager {i+1}',
            i+1, f'Class {i+1}', f'Market description {i+1}', i+1, f'Division {i+1}',
            i+1, f'Company {i+1}',
            random.choice(['Main St', 'Commerce Blvd', 'Industrial Way']),
            random.choice(['New York', 'Los Angeles', 'Chicago']),
            'County', random.choice(['NY', 'CA', 'IL']),
            f'{random.randint(10000,99999)}', 'USA',
            round(random.uniform(-8.0, -5.0), 2),
            round(random.uniform(0.001, 0.10), 4),
            '8am-8pm'
        ))
    conn.commit()
    print("[OK] call_center: 24 rows")


def generate_web_page(conn, n=30, seed=47):
    random.seed(seed)
    cur = conn.cursor()
    for i in range(n):
        cur.execute("""
            INSERT INTO web_page (wp_web_page_id, wp_rec_start_date, wp_rec_end_date,
                wp_url, wp_type, wp_char_count, wp_link_count, wp_image_count, wp_max_ad_count,
                wp_autogen_flag, wp_customer_sk)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            f'WP{i+1:04d}', datetime(2000, 1, 1).date(), datetime(2025, 12, 31).date(),
            f'http://www.example.com/page{i+1}',
            random.choice(['template', 'account', 'home', 'product', 'checkout']),
            random.randint(500, 50000), random.randint(10, 500), random.randint(0, 100),
            random.randint(0, 20), random.choice(['Y', 'N']), random.randint(1, 2000)
        ))
    conn.commit()
    print(f"[OK] web_page: {n} rows")


def generate_promotion(conn, n=50, seed=48):
    random.seed(seed)
    cur = conn.cursor()
    channel = ['P', 'N', 'E', 'T', 'C']
    purpose = ['P', 'G', 'N', 'C']
    for i in range(n):
        cur.execute("""
            INSERT INTO promotion (p_promo_id, p_start_date_sk, p_end_date_sk, p_item_sk,
                p_cost, p_response_target, p_promo_name, p_channel_email, p_channel_demo,
                p_channel_tv, p_channel_details, p_purpose, p_channel)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            f'P{random.randint(1,1000):09d}', random.randint(1, 365), random.randint(366, 730),
            random.randint(1, 500), round(random.uniform(50.0, 5000.0), 2),
            random.randint(100, 10000), f'Promotion {i+1}',
            random.choice(['Y', 'N']), random.choice(['Y', 'N']),
            random.choice(['Y', 'N']), f'Details for promo {i+1}',
            random.choice(purpose), random.choice(channel)
        ))
    conn.commit()
    print(f"[OK] promotion: {n} rows")


def generate_dbgen_version(conn):
    cur = conn.cursor()
    cur.execute("INSERT INTO dbgen_version (dv_version, dv_create_date, dv_create_time) VALUES (%s,%s,%s)",
                ('VERSION 2.11.0', datetime(2020, 1, 1).date(), datetime(2020, 1, 1).time()))
    conn.commit()
    print("[OK] dbgen_version: 1 row")


def generate_customer(conn, n=2000, seed=49):
    random.seed(seed)
    cur = conn.cursor()
    salutations = ['Mr.', 'Ms.', 'Mrs.', 'Dr.', 'Prof.']
    first = ['James', 'Mary', 'John', 'Patricia', 'Robert', 'Jennifer', 'Michael', 'Linda',
             'William', 'Elizabeth', 'David', 'Barbara', 'Richard', 'Susan', 'Joseph', 'Jessica',
             'Thomas', 'Sarah', 'Charles', 'Karen', 'Christopher', 'Nancy', 'Daniel', 'Lisa']
    last = ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis',
            'Rodriguez', 'Martinez', 'Hernandez', 'Lopez', 'Gonzalez', 'Wilson', 'Anderson', 'Thomas',
            'Taylor', 'Moore', 'Jackson', 'Martin']
    for i in range(n):
        cur.execute("""
            INSERT INTO customer (c_customer_id, c_current_hdemo_sk, c_current_addr_sk,
                c_first_shipto_date_sk, c_first_sales_date_sk, c_salutation, c_first_name,
                c_last_name, c_preferred_cust_flag, c_birth_day, c_birth_month, c_birth_year,
                c_birth_country, c_login, c_email_address, c_last_review_date_sk)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            f'C{random.randint(1,2000):010d}',
            random.randint(1, 200), random.randint(1, 500),
            random.randint(1, 365), random.randint(1, 365),
            random.choice(salutations), random.choice(first), random.choice(last),
            random.choice(['Y', 'N']),
            random.randint(1, 28), random.randint(1, 12), random.randint(1940, 2000),
            'United States', f'user{i+1}', f'user{i+1}@example.com', random.randint(300, 365)
        ))
    conn.commit()
    print(f"[OK] customer: {n} rows")


def generate_catalog_page(conn, n=200, seed=50):
    random.seed(seed)
    cur = conn.cursor()
    for i in range(n):
        cur.execute("""
            INSERT INTO catalog_page (cp_catalog_page_id, cp_start_date_sk, cp_end_date_sk,
                cp_catalog_number, cp_catalog_page_number, cp_department, cp_description, cp_type)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            f'CP{i+1:05d}', random.randint(1, 365), random.randint(366, 730),
            random.randint(1, 10), i+1,
            random.choice(['Electronics', 'Books', 'Home', 'Sports', 'Toys', 'Clothing']),
            f'Catalog page {i+1} description', random.choice(['CATALOG', 'WEB', 'BOTH'])
        ))
    conn.commit()
    print(f"[OK] catalog_page: {n} rows")


def generate_inventory(conn, n=5000, seed=51):
    random.seed(seed)
    cur = conn.cursor()
    for i in range(n):
        cur.execute("""
            INSERT INTO inventory (inv_date_sk, inv_item_sk, inv_warehouse_sk, inv_quantity_on_hand)
            VALUES (%s,%s,%s,%s)
        """, (random.randint(1, 365), random.randint(1, 500), random.randint(1, 10), random.randint(0, 100)))
    conn.commit()
    print(f"[OK] inventory: {n} rows")


def generate_store_sales(conn, n=5000, seed=52):
    random.seed(seed)
    cur = conn.cursor()
    for i in range(n):
        date_sk = random.randint(1, 365)
        item_sk = random.randint(1, 500)
        cust_sk = random.randint(1, 2000)
        store_sk = random.randint(1, 20)
        cdemo_sk = random.randint(1, 1000)
        hdemo_sk = random.randint(1, 200)
        addr_sk = random.randint(1, 500)
        promo_sk = random.randint(1, 50)
        qty = random.randint(1, 20)
        list_price = round(random.uniform(5.0, 500.0), 2)
        disc = round(list_price * random.uniform(0.0, 0.3), 2)
        sales = round(list_price - disc, 2)
        cost = round(list_price * random.uniform(0.4, 0.8), 2)
        profit = round(sales - cost - disc, 2)
        cur.execute("""
            INSERT INTO store_sales (ss_sold_date_sk, ss_sold_time_sk, ss_item_sk, ss_customer_sk,
                ss_cdemo_sk, ss_hdemo_sk, ss_addr_sk, ss_store_sk, ss_promo_sk, ss_ticket_number,
                ss_quantity, ss_wholesale_cost, ss_list_price, ss_sales_price, ss_ext_discount_amt,
                ss_ext_sales_price, ss_ext_wholesale_cost, ss_ext_list_price, ss_ext_tax,
                ss_coupon_amt, ss_ext_ship_cost, ss_net_paid, ss_net_paid_inc_tax, ss_net_paid_inc_ship,
                ss_net_paid_inc_ship_tax, ss_net_profit)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            date_sk, random.randint(1, 1440), item_sk, cust_sk,
            cdemo_sk, hdemo_sk, addr_sk, store_sk, promo_sk, random.randint(100000, 999999),
            qty, cost, list_price, sales, disc,
            sales, cost, list_price, round(sales * 0.08, 2),
            round(disc * 0.1, 2), round(sales * 0.05, 2),
            sales, round(sales * 1.08, 2), round(sales * 1.1, 2),
            round(sales * 1.15, 2), profit
        ))
    conn.commit()
    print(f"[OK] store_sales: {n} rows")


def generate_store_returns(conn, n=1000, seed=53):
    random.seed(seed)
    cur = conn.cursor()
    for i in range(n):
        qty = random.randint(1, 5)
        amt = round(random.uniform(5.0, 500.0), 2)
        cur.execute("""
            INSERT INTO store_returns (sr_returned_date_sk, sr_return_time_sk, sr_item_sk,
                sr_customer_sk, sr_cdemo_sk, sr_hdemo_sk, sr_addr_sk, sr_store_sk, sr_reason_sk,
                sr_ticket_number, sr_return_quantity, sr_return_amt, sr_return_tax,
                sr_return_amt_inc_tax, sr_fee, sr_return_ship_cost, sr_refunded_cash,
                sr_reversed_charge, sr_store_credit, sr_net_loss)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            random.randint(1, 365), random.randint(1, 1440),
            random.randint(1, 500), random.randint(1, 2000),
            random.randint(1, 1000), random.randint(1, 200), random.randint(1, 500),
            random.randint(1, 20), random.randint(1, 16),
            random.randint(100000, 999999), qty, amt, round(amt * 0.08, 2),
            round(amt * 1.08, 2), round(amt * 0.02, 2), round(amt * 0.05, 2),
            round(amt * 0.8, 2), round(amt * 0.1, 2), round(amt * 0.1, 2), round(amt * 0.1, 2)
        ))
    conn.commit()
    print(f"[OK] store_returns: {n} rows")


def generate_catalog_sales(conn, n=3000, seed=54):
    random.seed(seed)
    cur = conn.cursor()
    for i in range(n):
        date_sk = random.randint(1, 365)
        item_sk = random.randint(1, 500)
        cust_sk = random.randint(1, 2000)
        qty = random.randint(1, 10)
        list_price = round(random.uniform(5.0, 500.0), 2)
        disc = round(list_price * random.uniform(0.0, 0.3), 2)
        sales = round(list_price - disc, 2)
        cost = round(list_price * random.uniform(0.4, 0.8), 2)
        cur.execute("""
            INSERT INTO catalog_sales (cs_sold_date_sk, cs_sold_time_sk, cs_ship_date_sk,
                cs_bill_customer_sk, cs_bill_cdemo_sk, cs_bill_hdemo_sk, cs_bill_addr_sk,
                cs_ship_customer_sk, cs_ship_cdemo_sk, cs_ship_hdemo_sk, cs_ship_addr_sk,
                cs_call_center_sk, cs_catalog_page_sk, cs_ship_mode_sk, cs_warehouse_sk,
                cs_item_sk, cs_promo_sk, cs_order_number, cs_quantity,
                cs_wholesale_cost, cs_list_price, cs_sales_price, cs_ext_discount_amt,
                cs_ext_sales_price, cs_ext_wholesale_cost, cs_ext_list_price, cs_ext_tax,
                cs_coupon_amt, cs_ext_ship_cost, cs_net_paid, cs_net_paid_inc_tax,
                cs_net_paid_inc_ship, cs_net_paid_inc_ship_tax, cs_net_profit)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            date_sk, random.randint(1, 1440), date_sk + random.randint(1, 7),
            cust_sk, random.randint(1, 1000), random.randint(1, 200), random.randint(1, 500),
            cust_sk, random.randint(1, 1000), random.randint(1, 200), random.randint(1, 500),
            random.randint(1, 24), random.randint(1, 200), random.randint(1, 8), random.randint(1, 10),
            item_sk, random.randint(1, 50), random.randint(100000, 999999), qty,
            cost, list_price, sales, disc,
            sales, cost, list_price, round(sales * 0.08, 2),
            round(disc * 0.1, 2), round(sales * 0.1, 2),
            sales, round(sales * 1.08, 2), round(sales * 1.15, 2),
            round(sales * 1.20, 2), round(sales - cost, 2)
        ))
    conn.commit()
    print(f"[OK] catalog_sales: {n} rows")


def generate_catalog_returns(conn, n=500, seed=55):
    random.seed(seed)
    cur = conn.cursor()
    for i in range(n):
        amt = round(random.uniform(5.0, 500.0), 2)
        cur.execute("""
            INSERT INTO catalog_returns (cr_returned_date_sk, cr_returned_time_sk, cr_item_sk,
                cr_refunded_customer_sk, cr_refunded_cdemo_sk, cr_refunded_hdemo_sk, cr_refunded_addr_sk,
                cr_returning_customer_sk, cr_returning_cdemo_sk, cr_returning_hdemo_sk, cr_returning_addr_sk,
                cr_call_center_sk, cr_catalog_page_sk, cr_catalog_page_sk2, cr_ship_mode_sk, cr_warehouse_sk,
                cr_reason_sk, cr_order_number, cr_return_quantity, cr_return_amount, cr_return_tax,
                cr_return_amt_inc_tax, cr_fee, cr_return_ship_cost, cr_refunded_cash,
                cr_reversed_charge, cr_account_credit, cr_net_loss)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            random.randint(1, 365), random.randint(1, 1440), random.randint(1, 500),
            random.randint(1, 2000), random.randint(1, 1000), random.randint(1, 200), random.randint(1, 500),
            random.randint(1, 2000), random.randint(1, 1000), random.randint(1, 200), random.randint(1, 500),
            random.randint(1, 24), random.randint(1, 200), random.randint(1, 200),
            random.randint(1, 8), random.randint(1, 10),
            random.randint(1, 16), random.randint(100000, 999999), random.randint(1, 5),
            amt, round(amt * 0.08, 2), round(amt * 1.08, 2),
            round(amt * 0.02, 2), round(amt * 0.05, 2), round(amt * 0.8, 2),
            round(amt * 0.1, 2), round(amt * 0.1, 2), round(amt * 0.1, 2)
        ))
    conn.commit()
    print(f"[OK] catalog_returns: {n} rows")


def generate_web_sales(conn, n=3000, seed=56):
    random.seed(seed)
    cur = conn.cursor()
    for i in range(n):
        date_sk = random.randint(1, 365)
        item_sk = random.randint(1, 500)
        cust_sk = random.randint(1, 2000)
        qty = random.randint(1, 10)
        list_price = round(random.uniform(5.0, 500.0), 2)
        disc = round(list_price * random.uniform(0.0, 0.3), 2)
        sales = round(list_price - disc, 2)
        cost = round(list_price * random.uniform(0.4, 0.8), 2)
        cur.execute("""
            INSERT INTO web_sales (ws_sold_date_sk, ws_sold_time_sk, ws_ship_date_sk,
                ws_item_sk, ws_bill_customer_sk, ws_bill_cdemo_sk, ws_bill_hdemo_sk, ws_bill_addr_sk,
                ws_ship_customer_sk, ws_ship_cdemo_sk, ws_ship_hdemo_sk, ws_ship_addr_sk,
                ws_web_page_sk, ws_web_site_sk, ws_ship_mode_sk, ws_warehouse_sk,
                ws_promo_sk, ws_order_number, ws_quantity,
                ws_wholesale_cost, ws_list_price, ws_sales_price, ws_ext_discount_amt,
                ws_ext_sales_price, ws_ext_wholesale_cost, ws_ext_list_price, ws_ext_tax,
                ws_coupon_amt, ws_ext_ship_cost, ws_net_paid, ws_net_paid_inc_tax,
                ws_net_paid_inc_ship, ws_net_paid_inc_ship_tax, ws_net_profit)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            date_sk, random.randint(1, 1440), date_sk + random.randint(1, 5),
            item_sk, cust_sk, random.randint(1, 1000), random.randint(1, 200), random.randint(1, 500),
            cust_sk, random.randint(1, 1000), random.randint(1, 200), random.randint(1, 500),
            random.randint(1, 30), random.randint(1, 5), random.randint(1, 8), random.randint(1, 10),
            random.randint(1, 50), random.randint(100000, 999999), qty,
            cost, list_price, sales, disc,
            sales, cost, list_price, round(sales * 0.08, 2),
            round(disc * 0.1, 2), round(sales * 0.05, 2),
            sales, round(sales * 1.08, 2), round(sales * 1.10, 2),
            round(sales * 1.15, 2), round(sales - cost, 2)
        ))
    conn.commit()
    print(f"[OK] web_sales: {n} rows")


def generate_web_returns(conn, n=500, seed=57):
    random.seed(seed)
    cur = conn.cursor()
    for i in range(n):
        amt = round(random.uniform(5.0, 500.0), 2)
        cur.execute("""
            INSERT INTO web_returns (wr_returned_date_sk, wr_returned_time_sk, wr_item_sk,
                wr_refunded_customer_sk, wr_refunded_cdemo_sk, wr_refunded_hdemo_sk, wr_refunded_addr_sk,
                wr_returning_customer_sk, wr_returning_cdemo_sk, wr_returning_hdemo_sk, wr_returning_addr_sk,
                wr_web_page_sk, wr_reason_sk, wr_order_number, wr_return_quantity,
                wr_return_amt, wr_return_tax, wr_return_amt_inc_tax, wr_fee,
                wr_return_ship_cost, wr_refunded_cash, wr_reversed_charge, wr_account_credit, wr_net_loss)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            random.randint(1, 365), random.randint(1, 1440), random.randint(1, 500),
            random.randint(1, 2000), random.randint(1, 1000), random.randint(1, 200), random.randint(1, 500),
            random.randint(1, 2000), random.randint(1, 1000), random.randint(1, 200), random.randint(1, 500),
            random.randint(1, 30), random.randint(1, 16), random.randint(100000, 999999), random.randint(1, 5),
            amt, round(amt * 0.08, 2), round(amt * 1.08, 2), round(amt * 0.02, 2),
            round(amt * 0.05, 2), round(amt * 0.8, 2), round(amt * 0.1, 2), round(amt * 0.1, 2), round(amt * 0.1, 2)
        ))
    conn.commit()
    print(f"[OK] web_returns: {n} rows")


def run():
    """Setup DSB database with synthetic data."""
    import time
    t0 = time.time()

    # Create database
    try:
        conn0 = psycopg2.connect(host='localhost', port=5432, dbname='postgres',
                                  user='postgres', password='nhanpro12')
        conn0.set_session(autocommit=True)
        cur0 = conn0.cursor()
        cur0.execute("DROP DATABASE IF EXISTS dsb")
        cur0.execute("CREATE DATABASE dsb")
        cur0.close()
        conn0.close()
        print("[OK] Database 'dsb' created")
    except Exception as e:
        print(f"[WARN] Could not create database: {e}")
        return

    conn = get_conn('dsb')

    print("=== Creating DSB Schema ===")
    setup_dsb_schema(conn)

    print("\n=== Generating Synthetic Data ===")
    generate_date_dim(conn, 730)
    generate_time_dim(conn, 1440)
    generate_customer_demographics(conn, 1000)
    generate_customer_address(conn, 500)
    generate_household_demographics(conn, 200)
    generate_income_band(conn)
    generate_item(conn, 500)
    generate_store(conn, 20)
    generate_ship_mode(conn)
    generate_reason(conn)
    generate_warehouse(conn)
    generate_call_center(conn)
    generate_web_page(conn, 30)
    generate_promotion(conn, 50)
    generate_dbgen_version(conn)
    generate_customer(conn, 2000)
    generate_catalog_page(conn, 200)
    generate_inventory(conn, 5000)
    generate_store_sales(conn, 5000)
    generate_store_returns(conn, 1000)
    generate_catalog_sales(conn, 3000)
    generate_catalog_returns(conn, 500)
    generate_web_sales(conn, 3000)
    generate_web_returns(conn, 500)

    conn.close()
    print(f"\n=== DONE in {time.time()-t0:.1f}s ===")


if __name__ == '__main__':
    run()
