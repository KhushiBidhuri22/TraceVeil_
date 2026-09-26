import os
from typing import Any

from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()


class Neo4jGraphService:
    def __init__(self):
        uri = os.getenv("NEO4J_URI")
        username = os.getenv("NEO4J_USERNAME")
        password = os.getenv("NEO4J_PASSWORD")
        database = os.getenv("NEO4J_DATABASE", "neo4j")

        if not uri or not username or not password:
            raise RuntimeError(
                "Neo4j environment variables are missing."
            )

        self.database = database
        self.driver = GraphDatabase.driver(
            uri,
            auth=(username, password),
        )

    def verify(self):
        self.driver.verify_connectivity()

    def close(self):
        self.driver.close()

    def get_actor_graph(self, actor_id: int) -> dict:
        query = """
        MATCH (actor:Actor {id: $actor_id})
        OPTIONAL MATCH path = (actor)-[*1..2]-(related)
        RETURN actor, collect(path) AS paths
        """

        records, _, _ = self.driver.execute_query(
            query,
            actor_id=actor_id,
            database_=self.database,
        )

        if not records:
            return {
                "actor_id": actor_id,
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

        nodes_by_id: dict[str, dict[str, Any]] = {}
        edges: list[dict[str, Any]] = []
        edge_keys = set()

        for path in paths:
            if path is None:
                continue

            for node in path.nodes:
                node_id = str(node.element_id)

                nodes_by_id[node_id] = {
                    "id": node_id,
                    "type": list(node.labels)[0]
                    if node.labels
                    else "node",
                    "label": node.get(
                        "handle",
                        node.get("value", node_id),
                    ),
                }

            for relationship in path.relationships:
                edge_key = (
                    relationship.element_id,
                    relationship.start_node.element_id,
                    relationship.end_node.element_id,
                )

                if edge_key in edge_keys:
                    continue

                edge_keys.add(edge_key)

                edges.append({
                    "source": relationship.start_node.element_id,
                    "target": relationship.end_node.element_id,
                    "relation": relationship.type,
                })

        related_actors = [
            node["id"]
            for node in nodes_by_id.values()
            if node["type"] == "Actor"
            and node["id"] != str(actor.element_id)
        ]

        graph_score = min(
            len(related_actors) * 0.15,
            1.0,
        )

        evidence = []

        if related_actors:
            evidence.append({
                "type": "graph_relationship",
                "description": (
                    f"{len(related_actors)} related actor(s) "
                    "were found in the graph."
                ),
                "source": "neo4j",
                "weight": graph_score,
            })

        return {
            "actor_id": actor_id,
            "nodes": list(nodes_by_id.values()),
            "edges": edges,
            "metrics": {
                "node_count": len(nodes_by_id),
                "edge_count": len(edges),
                "related_actor_count": len(related_actors),
            },
            "related_actors": related_actors,
            "graph_score": round(graph_score, 3),
            "evidence": evidence,
        }