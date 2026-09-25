import os
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def wait_for_postgres(timeout=60):
    print("Waiting for PostgreSQL to be ready...")
    start = time.time()
    while time.time() - start < timeout:
        try:
            import psycopg
            conn = psycopg.connect(
                host=os.getenv("POSTGRES_HOST", "postgres"),
                port=int(os.getenv("POSTGRES_PORT", "5432")),
                dbname=os.getenv("POSTGRES_DB", "sih_darkweb"),
                user=os.getenv("POSTGRES_USER", "sih_user"),
                password=os.getenv("POSTGRES_PASSWORD", "sih_password"),
            )
            conn.close()
            print("PostgreSQL is ready.")
            return True
        except Exception as e:
            time.sleep(2)
    print("PostgreSQL connection timed out.")
    return False


def wait_for_neo4j(timeout=60):
    print("Waiting for Neo4j to be ready...")
    start = time.time()
    while time.time() - start < timeout:
        try:
            from neo4j import GraphDatabase
            driver = GraphDatabase.driver(
                os.getenv("NEO4J_URI", "bolt://neo4j:7687"),
                auth=(
                    os.getenv("NEO4J_USER", "neo4j"),
                    os.getenv("NEO4J_PASSWORD", "sih_password"),
                ),
            )
            driver.verify_connectivity()
            driver.close()
            print("Neo4j is ready.")
            return True
        except Exception as e:
            time.sleep(2)
    print("Neo4j connection timed out.")
    return False


def seed_database():
    import psycopg
    conn = psycopg.connect(
        host=os.getenv("POSTGRES_HOST", "postgres"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        dbname=os.getenv("POSTGRES_DB", "sih_darkweb"),
        user=os.getenv("POSTGRES_USER", "sih_user"),
        password=os.getenv("POSTGRES_PASSWORD", "sih_password"),
    )
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public';")
        tbl_count = cur.fetchone()[0]
    conn.close()

    if tbl_count == 0:
        print("Initializing PostgreSQL tables and loading dataset...")
        from scripts.load_postgres import main as load_pg
        load_pg()
    else:
        print(f"PostgreSQL already has {tbl_count} tables populated.")


def seed_neo4j():
    from neo4j import GraphDatabase
    driver = GraphDatabase.driver(
        os.getenv("NEO4J_URI", "bolt://neo4j:7687"),
        auth=(
            os.getenv("NEO4J_USER", "neo4j"),
            os.getenv("NEO4J_PASSWORD", "sih_password"),
        ),
    )
    database = os.getenv("NEO4J_DATABASE", "neo4j")
    with driver.session(database=database) as session:
        result = session.run("MATCH (n) RETURN count(n) AS c").single()
        node_count = result["c"] if result else 0
    driver.close()

    if node_count == 0:
        print("Populating Neo4j graph database...")
        from backend.graph_loader.neo4j_loader import main as load_n4j
        load_n4j()
    else:
        print(f"Neo4j already contains {node_count} nodes.")


def train_ml():
    print("Ensuring ML model artifacts are trained...")
    from ml.train_model import train_and_save_model
    train_and_save_model()


def main():
    print("=" * 60)
    print("TRACEVEIL / SIH PIPELINE INITIALIZER")
    print("=" * 60)

    if not wait_for_postgres():
        print("Warning: Skipping postgres seed due to timeout.")
    else:
        try:
            seed_database()
        except Exception as e:
            print(f"Postgres seed error: {e}")

    if not wait_for_neo4j():
        print("Warning: Skipping neo4j seed due to timeout.")
    else:
        try:
            seed_neo4j()
        except Exception as e:
            print(f"Neo4j seed error: {e}")

    try:
        train_ml()
    except Exception as e:
        print(f"ML training error: {e}")

    print("=" * 60)
    print("Initialization complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
