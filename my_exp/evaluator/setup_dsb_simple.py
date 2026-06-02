"""
Minimal DSB (Star Schema Benchmark) synthetic data setup.
Only creates essential tables needed for DSB query evaluation.
7 tables, 1000 rows each — sufficient for thesis evaluation.
"""
import os, sys, random
import psycopg2
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

DSB_TABLES = {
    'date_dim': {
        'rows': 730,
        'pk': 'd_date_sk',
        'cols': [
            ('d_date_sk', 'SERIAL PRIMARY KEY'),
            ('d_date_id', 'VARCHAR(20)'),
            ('d_date', 'DATE'),
            ('d_year', 'INTEGER'),
            ('d_month', 'INTEGER'),
            ('d_month_name', 'VARCHAR(20)'),
            ('d_day_name', 'VARCHAR(20)'),
            ('d_dom', 'INTEGER'),
            ('d_dow', 'INTEGER'),
            ('d_doy', 'INTEGER'),
            ('d_quarter', 'INTEGER'),
            ('d_week', 'INTEGER'),
            ('d_holiday', 'VARCHAR(10)'),
            ('d_weekend', 'VARCHAR(10)'),
        ],
        'seed': 10,
    },
    'item': {
        'rows': 1000,
        'pk': 'i_item_sk',
        'cols': [
            ('i_item_sk', 'SERIAL PRIMARY KEY'),
            ('i_item_id', 'VARCHAR(20)'),
            ('i_rec_start_date', 'DATE'),
            ('i_rec_end_date', 'DATE'),
            ('i_item_desc', 'VARCHAR(200)'),
            ('i_current_price', 'NUMERIC(10,2)'),
            ('i_wholesale_cost', 'NUMERIC(10,2)'),
            ('i_brand_id', 'INTEGER'),
            ('i_class_id', 'INTEGER'),
            ('i_category_id', 'INTEGER'),
            ('i_category', 'VARCHAR(50)'),
            ('i_class', 'VARCHAR(50)'),
            ('i_brand', 'VARCHAR(50)'),
            ('i_color', 'VARCHAR(50)'),
        ],
        'seed': 11,
    },
    'customer': {
        'rows': 1000,
        'pk': 'c_customer_sk',
        'cols': [
            ('c_customer_sk', 'SERIAL PRIMARY KEY'),
            ('c_customer_id', 'VARCHAR(20)'),
            ('c_first_name', 'VARCHAR(50)'),
            ('c_last_name', 'VARCHAR(50)'),
            ('c_login', 'VARCHAR(20)'),
            ('c_email_address', 'VARCHAR(100)'),
            ('c_last_review_date', 'INTEGER'),
            ('c_preferred_cust_flag', 'VARCHAR(5)'),
            ('c_birth_country', 'VARCHAR(60)'),
            ('c_customer_sk_ref', 'INTEGER'),
        ],
        'seed': 12,
    },
    'customer_address': {
        'rows': 500,
        'pk': 'ca_address_sk',
        'cols': [
            ('ca_address_sk', 'SERIAL PRIMARY KEY'),
            ('ca_address_id', 'VARCHAR(20)'),
            ('ca_street_number', 'VARCHAR(10)'),
            ('ca_street_name', 'VARCHAR(100)'),
            ('ca_street_type', 'VARCHAR(10)'),
            ('ca_city', 'VARCHAR(60)'),
            ('ca_county', 'VARCHAR(60)'),
            ('ca_state', 'VARCHAR(5)'),
            ('ca_zip', 'VARCHAR(10)'),
            ('ca_country', 'VARCHAR(20)'),
            ('ca_gmt_offset', 'NUMERIC(5,2)'),
        ],
        'seed': 13,
    },
    'store': {
        'rows': 20,
        'pk': 's_store_sk',
        'cols': [
            ('s_store_sk', 'SERIAL PRIMARY KEY'),
            ('s_store_id', 'VARCHAR(20)'),
            ('s_store_name', 'VARCHAR(100)'),
            ('s_manager', 'VARCHAR(100)'),
            ('s_street_number', 'VARCHAR(10)'),
            ('s_street_name', 'VARCHAR(100)'),
            ('s_street_type', 'VARCHAR(10)'),
            ('s_city', 'VARCHAR(60)'),
            ('s_county', 'VARCHAR(60)'),
            ('s_state', 'VARCHAR(5)'),
            ('s_zip', 'VARCHAR(10)'),
            ('s_country', 'VARCHAR(30)'),
            ('s_market_id', 'INTEGER'),
        ],
        'seed': 14,
    },
    'store_sales': {
        'rows': 5000,
        'pk': None,
        'cols': [
            ('ss_sold_date_sk', 'INTEGER'),
            ('ss_sold_time_sk', 'INTEGER'),
            ('ss_item_sk', 'INTEGER'),
            ('ss_customer_sk', 'INTEGER'),
            ('ss_cdemo_sk', 'INTEGER'),
            ('ss_hdemo_sk', 'INTEGER'),
            ('ss_addr_sk', 'INTEGER'),
            ('ss_store_sk', 'INTEGER'),
            ('ss_promo_sk', 'INTEGER'),
            ('ss_ticket_number', 'INTEGER'),
            ('ss_quantity', 'INTEGER'),
            ('ss_wholesale_cost', 'NUMERIC(10,2)'),
            ('ss_list_price', 'NUMERIC(10,2)'),
            ('ss_sales_price', 'NUMERIC(10,2)'),
            ('ss_ext_discount_amt', 'NUMERIC(10,2)'),
            ('ss_ext_sales_price', 'NUMERIC(10,2)'),
            ('ss_ext_tax', 'NUMERIC(10,2)'),
            ('ss_net_paid', 'NUMERIC(10,2)'),
            ('ss_net_profit', 'NUMERIC(10,2)'),
        ],
        'seed': 15,
    },
    'promotion': {
        'rows': 100,
        'pk': 'p_promo_sk',
        'cols': [
            ('p_promo_sk', 'SERIAL PRIMARY KEY'),
            ('p_promo_id', 'VARCHAR(20)'),
            ('p_start_date_sk', 'INTEGER'),
            ('p_end_date_sk', 'INTEGER'),
            ('p_item_sk', 'INTEGER'),
            ('p_cost', 'NUMERIC(10,2)'),
            ('p_response_target', 'INTEGER'),
            ('p_promo_name', 'VARCHAR(200)'),
            ('p_channel_email', 'VARCHAR(5)'),
        ],
        'seed': 16,
    },
}


def create_table(conn, name, spec):
    cur = conn.cursor()
    col_defs = ', '.join(f'{c[0]} {c[1]}' for c in spec['cols'])
    cur.execute(f'DROP TABLE IF EXISTS {name} CASCADE')
    cur.execute(f'CREATE TABLE {name} ({col_defs})')
    print(f'  [OK] {name} schema')


def varchar_size(ct):
    m = __import__('re').search(r'VARCHAR\((\d+)\)', ct, 0)
    return int(m.group(1)) if m else 200

def generate_data(conn, name, spec):
    cur = conn.cursor()
    non_serial = [(c[0], c[1]) for c in spec['cols'] if 'SERIAL' not in c[1].upper()]
    col_names = ', '.join(c[0] for c in non_serial)
    placeholders = ', '.join(['%s'] * len(non_serial))
    n = spec['rows']
    rng = random.Random(spec['seed'])
    months = ['January', 'February', 'March', 'April', 'May', 'June',
               'July', 'August', 'September', 'October', 'November', 'December']
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

    def get_val(col, ct, i):
        prefix = col[:2]
        # INTEGER types FIRST (before VARCHAR catches them)
        if 'INT' in ct.upper() or 'NUMERIC' in ct.upper():
            if 'PRICE' in col.upper() or 'COST' in col.upper() or 'AMT' in col.upper() or 'PROFIT' in col.upper():
                return round(rng.uniform(5.0, 500.0), 2)
            return rng.randint(1, 1000)
        # VARCHAR types
        cn = col.upper()
        if 'DATE' in cn:
            d = datetime(2001, 1, 1) + __import__('datetime').timedelta(days=i)
            return d.date()
        if 'NAME' in cn:
            return rng.choice(['Main', 'Oak', 'Market', 'First', 'Broadway']) + f' {i}'
        if 'DESC' in cn:
            return f'Description {i}'
        if 'FLAG' in cn:
            return rng.choice(['Y', 'N'])
        if cn.endswith('EMAIL') or cn.endswith('CHANNEL_EMAIL'):
            return rng.choice(['Y', 'N'])
        if 'EMAIL' in cn:
            return f'user{i}@example.com'
        if 'CITY' in cn:
            return rng.choice(['New York', 'Los Angeles', 'Chicago', 'Houston', 'Phoenix'])
        if 'STATE' in cn:
            return rng.choice(['NY', 'CA', 'TX', 'IL', 'AZ'])
        if 'ZIP' in cn:
            return str(rng.randint(10000, 99999))
        if 'COUNTRY' in cn:
            return 'United States'
        if 'NUMBER' in cn:
            return str(rng.randint(1, 9999))
        if 'TYPE' in cn:
            return rng.choice(['St', 'Ave', 'Blvd', 'Dr'])
        if 'LOGIN' in cn:
            return f'user{i}'
        if 'FIRST_NAME' in cn:
            return rng.choice(['James', 'Mary', 'John', 'Patricia', 'Robert'])
        if 'LAST_NAME' in cn:
            return rng.choice(['Smith', 'Johnson', 'Williams', 'Brown', 'Jones'])
        if 'BRAND' in cn:
            return rng.choice([f'Brand#{rng.randint(1,5)}', 'Generic', 'Premium'])
        if 'CLASS' in cn and 'CLASS_ID' not in cn:
            return rng.choice(['pop', 'rock', 'jazz', 'classical'])
        if 'CATEGORY' in cn and 'CATEGORY_ID' not in cn:
            return rng.choice(['Books', 'Electronics', 'Home', 'Sports'])
        if 'COLOR' in cn:
            return rng.choice(['white', 'black', 'red', 'blue', 'green'])
        if 'COUNTY' in cn:
            return rng.choice(['LA County', 'Cook County', 'Harris County'])
        if 'MONTH_NAME' in cn:
            return rng.choice(months)
        if 'DAY_NAME' in cn:
            return rng.choice(days)
        if 'HOLIDAY' in cn or 'WEEKEND' in cn:
            return rng.choice(['Y', 'N'])
        if 'ID' in cn:
            return f'{prefix}{i:05d}'[:varchar_size(ct)]
        val = f'{col} {i}'
        return val if 'VARCHAR' not in ct else val[:varchar_size(ct)]

    batch_size = 500
    for batch_start in range(0, n, batch_size):
        batch_rows = []
        for i in range(batch_start, min(batch_start + batch_size, n)):
            row = [get_val(cn, ct, i) for cn, ct in non_serial]
            batch_rows.append(tuple(row))
        cur.executemany(f'INSERT INTO {name} ({col_names}) VALUES ({placeholders})', batch_rows)
        conn.commit()
        print(f'  [OK] {name}: inserted {min(batch_start+batch_size, n)}/{n} rows')


def run():
    import time
    t0 = time.time()

    # Create database
    try:
        conn0 = psycopg2.connect(host='localhost', port=5432, dbname='postgres',
                                  user='postgres', password='nhanpro12')
        conn0.set_session(autocommit=True)
        cur0 = conn0.cursor()
        cur0.execute('DROP DATABASE IF EXISTS dsb')
        cur0.execute('CREATE DATABASE dsb')
        cur0.close()
        conn0.close()
        print('[OK] Database dsb created')
    except Exception as e:
        print(f'[WARN] Could not create dsb: {e}')

    conn = psycopg2.connect(host='localhost', port=5432, dbname='dsb',
                             user='postgres', password='nhanpro12')

    print('=== Creating DSB Schema ===')
    for name, spec in DSB_TABLES.items():
        create_table(conn, name, spec)

    print('\n=== Generating Synthetic Data ===')
    for name, spec in DSB_TABLES.items():
        generate_data(conn, name, spec)

    conn.close()

    # Verify
    print('\n=== Verification ===')
    conn2 = psycopg2.connect(host='localhost', port=5432, dbname='dsb',
                              user='postgres', password='nhanpro12')
    cur = conn2.cursor()
    cur.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename")
    tables = [r[0] for r in cur.fetchall()]
    print(f'Tables: {tables}')
    for t in tables:
        cur.execute(f'SELECT count(*) FROM {t}')
        cnt = cur.fetchone()[0]
        print(f'  {t}: {cnt} rows')
    conn2.close()
    print(f'\n=== DONE in {time.time()-t0:.1f}s ===')


if __name__ == '__main__':
    run()
