"""
Setup JOB (IMDB / Join Order Benchmark) synthetic data in PostgreSQL.
Creates schemas + generates realistic synthetic data for 6 IMDB tables.
Scale: 1000-5000 rows per table (small scale for thesis evaluation).
"""
import os
import sys
import random
import psycopg2

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))


def get_conn(dbname='job'):
    return psycopg2.connect(
        host='localhost', port=5432, dbname=dbname,
        user='postgres', password='nhanpro12'
    )


def setup_job_schema(conn):
    """Create JOB (IMDB) schema in PostgreSQL."""
    cur = conn.cursor()

    tables = ['title', 'movie_companies', 'cast_info', 'movie_info_idx', 'movie_info', 'movie_keyword']
    for t in tables:
        cur.execute(f"DROP TABLE IF EXISTS {t} CASCADE")

    # title: 2528312 rows -> 5000
    cur.execute("""
    CREATE TABLE title (
        id SERIAL PRIMARY KEY,
        title VARCHAR(500),
        imdb_index VARCHAR(50),
        kind_id INTEGER,
        production_year INTEGER,
        imdb_id VARCHAR(20),
        phonetic_code VARCHAR(20),
        episode_of_id INTEGER,
        season_nr INTEGER,
        episode_nr INTEGER,
        series_rank INTEGER,
        md5sum VARCHAR(50),
        kind VARCHAR(50),
        title_type VARCHAR(50)
    )
    """)

    # movie_companies: 2609129 rows -> 5000
    cur.execute("""
    CREATE TABLE movie_companies (
        id SERIAL PRIMARY KEY,
        movie_id INTEGER REFERENCES title(id),
        company_id INTEGER,
        company_type_id INTEGER,
        note TEXT
    )
    """)

    # cast_info: 36244344 rows -> 10000
    cur.execute("""
    CREATE TABLE cast_info (
        id SERIAL PRIMARY KEY,
        movie_id INTEGER REFERENCES title(id),
        person_id INTEGER,
        person_role_id INTEGER,
        nr_order INTEGER,
        role_id INTEGER,
        role VARCHAR(100)
    )
    """)

    # movie_info_idx: 1380035 rows -> 3000
    cur.execute("""
    CREATE TABLE movie_info_idx (
        id SERIAL PRIMARY KEY,
        movie_id INTEGER REFERENCES title(id),
        info_type_id INTEGER,
        info VARCHAR(1000),
        note TEXT
    )
    """)

    # movie_info: 14835720 rows -> 5000
    cur.execute("""
    CREATE TABLE movie_info (
        id SERIAL PRIMARY KEY,
        movie_id INTEGER REFERENCES title(id),
        info_type_id INTEGER,
        info VARCHAR(2000),
        note TEXT
    )
    """)

    # movie_keyword: 4523930 rows -> 5000
    cur.execute("""
    CREATE TABLE movie_keyword (
        id SERIAL PRIMARY KEY,
        movie_id INTEGER REFERENCES title(id),
        keyword_id INTEGER,
        keyword VARCHAR(100)
    )
    """)

    conn.commit()
    print("[OK] JOB schema created")


def generate_title(conn, n=5000, seed=100):
    """Generate title table."""
    random.seed(seed)
    cur = conn.cursor()
    kinds = ['movie', 'tv series', 'tv mini series', 'episode', 'video', 'tv movie', 'video game']
    title_words = [
        'Star', 'Wars', 'Dark', 'Knight', 'Batman', 'Superman', 'Spider', 'Man',
        'Avengers', 'Iron', 'Hulk', 'Thor', 'Captain', 'America', 'Guardians',
        'Infinity', 'War', 'Endgame', 'Rogue', 'One', 'Legacy', 'Rise', 'Fall',
        'Empire', 'Force', 'Last', 'Force', 'Hope', 'New', 'Order', 'Episode',
        'Matrix', 'Gladiator', 'Titanic', 'Avatar', 'Inception', 'Interstellar',
        'Prestige', 'Memento', 'Django', 'Pulp', 'Fiction', 'Shawshank', 'Redemption',
        'Godfather', 'Casino', 'Heat', 'Dark', 'Knight', 'Joker', 'Fight', 'Club',
        'Social', 'Network', 'Wolf', 'Wall', 'Street', 'Departed', 'Scarface', 'Heat',
        'Notebook', 'Titanic', 'Avatar', 'Terminator', 'Predator', 'Alien', 'Robocop'
    ]
    for i in range(n):
        year = random.randint(1970, 2025)
        kind = random.choice(kinds)
        kind_id = kinds.index(kind) + 1
        title_words_shuffled = title_words[:]
        random.shuffle(title_words_shuffled)
        title_name = ' '.join(title_words_shuffled[:random.randint(1, 5)])
        cur.execute("""
            INSERT INTO title (title, imdb_index, kind_id, production_year, imdb_id,
                phonetic_code, episode_of_id, season_nr, episode_nr, series_rank, md5sum, kind, title_type)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            title_name, str(i % 20 + 1), kind_id, year,
            f'tt{i+1:07d}',
            ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=12)),
            None, None, None, None,
            ''.join(random.choices('0123456789abcdef', k=32)),
            kind, kind
        ))
    conn.commit()
    print(f"[OK] title: {n} rows")


def generate_movie_companies(conn, n=5000, seed=101):
    """Generate movie_companies table."""
    random.seed(seed)
    cur = conn.cursor()
    for i in range(n):
        cur.execute("""
            INSERT INTO movie_companies (movie_id, company_id, company_type_id, note)
            VALUES (%s,%s,%s,%s)
        """, (
            random.randint(1, 5000),
            random.randint(1, 1000),
            random.randint(1, 5),
            None if random.random() > 0.2 else f'Note {i}'
        ))
    conn.commit()
    print(f"[OK] movie_companies: {n} rows")


def generate_cast_info(conn, n=10000, seed=102):
    """Generate cast_info table."""
    random.seed(seed)
    cur = conn.cursor()
    roles = ['actor', 'actress', 'director', 'producer', 'composer', 'cinematographer',
             'editor', 'writer', 'self', 'archive_footage', 'archive_sound']
    for i in range(n):
        cur.execute("""
            INSERT INTO cast_info (movie_id, person_id, person_role_id, nr_order, role_id, role)
            VALUES (%s,%s,%s,%s,%s,%s)
        """, (
            random.randint(1, 5000),
            random.randint(1, 5000),
            random.randint(1, 1000),
            random.randint(0, 100),
            random.randint(1, len(roles)),
            random.choice(roles)
        ))
    conn.commit()
    print(f"[OK] cast_info: {n} rows")


def generate_movie_info_idx(conn, n=3000, seed=103):
    """Generate movie_info_idx table."""
    random.seed(seed)
    cur = conn.cursor()
    info_type_ids = [100, 101, 102, 103, 104, 105, 106, 107, 108, 109]
    for i in range(n):
        itype = random.choice(info_type_ids)
        if itype == 100:
            info = f'{random.randint(5.0, 9.9):.1f}'
        elif itype == 101:
            info = f'{random.randint(10000, 500000):,} votes'
        elif itype == 102:
            info = f'${random.randint(1, 300):,}M'
        elif itype == 103:
            info = random.choice(['English', 'French', 'German', 'Spanish', 'Japanese', 'Korean', 'Mandarin', 'Hindi'])
        elif itype == 104:
            info = random.choice(['PG-13', 'R', 'PG', 'G', 'NC-17'])
        elif itype == 105:
            info = random.choice(['Released', 'Greenlight', 'Announced', 'Pre-production', 'Post-production', 'Rumored'])
        else:
            info = f'Info type {itype}'
        cur.execute("""
            INSERT INTO movie_info_idx (movie_id, info_type_id, info, note)
            VALUES (%s,%s,%s,%s)
        """, (random.randint(1, 5000), itype, info,
              None if random.random() > 0.1 else f'Note {i}'))
    conn.commit()
    print(f"[OK] movie_info_idx: {n} rows")


def generate_movie_info(conn, n=5000, seed=104):
    """Generate movie_info table."""
    random.seed(seed)
    cur = conn.cursor()
    info_type_ids = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]
    genres = ['Action', 'Drama', 'Comedy', 'Thriller', 'Romance', 'Sci-Fi', 'Horror',
              'Documentary', 'Animation', 'Adventure', 'Fantasy', 'Crime', 'Mystery',
              'Family', 'History', 'Music', 'War', 'Western', 'Biography', 'Sport']
    for i in range(n):
        itype = random.choice(info_type_ids)
        if itype == 3:
            info = random.choice(genres) + '|' + random.choice(genres)
        elif itype == 4:
            info = random.choice(genres)
        elif itype == 8:
            info = random.choice(['English', 'French', 'German', 'Spanish', 'Japanese', 'Korean', 'Mandarin', 'Hindi', 'Portuguese', 'Italian'])
        elif itype == 10:
            info = random.choice(['Filming', 'Post-production', 'Pre-production', 'Released', 'Announced', 'Rumored'])
        elif itype == 14:
            info = random.choice(['Biography', 'Adventure', 'Comedy', 'Drama', 'Family', 'Fantasy', 'Horror', 'Mystery', 'Romance', 'Thriller', 'Sci-Fi'])
        else:
            info = f'Info type {itype} description'
        cur.execute("""
            INSERT INTO movie_info (movie_id, info_type_id, info, note)
            VALUES (%s,%s,%s,%s)
        """, (random.randint(1, 5000), itype, info,
              None if random.random() > 0.1 else f'Note {i}'))
    conn.commit()
    print(f"[OK] movie_info: {n} rows")


def generate_movie_keyword(conn, n=5000, seed=105):
    """Generate movie_keyword table."""
    random.seed(seed)
    cur = conn.cursor()
    keywords = [
        'murder', 'love', 'death', 'suspense', 'action', 'comedy', 'drama', 'thriller',
        'romance', 'science-fiction', 'horror', 'fantasy', 'adventure', 'crime', 'mystery',
        'detective', 'police', 'war', 'spy', 'zombie', 'vampire', 'superhero', 'based-on-novel',
        '3d', 'cult-film', 'film-noir', 'ensemble-cast', 'voice-over', 'narration',
        'psychopath', 'serial-killer', 'artificial-intelligence', 'space', 'time-travel',
        'dystopia', 'alien-invasion', 'apocalypse', 'conspiracy', 'betrayal', 'revenge',
        'friendship', 'brother-brother-relationship', 'father-son-relationship', 'mother-daughter-relationship',
        'male-protagonist', 'female-protagonist', 'ensemble', 'nonlinear-timeline'
    ]
    for i in range(n):
        cur.execute("""
            INSERT INTO movie_keyword (movie_id, keyword_id, keyword)
            VALUES (%s,%s,%s)
        """, (random.randint(1, 5000), i + 1, random.choice(keywords)))
    conn.commit()
    print(f"[OK] movie_keyword: {n} rows")


def run():
    """Setup JOB database with synthetic data."""
    import time
    t0 = time.time()

    # Create database
    try:
        conn0 = psycopg2.connect(host='localhost', port=5432, dbname='postgres',
                                  user='postgres', password='nhanpro12')
        conn0.set_session(autocommit=True)
        cur0 = conn0.cursor()
        cur0.execute("DROP DATABASE IF EXISTS job")
        cur0.execute("CREATE DATABASE job")
        cur0.close()
        conn0.close()
        print("[OK] Database 'job' created")
    except Exception as e:
        print(f"[WARN] Could not create database: {e}")
        return

    conn = get_conn('job')

    print("=== Creating JOB Schema ===")
    setup_job_schema(conn)

    print("\n=== Generating Synthetic Data ===")
    generate_title(conn, 5000)
    generate_movie_companies(conn, 5000)
    generate_cast_info(conn, 10000)
    generate_movie_info_idx(conn, 3000)
    generate_movie_info(conn, 5000)
    generate_movie_keyword(conn, 5000)

    conn.close()
    print(f"\n=== DONE in {time.time()-t0:.1f}s ===")


if __name__ == '__main__':
    run()
