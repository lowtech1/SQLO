"""
my_exp.core.schema_loader
=========================
Dynamic schema loading from JSON files or PostgreSQL connection.
Schema-agnostic: works with any database schema without hardcoding.
"""

import json
import os
import psycopg2
from typing import Optional
from dataclasses import dataclass, field


@dataclass
class ColumnInfo:
    name: str
    data_type: str
    nullable: bool = True
    is_primary_key: bool = False
    is_foreign_key: bool = False
    referenced_table: Optional[str] = None
    referenced_column: Optional[str] = None


@dataclass
class TableInfo:
    name: str
    alias: Optional[str] = None
    rows: int = 0
    columns: list = field(default_factory=list)
    has_indexes: bool = False


@dataclass
class DatabaseSchema:
    name: str
    tables: dict = field(default_factory=dict)
    """dict: table_name -> TableInfo"""
    relationships: list = field(default_factory=list)
    """list of (table1, col1, table2, col2) foreign key relationships"""
    dialect: str = "postgres"

    def get_table(self, name: str) -> Optional[TableInfo]:
        return self.tables.get(name)

    def get_table_size(self, name: str) -> int:
        t = self.get_table(name)
        return t.rows if t else 0

    def get_columns(self, table_name: str) -> list:
        t = self.get_table(table_name)
        return t.columns if t else []

    def estimate_join_selectivity(self, table1: str, table2: str) -> float:
        """
        Estimate selectivity of a JOIN between two tables.
        Returns value between 0 and 1.
        Lower = more selective (fewer result rows).
        """
        t1_rows = self.get_table_size(table1)
        t2_rows = self.get_table_size(table2)
        if t1_rows == 0 or t2_rows == 0:
            return 0.1
        # Simple heuristic: smaller table / larger table
        smaller = min(t1_rows, t2_rows)
        larger = max(t1_rows, t2_rows)
        return smaller / larger if larger > 0 else 0.1


def load_schema_from_json(json_path: str, dialect: str = "postgres") -> DatabaseSchema:
    """
    Load database schema from a JSON file.

    JSON format:
    {
      "db_name": "...",
      "tables": [
        {
          "table": "customer",
          "rows": 150000,
          "columns": [
            {"name": "c_custkey", "type": "integer", "nullable": false, "pk": true},
            {"name": "c_name", "type": "varchar"}
          ]
        }
      ]
    }
    """
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"Schema file not found: {json_path}")

    with open(json_path, 'r', encoding='utf-8') as f:
        raw = json.load(f)

    db_name = raw.get("db_name", os.path.splitext(os.path.basename(json_path))[0])
    schema = DatabaseSchema(name=db_name, dialect=dialect)

    for tbl_data in raw.get("tables", []):
        columns = []
        for col in tbl_data.get("columns", []):
            columns.append(ColumnInfo(
                name=col["name"],
                data_type=col.get("type", "unknown"),
                nullable=col.get("nullable", True),
                is_primary_key=col.get("pk", False),
            ))

        table = TableInfo(
            name=tbl_data["table"],
            rows=tbl_data.get("rows", 0),
            columns=columns,
        )
        schema.tables[table.name] = table

    # Build relationships from primary/foreign key info
    for table_name, table in schema.tables.items():
        for col in table.columns:
            if col.is_primary_key:
                pass
            if col.is_foreign_key and col.referenced_table:
                schema.relationships.append(
                    (table_name, col.name, col.referenced_table, col.referenced_column)
                )

    return schema


def load_schema_from_postgres(
    dbname: str,
    host: str = "localhost",
    port: int = 5432,
    user: str = "postgres",
    password: str = "",
    sample_limit: int = 1000
) -> DatabaseSchema:
    """
    Dynamically load database schema from a live PostgreSQL connection.
    Infers table sizes, column types, and relationships.
    """
    schema = DatabaseSchema(name=dbname, dialect="postgres")

    try:
        conn = psycopg2.connect(
            host=host, port=port, dbname=dbname, user=user, password=password
        )
        conn.autocommit = True
        cur = conn.cursor()

        # Get tables
        cur.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_type = 'BASE TABLE'
            ORDER BY table_name;
        """)
        table_names = [row[0] for row in cur.fetchall()]

        for tbl_name in table_names:
            # Get row count estimate
            try:
                cur.execute(f"SELECT reltuples::bigint FROM pg_class WHERE relname = %s", (tbl_name,))
                row_est = cur.fetchone()[0]
            except Exception:
                row_est = 0

            # Get columns
            cur.execute("""
                SELECT
                    c.column_name,
                    c.data_type,
                    c.is_nullable,
                    c.column_default,
                    CASE WHEN pk.column_name IS NOT NULL THEN TRUE ELSE FALSE END AS is_pk,
                    COALESCE(fk.foreign_table_name, '') AS fk_table,
                    COALESCE(fk.foreign_column_name, '') AS fk_col
                FROM information_schema.columns c
                LEFT JOIN (
                    SELECT kcu.column_name
                    FROM information_schema.table_constraints tc
                    JOIN information_schema.key_column_usage kcu
                        ON tc.constraint_name = kcu.constraint_name
                    WHERE tc.table_name = %s
                    AND tc.constraint_type = 'PRIMARY KEY'
                ) pk ON pk.column_name = c.column_name
                LEFT JOIN (
                    SELECT
                        kcu.column_name,
                        ccu.table_name AS foreign_table_name,
                        ccu.column_name AS foreign_column_name
                    FROM information_schema.table_constraints tc
                    JOIN information_schema.key_column_usage kcu
                        ON tc.constraint_name = kcu.constraint_name
                    JOIN information_schema.constraint_column_usage ccu
                        ON tc.constraint_name = ccu.constraint_name
                    WHERE tc.table_name = %s
                    AND tc.constraint_type = 'FOREIGN KEY'
                ) fk ON fk.column_name = c.column_name
                WHERE c.table_name = %s
                AND c.table_schema = 'public'
                ORDER BY c.ordinal_position;
            """, (tbl_name, tbl_name, tbl_name))

            columns = []
            for row in cur.fetchall():
                col_name, data_type, nullable, default, is_pk, fk_table, fk_col = row
                col = ColumnInfo(
                    name=col_name,
                    data_type=data_type,
                    nullable=(nullable == 'YES'),
                    is_primary_key=is_pk,
                    is_foreign_key=(fk_table != ''),
                    referenced_table=fk_table if fk_table else None,
                    referenced_column=fk_col if fk_col else None,
                )
                columns.append(col)

                if col.is_foreign_key:
                    schema.relationships.append(
                        (tbl_name, col_name, col.referenced_table, col.referenced_column)
                    )

            table = TableInfo(name=tbl_name, rows=int(row_est), columns=columns)
            schema.tables[tbl_name] = table

        cur.close()
        conn.close()
        return schema

    except psycopg2.Error as e:
        raise RuntimeError(f"PostgreSQL connection error: {e}")


def load_schema_auto(source: str, dialect: str = "postgres") -> DatabaseSchema:
    """
    Auto-detect schema source and load accordingly.

    Args:
        source: Either a JSON file path or a database name (for PostgreSQL)
        dialect: SQL dialect for JSON schemas
    """
    if os.path.exists(source):
        return load_schema_from_json(source, dialect)
    else:
        return load_schema_from_postgres(
            dbname=source,
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=int(os.getenv("POSTGRES_PORT", "5432")),
            user=os.getenv("POSTGRES_USER", "postgres"),
            password=os.getenv("POSTGRES_PASSWORD", ""),
        )


def get_available_schemas() -> dict:
    """
    List all available schemas from data/data_llmr2/schemas/
    """
    schemas_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "data", "data_llmr2", "schemas"
    )
    available = {}
    if os.path.exists(schemas_dir):
        for f in os.listdir(schemas_dir):
            if f.endswith('.json'):
                db_id = os.path.splitext(f)[0]
                path = os.path.join(schemas_dir, f)
                with open(path, 'r') as fp:
                    data = json.load(fp)
                    db_name = data.get("db_name", db_id)
                    table_count = len(data.get("tables", []))
                    available[db_id] = {
                        "name": db_name,
                        "path": path,
                        "tables": table_count,
                    }
    return available
