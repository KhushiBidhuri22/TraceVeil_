from neo4j_loader import (
    connect_neo4j,
    connect_postgres,
    verify_neo4j,
)


def main():
    postgres = None
    neo4j = None

    try:
        print("Connecting to PostgreSQL...")
        postgres = connect_postgres()
        print("PostgreSQL connection successful.")

        print("Connecting to Neo4j...")
        neo4j = connect_neo4j()
        neo4j.verify_connectivity()
        verify_neo4j(neo4j)

        print("Neo4j connection successful.")
        print("Both connections are working.")

    finally:
        if postgres:
            postgres.close()

        if neo4j:
            neo4j.close()


if __name__ == "__main__":
    main()