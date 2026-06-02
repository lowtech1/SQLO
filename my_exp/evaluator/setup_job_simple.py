"""
Minimal JOB (IMDB / Join Order Benchmark) synthetic data setup.
6 tables, 1000-10000 rows — sufficient for thesis evaluation.
"""
import os, sys, random, psycopg2

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

JOB_TABLES = {
    'title': {
        'rows': 5000,
        'cols': [
            ('id', 'SERIAL PRIMARY KEY'),
            ('title', 'VARCHAR(500)'),
            ('imdb_index', 'VARCHAR(50)'),
            ('kind_id', 'INTEGER'),
            ('production_year', 'INTEGER'),
            ('imdb_id', 'VARCHAR(20)'),
            ('kind', 'VARCHAR(50)'),
            ('title_type', 'VARCHAR(50)'),
        ],
        'seed': 20,
    },
    'movie_companies': {
        'rows': 5000,
        'cols': [
            ('id', 'SERIAL PRIMARY KEY'),
            ('movie_id', 'INTEGER'),
            ('company_id', 'INTEGER'),
            ('company_type_id', 'INTEGER'),
            ('note', 'TEXT'),
        ],
        'seed': 21,
    },
    'cast_info': {
        'rows': 10000,
        'cols': [
            ('id', 'SERIAL PRIMARY KEY'),
            ('movie_id', 'INTEGER'),
            ('person_id', 'INTEGER'),
            ('person_role_id', 'INTEGER'),
            ('nr_order', 'INTEGER'),
            ('role_id', 'INTEGER'),
            ('role', 'VARCHAR(100)'),
        ],
        'seed': 22,
    },
    'movie_info_idx': {
        'rows': 3000,
        'cols': [
            ('id', 'SERIAL PRIMARY KEY'),
            ('movie_id', 'INTEGER'),
            ('info_type_id', 'INTEGER'),
            ('info', 'VARCHAR(1000)'),
            ('note', 'TEXT'),
        ],
        'seed': 23,
    },
    'movie_info': {
        'rows': 5000,
        'cols': [
            ('id', 'SERIAL PRIMARY KEY'),
            ('movie_id', 'INTEGER'),
            ('info_type_id', 'INTEGER'),
            ('info', 'VARCHAR(2000)'),
            ('note', 'TEXT'),
        ],
        'seed': 24,
    },
    'movie_keyword': {
        'rows': 5000,
        'cols': [
            ('id', 'SERIAL PRIMARY KEY'),
            ('movie_id', 'INTEGER'),
            ('keyword_id', 'INTEGER'),
            ('keyword', 'VARCHAR(100)'),
        ],
        'seed': 25,
    },
}


def create_table(conn, name, spec):
    cur = conn.cursor()
    cur.execute(f'DROP TABLE IF EXISTS {name} CASCADE')
    col_defs = ', '.join(f'{c[0]} {c[1]}' for c in spec['cols'])
    cur.execute(f'CREATE TABLE {name} ({col_defs})')
    print(f'  [OK] {name} schema')


def make_val(col, ct, i, rng, genres, kinds, roles, keywords, title_words):
    """Return a single Python value for the given column."""
    if ct.upper().startswith('SERIAL'):
        return None  # auto-generated
    if ct.upper().startswith('INT'):
        if col == 'production_year':
            return rng.randint(1970, 2025)
        if col == 'nr_order':
            return rng.randint(0, 50)
        return rng.randint(1, 5000)
    if col == 'imdb_id':
        return f'tt{i+1:07d}'
    if col == 'title':
        return ' '.join(rng.sample(title_words, k=rng.randint(2, 4)))
    if col == 'kind' or col == 'title_type':
        return rng.choice(kinds)
    if col == 'role':
        return rng.choice(roles)
    if col == 'keyword':
        return rng.choice(keywords)
    if col == 'info' and 'VARCHAR(2000)' in ct:
        return '|'.join(rng.sample(genres, k=2))
    if col == 'info':
        return rng.choice(genres)
    if col == 'note':
        return None if rng.random() > 0.1 else f'Note {i}'
    if col == 'imdb_index':
        return str(i % 20)
    return f'{col} {i}'


def generate_data(conn, name, spec):
    cur = conn.cursor()
    # Skip SERIAL columns
    non_serial = [(c[0], c[1]) for c in spec['cols'] if not c[1].upper().startswith('SERIAL')]
    col_names = ', '.join(c[0] for c in non_serial)
    placeholders = ', '.join(['%s'] * len(non_serial))
    n = spec['rows']
    rng = random.Random(spec['seed'])

    genres = ['Action', 'Drama', 'Comedy', 'Thriller', 'Romance', 'Sci-Fi', 'Horror',
              'Documentary', 'Animation', 'Adventure', 'Fantasy', 'Crime']
    kinds = ['movie', 'tv series', 'tv mini series', 'episode', 'video', 'tv movie']
    roles = ['actor', 'actress', 'director', 'producer', 'composer', 'editor', 'writer']
    keywords = ['murder', 'love', 'death', 'action', 'comedy', 'drama', 'thriller',
                'romance', 'sci-fi', 'horror', 'fantasy', 'adventure', 'crime']
    title_words = ['Star', 'Wars', 'Dark', 'Knight', 'Avengers', 'Batman', 'Superman',
                   'Spider', 'Infinity', 'War', 'Rise', 'Fall', 'Empire', 'Force',
                   'Matrix', 'Gladiator', 'Titanic', 'Avatar', 'Inception', 'Interstellar']

    batch_size = 500
    for batch_start in range(0, n, batch_size):
        batch_rows = []
        for i in range(batch_start, min(batch_start + batch_size, n)):
            row = [make_val(cn, ct, i, rng, genres, kinds, roles, keywords, title_words)
                   for cn, ct in non_serial]
            batch_rows.append(tuple(row))
        cur.executemany(f'INSERT INTO {name} ({col_names}) VALUES ({placeholders})', batch_rows)
        conn.commit()
        print(f'  [OK] {name}: {min(batch_start+batch_size, n)}/{n} rows')


def run():
    import time
    t0 = time.time()

    try:
        conn0 = psycopg2.connect(host='localhost', port=5432, dbname='postgres',
                                  user='postgres', password='nhanpro12')
        conn0.set_session(autocommit=True)
        cur0 = conn0.cursor()
        cur0.execute('DROP DATABASE IF EXISTS job')
        cur0.execute('CREATE DATABASE job')
        cur0.close()
        conn0.close()
        print('[OK] Database job created')
    except Exception as e:
        print(f'[WARN] Could not create job: {e}')

    conn = psycopg2.connect(host='localhost', port=5432, dbname='job',
                             user='postgres', password='nhanpro12')

    print('=== Creating JOB Schema ===')
    for name, spec in JOB_TABLES.items():
        create_table(conn, name, spec)

    print('\n=== Generating Synthetic Data ===')
    for name, spec in JOB_TABLES.items():
        generate_data(conn, name, spec)

    conn.close()

    # Verify
    print('\n=== Verification ===')
    conn2 = psycopg2.connect(host='localhost', port=5432, dbname='job',
                              user='postgres', password='nhanpro12')
    cur = conn2.cursor()
    cur.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename")
    tables = [r[0] for r in cur.fetchall()]
    print(f'Tables: {tables}')
    for t in tables:
        cur.execute(f'SELECT count(*) FROM {t}')
        print(f'  {t}: {cur.fetchone()[0]} rows')
    conn2.close()
    print(f'\n=== DONE in {time.time()-t0:.1f}s ===')


if __name__ == '__main__':
    run()
