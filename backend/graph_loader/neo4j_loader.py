from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = (
    Path(__file__).resolve().parents[2]
)

ENV_PATH = PROJECT_ROOT / ".env"

load_dotenv(
    dotenv_path=ENV_PATH,
    override=True,
)

POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_DB = os.getenv("POSTGRES_DB", "sih_darkweb")
POSTGRES_USER = os.getenv("POSTGRES_USER", "sih_user")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")
BATCH_SIZE = int(os.getenv("NEO4J_BATCH_SIZE", "500"))

ALLOWED_RELATIONSHIPS = {
    "USES", "ALIAS_OF", "RELATED_TO", "CONNECTED_TO",
    "MENTIONED_IN", "POSTED_ON", "USES_WALLET", "USES_PGP",
    "ASSOCIATED_WITH", "SHARES_INFRASTRUCTURE", "INTERACTS_WITH",
    "REPLIED_TO", "MIGRATED_TO", "POSSIBLE_ALIAS_OF",
    "POSSIBLE_LINK", "TRANSACTED_WITH",
}


def clean_value(value: Any):
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, float) and value != value:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def clean_row(row: dict) -> dict:
    return {
        key: cleaned
        for key, value in row.items()
        if (cleaned := clean_value(value)) is not None
    }


def chunks(items: list, size: int):
    for index in range(0, len(items), size):
        yield items[index:index + size]


def entity_key(entity_type: Any, entity_id: Any):
    if entity_type is None or entity_id is None:
        return None
    return f"{str(entity_type).strip().lower()}:{str(entity_id).strip()}"


def entity_label(entity_type: Any) -> str:
    labels = {
        "actor": "Actor", "source": "Source", "post": "Post",
        "observation": "Observation", "identifier": "Identifier",
        "infrastructure": "Infrastructure", "wallet": "Wallet",
        "transaction": "Transaction", "event": "ActivityEvent",
        "activity_event": "ActivityEvent", "handle": "Handle",
        "pgp": "PGP", "pgp_key": "PGP", "domain": "Domain",
        "url": "URL", "email_alias": "EmailAlias",
        "username_alias": "UsernameAlias", "profile_id": "Profile",
    }
    return labels.get(str(entity_type).strip().lower(), "Entity")


def connect_postgres():
    if not POSTGRES_PASSWORD:
        raise RuntimeError("POSTGRES_PASSWORD is not configured.")
    return psycopg.connect(
        host=POSTGRES_HOST, port=POSTGRES_PORT, dbname=POSTGRES_DB,
        user=POSTGRES_USER, password=POSTGRES_PASSWORD, row_factory=dict_row,
    )


def connect_neo4j():
    if not NEO4J_PASSWORD:
        raise RuntimeError("NEO4J_PASSWORD is not configured.")
    return GraphDatabase.driver(
        NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD)
    )


def verify_neo4j(driver):
    records, _, _ = driver.execute_query(
        "RETURN 1 AS test", database_=NEO4J_DATABASE
    )
    if not records or records[0]["test"] != 1:
        raise RuntimeError("Neo4j connection test failed.")
    print("Neo4j connection successful.")


def clear_graph(driver):
    print("Clearing existing Neo4j graph...")
    driver.execute_query(
        "MATCH (n) DETACH DELETE n", database_=NEO4J_DATABASE
    )
    print("Graph cleared.")


def create_entities(driver, entities: list[dict]):
    if not entities:
        return
    query = """
    UNWIND $rows AS row
    MERGE (e:Entity {entity_key: row.entity_key})
    SET e.entity_type = row.entity_type, e.entity_id = row.entity_id
    """
    for batch in chunks(entities, BATCH_SIZE):
        driver.execute_query(query, rows=batch, database_=NEO4J_DATABASE)


def add_label(driver, entity_type: str):
    label = entity_label(entity_type)
    query = f"""
    MATCH (e:Entity)
    WHERE e.entity_type = $entity_type
    SET e:{label}
    """
    driver.execute_query(
        query, entity_type=str(entity_type).lower(), database_=NEO4J_DATABASE
    )


def load_table(driver, conn, table: str, id_column: str, entity_type: str, step_number: int):
    print(f"\n[{step_number}/9] Loading {table}...")
    with conn.cursor() as cursor:
        cursor.execute(f'SELECT * FROM "{table}" ORDER BY "{id_column}"')
        rows = cursor.fetchall()
    print(f"Read {len(rows):,} rows.")

    entities = []
    data = []
    for row in rows:
        item_id = row.get(id_column)
        if item_id is None:
            continue
        key = entity_key(entity_type, item_id)
        entities.append({"entity_key": key, "entity_type": entity_type, "entity_id": str(item_id)})
        data.append({"entity_key": key, "properties": clean_row(row)})

    create_entities(driver, entities)
    add_label(driver, entity_type)

    query = """
    UNWIND $rows AS row
    MATCH (e:Entity {entity_key: row.entity_key})
    SET e += row.properties
    """
    for batch in chunks(data, BATCH_SIZE):
        driver.execute_query(query, rows=batch, database_=NEO4J_DATABASE)
    print(f"Loaded {len(data):,} {entity_type} records.")


def load_actors(driver, conn):
    print("\n[1/9] Loading actors...")
    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM actors ORDER BY actor_id")
        rows = cursor.fetchall()
    entities = []
    for row in rows:
        actor_id = row.get("actor_id")
        if actor_id is not None:
            entities.append({
                "entity_key": entity_key("actor", actor_id),
                "entity_type": "actor",
                "entity_id": str(actor_id),
            })
    create_entities(driver, entities)
    add_label(driver, "actor")
    print(f"Loaded {len(entities):,} actors.")


def load_wallet_transactions(driver, conn):
    print("\n[7/9] Loading wallet transactions...")
    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM wallet_transactions ORDER BY transaction_id")
        rows = cursor.fetchall()

    wallets = set()
    transactions = []
    transaction_data = []
    paths = []

    for row in rows:
        for column in ("from_wallet", "to_wallet"):
            if row.get(column):
                wallets.add(str(row[column]))
        transaction_id = row.get("transaction_id")
        if transaction_id is None:
            continue
        transaction_id = str(transaction_id)
        transactions.append({
            "entity_key": entity_key("transaction", transaction_id),
            "entity_type": "transaction",
            "entity_id": transaction_id,
        })
        transaction_data.append({
            "entity_key": entity_key("transaction", transaction_id),
            "properties": clean_row(row),
        })
        if row.get("from_wallet") and row.get("to_wallet"):
            paths.append({
                "transaction_id": transaction_id,
                "from_wallet": str(row["from_wallet"]),
                "to_wallet": str(row["to_wallet"]),
            })

    create_entities(driver, [
        {"entity_key": entity_key("wallet", wallet), "entity_type": "wallet", "entity_id": wallet}
        for wallet in wallets
    ])
    add_label(driver, "wallet")
    create_entities(driver, transactions)
    add_label(driver, "transaction")

    property_query = """
    UNWIND $rows AS row
    MATCH (e:Entity {entity_key: row.entity_key})
    SET e += row.properties
    """
    for batch in chunks(transaction_data, BATCH_SIZE):
        driver.execute_query(property_query, rows=batch, database_=NEO4J_DATABASE)

    relationship_query = """
    UNWIND $rows AS row
    MATCH (from:Entity {entity_key: 'wallet:' + row.from_wallet})
    MATCH (transaction:Entity {entity_key: 'transaction:' + row.transaction_id})
    MATCH (to:Entity {entity_key: 'wallet:' + row.to_wallet})
    MERGE (from)-[:SENT]->(transaction)
    MERGE (transaction)-[:RECEIVED_BY]->(to)
    """
    for batch in chunks(paths, BATCH_SIZE):
        driver.execute_query(relationship_query, rows=batch, database_=NEO4J_DATABASE)
    print(f"Loaded {len(transaction_data):,} transactions and {len(paths):,} wallet paths.")


def load_relationships(driver, conn):
    print("\n[9/9] Loading graph relationships...")

    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                relationship_id,
                source_entity_type,
                source_entity_id,
                relationship_type,
                target_entity_type,
                target_entity_id,
                source_id,
                event_timestamp,
                confidence
            FROM relationships
            ORDER BY relationship_id
            """
        )
        rows = cursor.fetchall()

    endpoints = {}
    grouped = {}
    skipped = 0

    for row in rows:
        source_key = entity_key(
            row.get("source_entity_type"),
            row.get("source_entity_id"),
        )

        target_key = entity_key(
            row.get("target_entity_type"),
            row.get("target_entity_id"),
        )

        if source_key:
            endpoints[source_key] = {
                "entity_key": source_key,
                "entity_type": str(
                    row["source_entity_type"]
                ).lower(),
                "entity_id": str(
                    row["source_entity_id"]
                ),
            }

        if target_key:
            endpoints[target_key] = {
                "entity_key": target_key,
                "entity_type": str(
                    row["target_entity_type"]
                ).lower(),
                "entity_id": str(
                    row["target_entity_id"]
                ),
            }

        relationship_type = str(
            row.get("relationship_type") or ""
        ).strip().upper()

        if (
            relationship_type not in ALLOWED_RELATIONSHIPS
            or not source_key
            or not target_key
        ):
            skipped += 1
            continue

        relationship_data = {
            "relationship_id": str(
                row["relationship_id"]
            ),
            "source_key": source_key,
            "target_key": target_key,
            "source_type": str(
                row["source_entity_type"]
            ).lower(),
            "target_type": str(
                row["target_entity_type"]
            ).lower(),
            "source_id": str(
                row["source_entity_id"]
            ),
            "target_id": str(
                row["target_entity_id"]
            ),
            "source_id_original": clean_value(
                row.get("source_id")
            ),
            "event_timestamp": clean_value(
                row.get("event_timestamp")
            ),
            "confidence": clean_value(
                row.get("confidence")
            ),
        }

        grouped.setdefault(
            relationship_type,
            [],
        ).append(relationship_data)

    endpoint_list = list(endpoints.values())

    create_entities(
        driver,
        endpoint_list,
    )

    endpoint_types = {
        item["entity_type"]
        for item in endpoint_list
    }

    for entity_type in endpoint_types:
        add_label(
            driver,
            entity_type,
        )

    for relationship_type in sorted(grouped):
        relationship_rows = grouped[
            relationship_type
        ]

        query = f"""
        UNWIND $rows AS row

        MATCH (
            source:Entity {{
                entity_key: row.source_key
            }}
        )

        MATCH (
            target:Entity {{
                entity_key: row.target_key
            }}
        )

        MERGE (
            source
        )-[r:{relationship_type} {{
            relationship_id: row.relationship_id
        }}]->(
            target
        )

        SET r.source_type =
                row.source_type,

            r.target_type =
                row.target_type,

            r.source_id =
                row.source_id,

            r.target_id =
                row.target_id,

            r.source_id_original =
                row.source_id_original,

            r.event_timestamp =
                row.event_timestamp,

            r.confidence =
                row.confidence
        """

        for batch in chunks(
            relationship_rows,
            BATCH_SIZE,
        ):
            driver.execute_query(
                query,
                rows=batch,
                database_=NEO4J_DATABASE,
            )

        print(
            f"Loaded {len(relationship_rows):,} "
            f"{relationship_type} relationships."
        )

    print(
        f"Skipped {skipped:,} relationships."
    )

def main():
    conn = connect_postgres()
    driver = connect_neo4j()

    try:
        verify_neo4j(driver)
        clear_graph(driver)
        driver.execute_query(
        "CREATE INDEX entity_key_index IF NOT EXISTS FOR (e:Entity) ON (e.entity_key)",
        database_=NEO4J_DATABASE,
)

        load_actors(driver, conn)
        load_table(driver, conn, "sources", "source_id", "source", 2)
        load_table(driver, conn, "observations", "observation_id", "observation", 3)
        load_table(driver, conn, "posts", "post_id", "post", 4)
        load_table(driver, conn, "identifiers", "identifier_id", "identifier", 5)
        load_table(driver, conn, "infrastructure", "indicator_id", "infrastructure", 6)
        load_wallet_transactions(driver, conn)
        load_table(driver, conn, "activity_timeline", "event_id", "activity_event", 8)
        load_relationships(driver, conn)

        print("\nAll data loaded successfully.")

    finally:
        conn.close()
        driver.close()


if __name__ == "__main__":
    main()