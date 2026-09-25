import csv
import os
import sys
import traceback

sys.path.append(os.path.dirname(__file__))
from neo4j_loader import connect_postgres

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

TABLE_CSV_MAP = {
    "sources": "01_sources.csv",
    "actors": "00_actors.csv",
    "observations": "02_observations.csv",
    "posts": "03_posts.csv",
    "identifiers": "04_identifiers.csv",
    "infrastructure": "05_infrastructure.csv",
    "wallet_transactions": "07_wallet_transactions.csv",
    "activity_timeline": "08_activity_timeline.csv",
    "relationships": "06_relationships.csv",
}

LOAD_ORDER = [
    "sources", "actors", "observations", "posts", "identifiers",
    "infrastructure", "wallet_transactions", "activity_timeline", "relationships",
]

COLUMN_RENAMES = {
    "observations": {"timestamp": "event_timestamp"},
    "posts": {"timestamp": "event_timestamp"},
    "wallet_transactions": {"timestamp": "event_timestamp", "source": "source_id"},
    "activity_timeline": {"timestamp": "event_timestamp"},
    "relationships": {"timestamp": "event_timestamp"},
}


def load_table(connection, table_name, csv_path):
    if not os.path.exists(csv_path):
        print(f"  [SKIP] {table_name}: file not found at {csv_path}")
        return

    with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        header = [h.strip() for h in next(reader)]

    renames = COLUMN_RENAMES.get(table_name, {})
    header = [renames.get(h, h) for h in header]
    columns_sql = ", ".join(f'"{c}"' for c in header)
    copy_sql = f'COPY {table_name} ({columns_sql}) FROM STDIN WITH (FORMAT CSV, HEADER TRUE, NULL \'\')'

    copy_cursor = connection.cursor()
    try:
        if hasattr(copy_cursor, "copy_expert"):
            with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
                copy_cursor.copy_expert(copy_sql, f)
        elif hasattr(copy_cursor, "copy"):
            with copy_cursor.copy(copy_sql) as copy:
                with open(csv_path, "rb") as f:
                    while True:
                        chunk = f.read(8192)
                        if not chunk:
                            break
                        copy.write(chunk)
        else:
            raise RuntimeError("Cursor supports neither copy_expert nor copy.")
    finally:
        copy_cursor.close()

    connection.commit()

    # fresh cursor for verification, after commit
    check_cursor = connection.cursor()
    try:
        check_cursor.execute(f"SELECT COUNT(*) AS cnt FROM {table_name}")
        row = check_cursor.fetchone()
        count = row["cnt"] if isinstance(row, dict) else row[0]
    finally:
        check_cursor.close()

    print(f"  [OK] {table_name}: {count} rows now in table")


def main():
    connection = connect_postgres()
    try:
        for table_name in LOAD_ORDER:
            csv_path = os.path.join(DATA_DIR, TABLE_CSV_MAP[table_name])
            print(f"Loading {table_name} from {TABLE_CSV_MAP[table_name]} ...")
            try:
                load_table(connection, table_name, csv_path)
            except Exception:
                connection.rollback()
                print(f"  [ERROR] {table_name}:")
                traceback.print_exc()
        print("\nDone.")
    finally:
        connection.close()


if __name__ == "__main__":
    main()