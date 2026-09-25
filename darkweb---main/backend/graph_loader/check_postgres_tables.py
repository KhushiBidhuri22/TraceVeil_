from neo4j_loader import connect_postgres


EXPECTED_TABLES = [
    "actors",
    "sources",
    "posts",
    "observations",
    "identifiers",
    "infrastructure",
    "wallet_transactions",
    "activity_timeline",
    "relationships",
]


def main():
    connection = None

    try:
        connection = connect_postgres()

        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name
                """
            )

            existing_tables = {
                row["table_name"]
                for row in cursor.fetchall()
            }

        print("PostgreSQL tables:")
        for table in sorted(existing_tables):
            print(f"  [FOUND] {table}")

        print("\nLoader requirements:")
        missing_tables = []

        for table in EXPECTED_TABLES:
            if table in existing_tables:
                print(f"  [FOUND] {table}")
            else:
                print(f"  [MISSING] {table}")
                missing_tables.append(table)

        if missing_tables:
            print("\nThe database is missing required tables.")
        else:
            print("\nAll loader tables are present.")

    finally:
        if connection:
            connection.close()


if __name__ == "__main__":
    main()