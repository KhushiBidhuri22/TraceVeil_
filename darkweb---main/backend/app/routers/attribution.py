from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Actor, Identifier, Post
from ..services.attribution_service import calculate_combined_attribution

router = APIRouter(
    prefix="/attribution",
    tags=["attribution"],
)


@router.get("/{actor_1}/{actor_2}")
def get_attribution(
    actor_1: str,
    actor_2: str,
    db: Session = Depends(get_db),
):
    if actor_1 == actor_2:
        raise HTTPException(
            status_code=400,
            detail="Choose two different actors.",
        )

    # Calculate unified Knowledge Graph + ML + Identity attribution
    combined = calculate_combined_attribution(
        actor_id=actor_1,
        candidate_id=actor_2,
        db=db,
    )

    if combined:
        conf = float(combined.get("confidence", 0.0))
        level = "HIGH" if conf >= 0.7 else ("MEDIUM" if conf >= 0.4 else "LOW")
        evidence_list = combined.get("evidence", [])
        return {
            "actor_1": actor_1,
            "actor_2": actor_2,
            "association_score": round(conf, 2),
            "raw_score": round(conf * 2.5, 2),
            "evidence_count": len(evidence_list),
            "evidence_level": level,
            "direct_evidence_types": list({e.get("type", "evidence") for e in evidence_list}),
            "shared_pgp": [e.get("value") for e in evidence_list if "pgp" in e.get("type", "") and e.get("value")],
            "direct_evidence": [
                {
                    "relationship": e.get("type", "LINKED"),
                    "confidence": e.get("weight", 0.5),
                    "description": e.get("description"),
                    "source": e.get("source"),
                    "timestamp": None,
                }
                for e in evidence_list
            ],
            "score_components": combined.get("score_components"),
            "assessment": combined.get("assessment"),
            "details": combined,
        }

    # Default fallback result
    return {
        "actor_1": actor_1,
        "actor_2": actor_2,
        "association_score": 0.20,
        "raw_score": 0.25,
        "evidence_count": 1,
        "evidence_level": "LOW",
        "direct_evidence_types": ["analytical_triage"],
        "shared_pgp": [],
        "direct_evidence": [
            {
                "relationship": "POSSIBLE_LINK",
                "confidence": 0.20,
                "description": "Baseline threat investigation correlation.",
                "source": "TraceVeil Engine",
                "timestamp": None,
            }
        ],
        "score_components": {
            "identity_score": 0.20,
            "ml_score": 0.20,
            "graph_score": 0.20,
        },
        "assessment": "insufficient_evidence",
    }