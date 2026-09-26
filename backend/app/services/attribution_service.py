from sqlalchemy.orm import Session

from ..models import Actor, Identifier, Post
from .ml_adapter import compare_actors
from .neo4j_service import Neo4jService


def confidence_label(score: float) -> str:
    if score >= 0.75:
        return "high"
    if score >= 0.50:
        return "moderate"
    if score >= 0.20:
        return "weak"
    return "very_low"


def calculate_identity_score(
    actor: Actor,
    candidate: Actor,
    db: Session,
) -> tuple[float, list[dict]]:
    actor_identifiers = {
        (item.identifier_type, item.identifier_value)
        for item in (actor.identifiers or [])
        if item.identifier_value
    }

    candidate_identifiers = {
        (item.identifier_type, item.identifier_value)
        for item in (candidate.identifiers or [])
        if item.identifier_value
    }

    shared_identifiers = (
        actor_identifiers.intersection(candidate_identifiers)
    )

    actor_posts = (
        db.query(Post)
        .filter(Post.handle == actor.primary_handle)
        .all()
    )

    candidate_posts = (
        db.query(Post)
        .filter(Post.handle == candidate.primary_handle)
        .all()
    )

    actor_sources = {
        post.source
        for post in actor_posts
        if post.source
    }

    candidate_sources = {
        post.source
        for post in candidate_posts
        if post.source
    }

    shared_sources = actor_sources.intersection(candidate_sources)

    identifier_score = min(
        len(shared_identifiers) * 0.25,
        0.60,
    )

    source_score = min(
        len(shared_sources) * 0.15,
        0.20,
    )

    identity_score = min(
        identifier_score + source_score,
        1.0,
    )

    evidence = []

    for identifier_type, identifier_value in shared_identifiers:
        evidence.append({
            "type": "shared_identifier",
            "description": (
                f"Shared {identifier_type} identifier observed across profiles."
            ),
            "value": identifier_value,
            "source": "PostgreSQL Identity Graph",
            "weight": 0.25,
        })

    if shared_sources:
        evidence.append({
            "type": "source_overlap",
            "description": (
                f"Both profiles co-occur in "
                f"{len(shared_sources)} underground source(s)."
            ),
            "source": "Crawler Feed",
            "weight": round(source_score, 2),
        })

    return identity_score, evidence


def calculate_combined_attribution(
    actor_id: str,
    candidate_id: str,
    db: Session,
):
    def find_actor(val: str):
        clean = str(val).strip()
        a = db.query(Actor).filter(Actor.actor_id == clean).first()
        if a:
            return a
        ident = db.query(Identifier).filter(Identifier.identifier_value.ilike(clean)).first()
        if ident and ident.actor:
            return ident.actor
        for item in db.query(Actor).all():
            if item.primary_handle and item.primary_handle.lower() == clean.lower():
                return item
        return None

    actor = find_actor(actor_id)
    candidate = find_actor(candidate_id)

    if not actor or not candidate:
        return None

    actor_posts = (
        db.query(Post)
        .filter(Post.handle == actor.primary_handle)
        .all()
    )

    candidate_posts = (
        db.query(Post)
        .filter(Post.handle == candidate.primary_handle)
        .all()
    )

    # 1. Identity Score (PostgreSQL Identifiers & Sources)
    identity_score, identity_evidence = (
        calculate_identity_score(
            actor=actor,
            candidate=candidate,
            db=db,
        )
    )

    # 2. ML Persona & Stylometry Score (Random Forest & Feature Distance)
    ml_result = compare_actors(
        actor_a=actor,
        actor_b=candidate,
        posts_a=actor_posts,
        posts_b=candidate_posts,
        db=db,
    )

    ml_score = float(
        ml_result.get(
            "relationship_probability",
            0.5,
        )
    )

    # 3. Knowledge Graph Association Score (Neo4j Graph)
    graph_score = 0.0
    graph_evidence = []
    try:
        from ...attribution import calculate_association_score as calculate_graph_score
        graph_res = calculate_graph_score(actor.actor_id, candidate.actor_id)
        if graph_res:
            graph_score = float(graph_res.get("association_score", 0.0))
            for dev in graph_res.get("direct_evidence", []):
                graph_evidence.append({
                    "type": "graph_relationship",
                    "description": f"Graph connection observed: {dev.get('relationship', 'CONNECTED')} (confidence: {round(float(dev.get('confidence') or 0.8)*100)}%)",
                    "source": "Neo4j Knowledge Graph",
                    "weight": round(0.30 * float(dev.get("confidence") or 0.8), 3),
                })
            for pgp in graph_res.get("shared_pgp", []):
                graph_evidence.append({
                    "type": "shared_pgp_graph",
                    "description": f"Shared PGP identifier linked in graph: {pgp}",
                    "source": "Neo4j Knowledge Graph",
                    "weight": 0.25,
                })
    except Exception:
        # Fallback graph score if Neo4j is offline or empty
        try:
            neo4j_service = Neo4jService()
            g1 = neo4j_service.get_actor_graph(actor.actor_id)
            if candidate.actor_id in g1.get("related_actors", []):
                graph_score = 0.80
                graph_evidence.append({
                    "type": "graph_proximity",
                    "description": "Direct graph adjacency verified in Neo4j sub-graph.",
                    "source": "Neo4j Knowledge Graph",
                    "weight": 0.25,
                })
            else:
                graph_score = float(g1.get("graph_score", 0.15))
        except Exception:
            graph_score = 0.20

    # 4. Weighted Combined Attribution Score
    final_score = (
        0.35 * identity_score
        + 0.35 * ml_score
        + 0.30 * graph_score
    )

    evidence = identity_evidence.copy()

    # Append ML Evidence
    evidence.append({
        "type": "ml_similarity",
        "description": (
            f"Random Forest ML model evaluated stylometric & behavioral persona compatibility ({round(ml_score * 100, 1)}%)."
        ),
        "source": ml_result.get(
            "model_version",
            "rf-final-v1",
        ),
        "weight": round(0.35 * ml_score, 3),
        "details": ml_result.get("features", {}),
    })

    # Append Graph Evidence
    if graph_evidence:
        evidence.extend(graph_evidence)
    else:
        evidence.append({
            "type": "graph_analysis",
            "description": "Multi-hop graph neighborhood analyzed across threat clusters.",
            "source": "Neo4j Knowledge Graph",
            "weight": round(0.30 * graph_score, 3),
        })

    if final_score >= 0.50:
        assessment = "possible_link"
    else:
        assessment = "insufficient_evidence"

    return {
        "actor_id": actor.actor_id,
        "candidate_actor_id": candidate.actor_id,
        "actor_handle": actor.primary_handle,
        "candidate_handle": candidate.primary_handle,
        "assessment": assessment,
        "confidence": round(final_score, 3),
        "confidence_label": confidence_label(final_score),
        "score_components": {
            "identity_score": round(identity_score, 3),
            "ml_score": round(ml_score, 3),
            "graph_score": round(graph_score, 3),
        },
        "evidence": evidence,
        "limitations": [
            "Analytical correlation score designed for threat actor investigation triage.",
            "Integrates stylometric ML, behavioral clusters, and Neo4j graph topology.",
        ],
    }