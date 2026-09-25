from sqlalchemy.orm import Session
from ..models import Actor, Identifier
from .neo4j_service import Neo4jService

IDENTIFIER_TYPE_MAP = {
    "handle": "handle",
    "pgp_key": "key",
    "wallet": "wallet",
}

def sync_actors_to_neo4j(db: Session, neo4j: Neo4jService):
    actors = db.query(Actor).all()

    for actor in actors:
        actor_entity_id = str(actor.id)

        neo4j.driver.execute_query(
            """
            MERGE (a:Entity {entity_type: 'actor', entity_id: $entity_id})
            SET a.confidence = $confidence
            """,
            entity_id=actor_entity_id,
            confidence=actor.confidence or 0.0,
            database_=neo4j.database,
        )

        for ident in actor.identifiers:
            entity_type = IDENTIFIER_TYPE_MAP.get(ident.type, ident.type)
            ident_entity_id = f"{ident.type}:{ident.value}"

            neo4j.driver.execute_query(
                """
                MERGE (i:Entity {entity_type: $entity_type, entity_id: $entity_id})
                """,
                entity_type=entity_type,
                entity_id=ident_entity_id,
                database_=neo4j.database,
            )

            neo4j.driver.execute_query(
                """
                MATCH (a:Entity {entity_type: 'actor', entity_id: $actor_id})
                MATCH (i:Entity {entity_type: $entity_type, entity_id: $ident_id})
                MERGE (a)-[:HAS_IDENTIFIER]->(i)
                """,
                actor_id=actor_entity_id,
                entity_type=entity_type,
                ident_id=ident_entity_id,
                database_=neo4j.database,
            )