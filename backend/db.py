import psycopg

from neo4j import GraphDatabase

from .config import (
    POSTGRES_HOST,
    POSTGRES_PORT,
    POSTGRES_DB,
    POSTGRES_USER,
    POSTGRES_PASSWORD,
    NEO4J_URI,
    NEO4J_USER,
    NEO4J_PASSWORD,
    NEO4J_DATABASE,
)


def get_postgres_connection():
    """Create and return a PostgreSQL connection."""
    return psycopg.connect(
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        dbname=POSTGRES_DB,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
    )


def get_neo4j_driver():
    """Create and return a Neo4j driver."""
    return GraphDatabase.driver(
        NEO4J_URI,
        auth=(NEO4J_USER, NEO4J_PASSWORD),
    )


def test_postgres_connection():
    """Test PostgreSQL connectivity."""
    connection = get_postgres_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1;")
            result = cursor.fetchone()

        return result[0] == 1

    finally:
        connection.close()


def test_neo4j_connection():
    """Test Neo4j connectivity."""
    driver = get_neo4j_driver()

    try:
        with driver.session(database=NEO4J_DATABASE) as session:
            result = session.run("RETURN 1 AS test").single()

        return result["test"] == 1

    finally:
        driver.close()