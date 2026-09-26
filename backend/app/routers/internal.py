from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..services.actor_service import sync_actors_from_posts
from ..services.neo4j_service import Neo4jService
from ..services.neo4j_sync import sync_actors_to_neo4j


router = APIRouter(prefix="/internal", tags=["internal"])


@router.post("/sync-actors")
def sync_actors(db: Session = Depends(get_db)):
    """
    Sync actors from posts table.
    Turns raw observations into actor profiles + identifiers.
    """
    sync_actors_from_posts(db)
    return {"status": "ok", "message": "Actors synced from posts"}

@router.post("/sync-neo4j")
def sync_neo4j(db: Session = Depends(get_db)):
    neo4j = Neo4jService()
    sync_actors_to_neo4j(db, neo4j)
    neo4j.close()
    return {"status": "ok", "message": "Actors synced to Neo4j"}
