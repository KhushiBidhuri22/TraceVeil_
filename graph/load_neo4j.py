import os
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from dotenv import load_dotenv
import psycopg
from neo4j import GraphDatabase

load_dotenv()

# ============================================================
# CONFIG
# ============================================================

POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_DB = os.getenv("POSTGRES_DB", "sih_darkweb")
POSTGRES_USER = os.getenv("POSTGRES_USER", "sih_user")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "sih_password")

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "sih_password")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")

BATCH_SIZE = int(os.getenv("NEO4J_BATCH_SIZE", "1000"))


# ============================================================
# HELPERS
# ============================================================

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


def clean_row(row):
    result = {}

    for key, value in row.items():
        value = clean_value(value)

        if value is not None:
            result[key] = value

    return result


def chunks(items, size):
    for i in range(0, len(items), size):
        yield items[i:i + size]


def entity_key(entity_type, entity_id):
    if entity_type is None or entity_id is None:
        return None

    return (
        str(entity_type).strip().lower()
        + ":"
        + str(entity_id).strip()
    )


def entity_label(entity_type):
    labels = {
        "actor": "Actor",
        "source": "Source",
        "post": "Post",
        "observation": "Observation",
        "identifier": "Identifier",
        "infrastructure": "Infrastructure",
        "wallet": "Wallet",
        "transaction": "Transaction",
        "event": "ActivityEvent",
        "activity_event": "ActivityEvent",
        "handle": "Handle",
        "pgp": "PGP",
        "domain": "Domain",
        "url": "URL",
        "email_alias": "EmailAlias",
        "username_alias": "UsernameAlias",
        "profile_id": "Profile",
    }

    return labels.get(
        str(entity_type).strip().lower(),
        "Entity"
    )


# ============================================================
# CONNECTIONS
# ============================================================

def connect_postgres():
    return psycopg.connect(
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        dbname=POSTGRES_DB,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
        row_factory=psycopg.rows.dict_row,
    )


def connect_neo4j():
    return GraphDatabase.driver(
        NEO4J_URI,
        auth=(
            NEO4J_USER,
            NEO4J_PASSWORD
        ),
    )


# ============================================================
# NEO4J TEST
# ============================================================

def verify_neo4j(driver):
    with driver.session(
        database=NEO4J_DATABASE
    ) as session:

        result = session.run(
            "RETURN 1 AS test"
        ).single()

        if result["test"] != 1:
            raise RuntimeError(
                "Neo4j connection test failed."
            )

    print("Neo4j connection successful.")


# ============================================================
# CLEAR GRAPH
# ============================================================

def clear_graph(driver):

    print("\nClearing existing Neo4j graph...")

    with driver.session(
        database=NEO4J_DATABASE
    ) as session:

        session.run(
            "MATCH (n) DETACH DELETE n"
        ).consume()

    print("Graph cleared.")


# ============================================================
# GENERIC ENTITY CREATION
# ============================================================

def create_entities(driver, entities):

    if not entities:
        return

    query = """
    UNWIND $rows AS row

    MERGE (e:Entity {
        entity_key: row.entity_key
    })

    SET e.entity_type = row.entity_type,
        e.entity_id = row.entity_id
    """

    with driver.session(
        database=NEO4J_DATABASE
    ) as session:

        for batch in chunks(
            entities,
            BATCH_SIZE
        ):

            session.run(
                query,
                rows=batch
            ).consume()


def add_label(
    driver,
    entity_type
):

    label = entity_label(entity_type)

    query = f"""
    MATCH (e:Entity)
    WHERE e.entity_type = $entity_type
    SET e:`{label}`
    """

    with driver.session(
        database=NEO4J_DATABASE
    ) as session:

        session.run(
            query,
            entity_type=str(
                entity_type
            ).lower()
        ).consume()


# ============================================================
# SIMPLE TABLE LOADER
# ============================================================

def load_table(
    driver,
    conn,
    table,
    id_column,
    entity_type,
    step_number
):

    print(
        f"\n[{step_number}/9] "
        f"Loading {table}..."
    )

    with conn.cursor() as cursor:

        cursor.execute(
            f'''
            SELECT *
            FROM "{table}"
            ORDER BY "{id_column}"
            '''
        )

        rows = cursor.fetchall()

    print(
        f"  Read {len(rows):,} rows."
    )

    entities = []

    for row in rows:

        item_id = row.get(
            id_column
        )

        if item_id is None:
            continue

        key = entity_key(
            entity_type,
            item_id
        )

        entities.append({
            "entity_key": key,
            "entity_type": entity_type,
            "entity_id": str(item_id)
        })

    create_entities(
        driver,
        entities
    )

    add_label(
        driver,
        entity_type
    )

    query = """
    UNWIND $rows AS row

    MATCH (e:Entity {
        entity_key: row.entity_key
    })

    SET e += row.properties
    """

    data = []

    for row in rows:

        item_id = row.get(
            id_column
        )

        if item_id is None:
            continue

        data.append({
            "entity_key": entity_key(
                entity_type,
                item_id
            ),
            "properties": clean_row(row)
        })

    with driver.session(
        database=NEO4J_DATABASE
    ) as session:

        total = 0

        for batch in chunks(
            data,
            BATCH_SIZE
        ):

            session.run(
                query,
                rows=batch
            ).consume()

            total += len(batch)

            print(
                f"  {total:,}/{len(data):,}"
            )

    print(
        f"Loaded {len(data):,} {entity_type} records."
    )


# ============================================================
# ACTORS
# ============================================================

def load_actors(driver, conn):

    print("\n[1/9] Loading actors...")

    with conn.cursor() as cursor:

        cursor.execute(
            """
            SELECT actor_id
            FROM actors
            ORDER BY actor_id
            """
        )

        rows = cursor.fetchall()

    entities = []

    for row in rows:

        actor_id = row["actor_id"]

        entities.append({
            "entity_key": entity_key(
                "actor",
                actor_id
            ),
            "entity_type": "actor",
            "entity_id": str(actor_id)
        })

    create_entities(
        driver,
        entities
    )

    add_label(
        driver,
        "actor"
    )

    print(
        f"Loaded {len(rows):,} actors."
    )


# ============================================================
# WALLET TRANSACTIONS
# ============================================================

def load_wallet_transactions(
    driver,
    conn
):

    print(
        "\n[7/9] Loading wallet transactions..."
    )

    with conn.cursor() as cursor:

        cursor.execute(
            """
            SELECT *
            FROM wallet_transactions
            ORDER BY transaction_id
            """
        )

        rows = cursor.fetchall()

    # --------------------------------------------------------
    # Wallets
    # --------------------------------------------------------

    wallets = set()

    for row in rows:

        if row.get("from_wallet"):
            wallets.add(
                str(row["from_wallet"])
            )

        if row.get("to_wallet"):
            wallets.add(
                str(row["to_wallet"])
            )

    wallet_entities = []

    for wallet in wallets:

        wallet_entities.append({
            "entity_key": entity_key(
                "wallet",
                wallet
            ),
            "entity_type": "wallet",
            "entity_id": wallet
        })

    create_entities(
        driver,
        wallet_entities
    )

    add_label(
        driver,
        "wallet"
    )

    print(
        f"Loaded {len(wallet_entities):,} wallets."
    )

    # --------------------------------------------------------
    # Transactions
    # --------------------------------------------------------

    transaction_entities = []

    for row in rows:

        transaction_id = row.get(
            "transaction_id"
        )

        if transaction_id is None:
            continue

        transaction_entities.append({
            "entity_key": entity_key(
                "transaction",
                transaction_id
            ),
            "entity_type": "transaction",
            "entity_id": str(transaction_id)
        })

    create_entities(
        driver,
        transaction_entities
    )

    add_label(
        driver,
        "transaction"
    )

    query = """
    UNWIND $rows AS row

    MATCH (e:Entity {
        entity_key: row.entity_key
    })

    SET e += row.properties
    """

    data = []

    for row in rows:

        transaction_id = row.get(
            "transaction_id"
        )

        if transaction_id is None:
            continue

        data.append({
            "entity_key": entity_key(
                "transaction",
                transaction_id
            ),
            "properties": clean_row(row)
        })

    with driver.session(
        database=NEO4J_DATABASE
    ) as session:

        total = 0

        for batch in chunks(
            data,
            BATCH_SIZE
        ):

            session.run(
                query,
                rows=batch
            ).consume()

            total += len(batch)

            print(
                f"  Transactions: "
                f"{total:,}/{len(data):,}"
            )

    # --------------------------------------------------------
    # Wallet paths
    # --------------------------------------------------------

    paths = []

    for row in rows:

        transaction_id = row.get(
            "transaction_id"
        )

        from_wallet = row.get(
            "from_wallet"
        )

        to_wallet = row.get(
            "to_wallet"
        )

        if not transaction_id:
            continue

        if not from_wallet or not to_wallet:
            continue

        paths.append({
            "transaction_id": str(
                transaction_id
            ),
            "from_wallet": str(
                from_wallet
            ),
            "to_wallet": str(
                to_wallet
            )
        })

    relationship_query = """
    UNWIND $rows AS row

    MATCH (from:Entity {
        entity_key:
            'wallet:' + row.from_wallet
    })

    MATCH (transaction:Entity {
        entity_key:
            'transaction:' + row.transaction_id
    })

    MATCH (to:Entity {
        entity_key:
            'wallet:' + row.to_wallet
    })

    MERGE (from)-[:SENT]->(transaction)

    MERGE (transaction)-[:RECEIVED_BY]->(to)
    """

    with driver.session(
        database=NEO4J_DATABASE
    ) as session:

        total = 0

        for batch in chunks(
            paths,
            BATCH_SIZE
        ):

            session.run(
                relationship_query,
                rows=batch
            ).consume()

            total += len(batch)

            print(
                f"  Wallet transaction paths: "
                f"{total:,}/{len(paths):,}"
            )

    print(
        f"Loaded {len(data):,} transactions."
    )


# ============================================================
# RELATIONSHIPS
# ============================================================

ALLOWED_RELATIONSHIPS = {
    "USES",
    "ALIAS_OF",
    "RELATED_TO",
    "CONNECTED_TO",
    "MENTIONED_IN",
    "POSTED_ON",
    "USES_WALLET",
    "USES_PGP",
    "ASSOCIATED_WITH",
    "SHARES_INFRASTRUCTURE",
    "INTERACTS_WITH",
    "REPLIED_TO",
    "MIGRATED_TO",
    "POSSIBLE_ALIAS_OF",
    "POSSIBLE_LINK",
    "TRANSACTED_WITH",
}


def load_relationships(
    driver,
    conn
):

    print(
        "\n[9/9] Loading graph relationships..."
    )

    # IMPORTANT:
    # These are the ACTUAL columns in the PostgreSQL table.
    #
    # There is:
    #   event_timestamp
    #
    # There is NOT:
    #   timestamp
    #   evidence_id
    #   relationship_status

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

    print(
        f"Read {len(rows):,} relationships."
    )

    # --------------------------------------------------------
    # Create every endpoint first.
    # This includes handles, which were missing before.
    # --------------------------------------------------------

    endpoint_map = {}

    for row in rows:

        source_key = entity_key(
            row["source_entity_type"],
            row["source_entity_id"]
        )

        target_key = entity_key(
            row["target_entity_type"],
            row["target_entity_id"]
        )

        if source_key:

            endpoint_map[source_key] = {
                "entity_key": source_key,
                "entity_type": str(
                    row["source_entity_type"]
                ).lower(),
                "entity_id": str(
                    row["source_entity_id"]
                )
            }

        if target_key:

            endpoint_map[target_key] = {
                "entity_key": target_key,
                "entity_type": str(
                    row["target_entity_type"]
                ).lower(),
                "entity_id": str(
                    row["target_entity_id"]
                )
            }

    endpoints = list(
        endpoint_map.values()
    )

    create_entities(
        driver,
        endpoints
    )

    # Add correct labels.
    entity_types = sorted(
        {
            x["entity_type"]
            for x in endpoints
        }
    )

    for entity_type in entity_types:

        add_label(
            driver,
            entity_type
        )

    print(
        f"Prepared {len(endpoints):,} "
        "unique relationship endpoints."
    )

    # --------------------------------------------------------
    # Group relationships by type.
    # --------------------------------------------------------

    grouped = {}

    skipped = 0

    for row in rows:

        relationship_type = str(
            row["relationship_type"]
        ).strip().upper()

        if relationship_type not in ALLOWED_RELATIONSHIPS:

            skipped += 1

            continue

        source_key = entity_key(
            row["source_entity_type"],
            row["source_entity_id"]
        )

        target_key = entity_key(
            row["target_entity_type"],
            row["target_entity_id"]
        )

        if not source_key or not target_key:

            skipped += 1

            continue

        grouped.setdefault(
            relationship_type,
            []
        ).append({

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
                row["source_id"]
            ),

            # CORRECT PostgreSQL column:
            "event_timestamp": clean_value(
                row["event_timestamp"]
            ),

            "confidence": clean_value(
                row["confidence"]
            ),
        })

    # --------------------------------------------------------
    # Create relationships.
    # --------------------------------------------------------

    for relationship_type in sorted(
        grouped
    ):

        relationship_rows = grouped[
            relationship_type
        ]

        print(
            f"\n{relationship_type}: "
            f"{len(relationship_rows):,}"
        )

        query = f"""
        UNWIND $rows AS row

        MATCH (source:Entity {{
            entity_key: row.source_key
        }})

        MATCH (target:Entity {{
            entity_key: row.target_key
        }})

        MERGE (
            source
        )-[
            r:{relationship_type}
        {{
            relationship_id:
                row.relationship_id
        }}
        ]->(
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

        with driver.session(
            database=NEO4J_DATABASE
        ) as session:

            total = 0

            for batch in chunks(
                relationship_rows,
                BATCH_SIZE
            ):

                session.run(
                    query,
                    rows=batch
                ).consume()

                total += len(batch)

                print(
                    f"  {total:,}/"
                    f"{len(relationship_rows):,}"
                )

    print(
        "\nRelationship loading finished."
    )

    print(
        f"Loaded "
        f"{len(rows) - skipped:,} relationships."
    )

    if skipped:

        print(
            f"Skipped {skipped:,} relationships."
        )


# ============================================================
# VERIFICATION
# ============================================================

def verify_graph(driver):

    print("\n")
    print("=" * 65)
    print("NEO4J GRAPH VERIFICATION")
    print("=" * 65)

    queries = [

        (
            "Total nodes",
            """
            MATCH (n)
            RETURN count(n) AS count
            """
        ),

        (
            "Total relationships",
            """
            MATCH ()-[r]->()
            RETURN count(r) AS count
            """
        ),

        (
            "Actors",
            """
            MATCH (n:Actor)
            RETURN count(n) AS count
            """
        ),

        (
            "Handles",
            """
            MATCH (n:Handle)
            RETURN count(n) AS count
            """
        ),

        (
            "Sources",
            """
            MATCH (n:Source)
            RETURN count(n) AS count
            """
        ),

        (
            "Posts",
            """
            MATCH (n:Post)
            RETURN count(n) AS count
            """
        ),

        (
            "Observations",
            """
            MATCH (n:Observation)
            RETURN count(n) AS count
            """
        ),

        (
            "Identifiers",
            """
            MATCH (n:Identifier)
            RETURN count(n) AS count
            """
        ),

        (
            "Infrastructure",
            """
            MATCH (n:Infrastructure)
            RETURN count(n) AS count
            """
        ),

        (
            "Wallets",
            """
            MATCH (n:Wallet)
            RETURN count(n) AS count
            """
        ),

        (
            "Transactions",
            """
            MATCH (n:Transaction)
            RETURN count(n) AS count
            """
        ),

        (
            "Activity events",
            """
            MATCH (n:ActivityEvent)
            RETURN count(n) AS count
            """
        ),

        (
            "PGP nodes",
            """
            MATCH (n:PGP)
            RETURN count(n) AS count
            """
        ),

        (
            "Domain nodes",
            """
            MATCH (n:Domain)
            RETURN count(n) AS count
            """
        ),
    ]

    with driver.session(
        database=NEO4J_DATABASE
    ) as session:

        for name, query in queries:

            result = session.run(
                query
            ).single()

            print(
                f"{name:<25}"
                f"{result['count']:,}"
            )

    print("=" * 65)


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 65)
    print("SIH DARK WEB PROJECT")
    print("POSTGRESQL -> NEO4J GRAPH LOADER")
    print("=" * 65)

    postgres = None
    neo4j = None

    try:

        # ----------------------------------------------------
        # PostgreSQL
        # ----------------------------------------------------

        print(
            "\nConnecting to PostgreSQL..."
        )

        postgres = connect_postgres()

        print(
            "PostgreSQL connection successful."
        )

        # ----------------------------------------------------
        # Neo4j
        # ----------------------------------------------------

        print(
            "\nConnecting to Neo4j..."
        )

        neo4j = connect_neo4j()

        verify_neo4j(
            neo4j
        )

        # ----------------------------------------------------
        # Start clean
        # ----------------------------------------------------

        clear_graph(
            neo4j
        )

        # ----------------------------------------------------
        # Load nodes
        # ----------------------------------------------------

        load_actors(
            neo4j,
            postgres
        )

        load_table(
            neo4j,
            postgres,
            "sources",
            "source_id",
            "source",
            2
        )

        load_table(
            neo4j,
            postgres,
            "posts",
            "post_id",
            "post",
            3
        )

        load_table(
            neo4j,
            postgres,
            "observations",
            "observation_id",
            "observation",
            4
        )

        load_table(
            neo4j,
            postgres,
            "identifiers",
            "identifier_id",
            "identifier",
            5
        )

        load_table(
            neo4j,
            postgres,
            "infrastructure",
            "indicator_id",
            "infrastructure",
            6
        )

        load_wallet_transactions(
            neo4j,
            postgres
        )

        load_table(
            neo4j,
            postgres,
            "activity_timeline",
            "event_id",
            "event",
            8
        )

        # ----------------------------------------------------
        # Relationships
        # ----------------------------------------------------

        load_relationships(
            neo4j,
            postgres
        )

        # ----------------------------------------------------
        # Verification
        # ----------------------------------------------------

        verify_graph(
            neo4j
        )

        print("\n")
        print("=" * 65)
        print("NEO4J GRAPH LOAD COMPLETE")
        print("=" * 65)

    except Exception as error:

        print("\n")
        print("=" * 65)
        print("ERROR")
        print("=" * 65)

        print(
            f"{type(error).__name__}: {error}"
        )

        raise

    finally:

        if postgres:
            postgres.close()

        if neo4j:
            neo4j.close()


if __name__ == "__main__":
    main()
