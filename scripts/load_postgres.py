import json
import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.dialects.postgresql import JSONB


# ============================================================
# SIH DARK WEB DATASET → POSTGRESQL ETL
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data" / "raw"

# Load credentials from the project-root .env file.
load_dotenv(PROJECT_ROOT / ".env")


# ============================================================
# DATABASE CONFIGURATION
# ============================================================

_engine = None

def get_engine():
    global _engine
    if _engine is not None:
        return _engine
    raw_db_url = os.getenv("DATABASE_URL")
    if raw_db_url:
        db_url = raw_db_url.replace("postgresql://", "postgresql+psycopg://")
    else:
        host = os.getenv("POSTGRES_HOST", "localhost")
        port = os.getenv("POSTGRES_PORT", "5432")
        db = os.getenv("POSTGRES_DB", "sih_darkweb")
        user = os.getenv("POSTGRES_USER", "sih_user")
        pwd = os.getenv("POSTGRES_PASSWORD", "sih_password")
        db_url = f"postgresql+psycopg://{user}:{pwd}@{host}:{port}/{db}"
    _engine = create_engine(db_url, pool_pre_ping=True)
    return _engine

class LazyEngine:
    def __getattribute__(self, item):
        return getattr(get_engine(), item)

engine = get_engine()


# ============================================================
# DATASET TABLES
# ============================================================

TABLES = [
    ("01_sources.csv", "sources"),
    ("02_observations.csv", "observations"),
    ("03_posts.csv", "posts"),
    ("04_identifiers.csv", "identifiers"),
    ("05_infrastructure.csv", "infrastructure"),
    ("07_wallet_transactions.csv", "wallet_transactions"),
    ("08_activity_timeline.csv", "activity_timeline"),
    ("06_relationships.csv", "relationships"),
]


# ============================================================
# COLUMN TYPES
# ============================================================

DATE_COLUMNS = [
    "created_at",
    "first_seen",
    "last_seen",
    "last_checked",
    "timestamp",
    "observed_at",
    "event_timestamp",
]


NUMERIC_COLUMNS = [
    "reliability_score",
    "confidence",
    "reply_count",
    "sentiment_score",
    "word_count",
    "avg_sentence_length",
    "punctuation_ratio",
    "technical_term_ratio",
    "amount",
]


BOOLEAN_COLUMNS = [
    "repeated_phrase_flag",
]


JSON_COLUMNS = [
    "metadata",
]


# ============================================================
# JSON HELPER
# ============================================================

def parse_json(value):
    """
    Convert a CSV JSON value into a Python dictionary/list.

    Examples:
        '{"hour": 12}' -> {'hour': 12}
        empty value    -> None
    """

    if value is None:
        return None

    if isinstance(value, float) and pd.isna(value):
        return None

    if pd.isna(value):
        return None

    if isinstance(value, (dict, list)):
        return value

    value = str(value).strip()

    if not value:
        return None

    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return None


# ============================================================
# CLEAN DATAFRAME
# ============================================================

def clean_dataframe(df):
    """
    Clean dates, numbers, booleans and JSON metadata.
    """

    # --------------------------------------------------------
    # DATE COLUMNS
    # --------------------------------------------------------

    for column in DATE_COLUMNS:

        if column in df.columns:

            df[column] = pd.to_datetime(
                df[column],
                utc=True,
                errors="coerce",
            )

            # Convert timezone-aware pandas datetime to
            # timezone-naive datetime for PostgreSQL
            # TIMESTAMP WITHOUT TIME ZONE columns.
            df[column] = df[column].dt.tz_localize(None)


    # --------------------------------------------------------
    # NUMERIC COLUMNS
    # --------------------------------------------------------

    for column in NUMERIC_COLUMNS:

        if column in df.columns:

            df[column] = pd.to_numeric(
                df[column],
                errors="coerce",
            )


    # --------------------------------------------------------
    # BOOLEAN COLUMNS
    # --------------------------------------------------------

    for column in BOOLEAN_COLUMNS:

        if column in df.columns:

            def convert_boolean(value):

                if value is None:
                    return None

                if isinstance(value, float) and pd.isna(value):
                    return None

                if pd.isna(value):
                    return None

                if isinstance(value, bool):
                    return value

                value = str(value).strip().lower()

                if value in {
                    "true",
                    "1",
                    "yes",
                    "y",
                }:
                    return True

                if value in {
                    "false",
                    "0",
                    "no",
                    "n",
                }:
                    return False

                return None

            df[column] = df[column].apply(
                convert_boolean
            )


    # --------------------------------------------------------
    # JSON COLUMNS
    # --------------------------------------------------------

    for column in JSON_COLUMNS:

        if column in df.columns:

            df[column] = df[column].apply(
                parse_json
            )


    return df


# ============================================================
# GET ACTUAL POSTGRESQL COLUMNS
# ============================================================

def get_table_columns(table_name):

    inspector = inspect(engine)

    columns = inspector.get_columns(
        table_name
    )

    return {
        column["name"]
        for column in columns
    }


# ============================================================
# LOAD ACTORS
# ============================================================

def collect_actor_ids():

    actor_ids = set()

    files_to_scan = [
        "02_observations.csv",
        "03_posts.csv",
        "04_identifiers.csv",
        "05_infrastructure.csv",
        "06_relationships.csv",
        "07_wallet_transactions.csv",
        "08_activity_timeline.csv",
    ]

    for filename in files_to_scan:

        csv_path = DATA_DIR / filename

        if not csv_path.exists():
            continue

        df = pd.read_csv(
            csv_path,
            low_memory=False,
        )

        for column in [
            "actor_id",
            "actor_from",
            "actor_to",
        ]:

            if column not in df.columns:
                continue

            values = (
                df[column]
                .dropna()
                .astype(str)
                .str.strip()
            )

            for value in values:

                if value:
                    actor_ids.add(value)


    return sorted(actor_ids)


def load_actors():

    print()
    print("[1/9] Loading actors...")

    actor_ids = collect_actor_ids()

    actors_df = pd.DataFrame(
        {
            "actor_id": actor_ids
        }
    )

    table_columns = get_table_columns(
        "actors"
    )

    insert_columns = [
        column
        for column in actors_df.columns
        if column in table_columns
    ]

    actors_df = actors_df[
        insert_columns
    ]

    actors_df.to_sql(
        "actors",
        engine,
        if_exists="append",
        index=False,
        chunksize=500,
    )

    print(
        f"Loaded {len(actors_df):,} actors"
    )


# ============================================================
# HANDLE LEGACY EVENT TIMESTAMP
# ============================================================

def handle_legacy_columns(
    df,
    table_name,
):

    table_columns = get_table_columns(
        table_name
    )

    # Some of the original tables contain an older
    # event_timestamp column.
    #
    # If the CSV provides timestamp, copy that value into
    # event_timestamp as well.

    if (
        "event_timestamp" in table_columns
        and "timestamp" in df.columns
    ):

        df["event_timestamp"] = df[
            "timestamp"
        ]

    return df


# ============================================================
# LOAD NORMAL TABLE
# ============================================================

def load_table(
    filename,
    table_name,
):

    print()
    print(
        f"Loading {filename} -> {table_name}"
    )

    csv_path = DATA_DIR / filename

    if not csv_path.exists():

        raise FileNotFoundError(
            f"CSV file not found: {csv_path}"
        )


    # --------------------------------------------------------
    # READ CSV
    # --------------------------------------------------------

    df = pd.read_csv(
        csv_path,
        low_memory=False,
    )

    print(
        f"CSV rows: {len(df):,}"
    )


    # --------------------------------------------------------
    # CLEAN
    # --------------------------------------------------------

    df = clean_dataframe(df)


    # --------------------------------------------------------
    # HANDLE OLD DATABASE COLUMNS
    # --------------------------------------------------------

    df = handle_legacy_columns(
        df,
        table_name,
    )


    # --------------------------------------------------------
    # ONLY USE REAL DATABASE COLUMNS
    # --------------------------------------------------------

    table_columns = get_table_columns(
        table_name
    )

    insert_columns = [
        column
        for column in df.columns
        if column in table_columns
    ]

    if not insert_columns:

        raise RuntimeError(
            f"No matching columns found for "
            f"PostgreSQL table '{table_name}'."
        )

    df = df[
        insert_columns
    ]


    # --------------------------------------------------------
    # SPECIAL JSONB HANDLING
    # --------------------------------------------------------

    sql_dtype = {}

    if "metadata" in df.columns:

        sql_dtype["metadata"] = JSONB()


    # --------------------------------------------------------
    # INSERT INTO POSTGRESQL
    # --------------------------------------------------------

    df.to_sql(
        table_name,
        engine,
        if_exists="append",
        index=False,
        chunksize=500,
        dtype=sql_dtype,
    )

    print(
        f"Loaded {len(df):,} rows into {table_name}"
    )


# ============================================================
# RESET DATABASE
# ============================================================

def init_schema():
    schema_path = PROJECT_ROOT / "backend" / "graph_loader" / "schema.sql"
    if schema_path.exists():
        print("Ensuring database schema exists...")
        with open(schema_path, "r", encoding="utf-8") as f:
            sql_script = f.read()
        with engine.begin() as connection:
            connection.execute(text(sql_script))


def reset_tables():
    init_schema()

    print()
    print(
        "Resetting existing table data..."
    )

    tables = [
        "relationships",
        "activity_timeline",
        "wallet_transactions",
        "infrastructure",
        "identifiers",
        "posts",
        "observations",
        "sources",
        "actors",
    ]

    with engine.begin() as connection:

        for table in tables:

            print(
                f"Clearing {table}..."
            )

            try:
                connection.execute(
                    text(
                        f'TRUNCATE TABLE "{table}" CASCADE'
                    )
                )
            except Exception as e:
                print(f"  (Skipping clear for {table}: table might not exist yet)")

    print(
        "Database reset complete."
    )


# ============================================================
# TEST DATABASE CONNECTION
# ============================================================

def test_connection():

    print()
    print(
        "Testing PostgreSQL connection..."
    )

    with engine.connect() as connection:

        result = connection.execute(
            text("SELECT version();")
        )

        version = result.scalar()

    print(
        "PostgreSQL connection: OK"
    )

    print(version)


# ============================================================
# VERIFY ROW COUNTS
# ============================================================

def verify_counts():

    print()
    print(
        "=" * 70
    )

    print(
        "DATABASE ROW COUNT VERIFICATION"
    )

    print(
        "=" * 70
    )

    tables = [
        "actors",
        "sources",
        "observations",
        "posts",
        "identifiers",
        "infrastructure",
        "wallet_transactions",
        "activity_timeline",
        "relationships",
    ]

    with engine.connect() as connection:

        for table in tables:

            result = connection.execute(
                text(
                    f'SELECT COUNT(*) '
                    f'FROM "{table}"'
                )
            )

            count = result.scalar()

            print(
                f"{table:25} {count:>10,}"
            )


# ============================================================
# MAIN
# ============================================================

def main():
    global _engine, engine
    _engine = None
    engine = get_engine()

    print(
        "=" * 70
    )

    print(
        "SIH DARK WEB DATASET -> POSTGRESQL ETL"
    )

    print(
        "=" * 70
    )

    print()

    print(
        f"Data directory: {DATA_DIR}"
    )

    db_info = os.getenv("DATABASE_URL") or "postgresql+psycopg://..."
    print(
        f"Database: {db_info}"
    )


    # --------------------------------------------------------
    # DATABASE CONNECTION
    # --------------------------------------------------------

    test_connection()


    # --------------------------------------------------------
    # RESET
    # --------------------------------------------------------

    reset_tables()


    # --------------------------------------------------------
    # ACTORS
    # --------------------------------------------------------

    load_actors()


    # --------------------------------------------------------
    # DATA TABLES
    # --------------------------------------------------------

    for index, (
        filename,
        table_name,
    ) in enumerate(
        TABLES,
        start=2,
    ):

        print()

        print(
            f"[{index}/9]"
        )

        load_table(
            filename,
            table_name,
        )


    # --------------------------------------------------------
    # FINAL VERIFICATION
    # --------------------------------------------------------

    verify_counts()


    print()

    print(
        "=" * 70
    )

    print(
        "ETL COMPLETE"
    )

    print(
        "=" * 70
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    main()