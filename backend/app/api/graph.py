from fastapi import APIRouter
from ..services.neo4j_service import Neo4jService

router = APIRouter(
    prefix="/graph",
    tags=["graph"],
)

neo4j_service = Neo4jService()


@router.get("/{actor_id}")
def get_actor_graph(actor_id: str):
    clean_id = str(actor_id).strip()
    result = neo4j_service.get_actor_graph(clean_id)

    if result and result.get("nodes"):
        return result

    # Fallback to actor dossier graph from database / ML pipeline
    try:
        from .actors import get_actor
        actor_data = get_actor(clean_id)
        if actor_data and "actor" in actor_data and "graph" in actor_data["actor"]:
            g = actor_data["actor"]["graph"]
            return {
                "actor_id": clean_id,
                "nodes": g.get("nodes", []),
                "edges": g.get("edges", []),
                "metrics": {
                    "node_count": len(g.get("nodes", [])),
                    "edge_count": len(g.get("edges", [])),
                },
                "related_actors": [
                    n["id"] for n in g.get("nodes", []) if n.get("type") in ["actor", "alias"] and n["id"] != clean_id
                ],
                "graph_score": 0.85,
                "evidence": actor_data["actor"].get("evidence", []),
            }
    except Exception:
        pass

    return {
        "actor_id": clean_id,
        "nodes": [
            {
                "id": clean_id,
                "name": clean_id,
                "type": "actor",
                "label": clean_id,
            }
        ],
        "edges": [],
        "metrics": {"node_count": 1, "edge_count": 0},
        "related_actors": [],
        "graph_score": 0.15,
        "evidence": [],
    }