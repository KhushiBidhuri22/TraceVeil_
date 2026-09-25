import os

from dotenv import load_dotenv
from neo4j import GraphDatabase


load_dotenv()


class Neo4jService:
    def __init__(self):
        user = os.getenv("NEO4J_USER", "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "sih_password")
        self.database = os.getenv("NEO4J_DATABASE", "neo4j")

        env_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        candidates = [env_uri, "bolt://localhost:7687", "bolt://127.0.0.1:7687", "bolt://neo4j:7687"]

        self.driver = None
        for uri in candidates:
            try:
                driver = GraphDatabase.driver(uri, auth=(user, password))
                driver.verify_connectivity()
                self.driver = driver
                break
            except Exception:
                continue

        if self.driver is None:
            # Fallback driver without verify_connectivity to avoid startup crash
            self.driver = GraphDatabase.driver(env_uri, auth=(user, password))

    def verify(self):
        if self.driver:
            self.driver.verify_connectivity()

    def close(self):
        if self.driver:
            self.driver.close()

    def get_actor_graph(self, actor_id: str) -> dict:
        query = """
        MATCH (actor:Entity {
            entity_type: 'actor',
            entity_id: $actor_id
        })
        OPTIONAL MATCH path = (actor)-[*1..2]-(related)
        RETURN actor, collect(path) AS paths
        """

        try:
            records, _, _ = self.driver.execute_query(
                query,
                actor_id=str(actor_id),
                database_=self.database,
            )
        except Exception:
            return {
                "actor_id": str(actor_id),
                "nodes": [],
                "edges": [],
                "metrics": {},
                "related_actors": [],
                "graph_score": 0.0,
                "evidence": [],
            }

        if not records:
            return {
                "actor_id": str(actor_id),
                "nodes": [],
                "edges": [],
                "metrics": {},
                "related_actors": [],
                "graph_score": 0.0,
                "evidence": [],
            }

        record = records[0]
        actor = record["actor"]
        paths = record["paths"]
        nodes_by_id = {}
        edges_by_id = {}

        def add_node(node):
            entity_type = str(
                node.get("entity_type", "entity")
            ).lower()
            node_id = node.element_id
            entity_id = str(
                node.get("entity_id", node_id)
            )
            nodes_by_id[node_id] = {
                "id": node_id,
                "entity_id": entity_id,
                "entity_type": entity_type,
                "type": entity_type,
                "label": entity_id,
            }

        add_node(actor)

        for path in paths:
            if path is None:
                continue
            for node in path.nodes:
                add_node(node)
            for relationship in path.relationships:
                edges_by_id[relationship.element_id] = {
                    "id": relationship.element_id,
                    "source": relationship.start_node.element_id,
                    "target": relationship.end_node.element_id,
                    "type": relationship.type,
                    "confidence": relationship.get("confidence"),
                    "observed_at": relationship.get("event_timestamp"),
                }

        related_actor_count = sum(
            1
            for node in nodes_by_id.values()
            if node["entity_type"] == "actor"
            and node["id"] != actor.element_id
        )

        graph_score = min(related_actor_count * 0.15, 1.0)

        return {
            "actor_id": str(actor_id),
            "nodes": list(nodes_by_id.values()),
            "edges": list(edges_by_id.values()),
            "metrics": {
                "node_count": len(nodes_by_id),
                "edge_count": len(edges_by_id),
                "related_actor_count": related_actor_count,
            },
            "related_actors": [
                node["entity_id"]
                for node in nodes_by_id.values()
                if node["entity_type"] == "actor"
                and node["id"] != actor.element_id
            ],
            "graph_score": round(graph_score, 3),
            "evidence": [],
        }