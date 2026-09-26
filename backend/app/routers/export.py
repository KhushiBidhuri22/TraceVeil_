import csv
import io
import json
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Actor, Identifier
from ..services.actor_service import build_actor_dossier

router = APIRouter(prefix="/export", tags=["export"])


def actor_to_dict(actor):
    return {
        "id": actor.actor_id or str(actor.id),
        "primary_handle": actor.primary_handle,
        "confidence": actor.confidence,
        "last_seen": (
            actor.last_seen.isoformat()
            if actor.last_seen
            else None
        ),
        "identifiers": [
            {
                "id": str(identifier.id),
                "type": identifier.type,
                "value": identifier.value,
            }
            for identifier in (actor.identifiers or [])
        ],
    }


@router.get("/actors")
def export_actors_csv(db: Session = Depends(get_db)):
    """
    Export all actors and their basic information as CSV.
    """
    actors = db.query(Actor).all()

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "id",
        "primary_handle",
        "confidence",
        "last_seen",
        "identifier_count",
    ])

    for actor in actors:
        writer.writerow([
            actor.actor_id or actor.id,
            actor.primary_handle,
            actor.confidence,
            actor.last_seen.isoformat() if actor.last_seen else "",
            len(actor.identifiers) if actor.identifiers else 0,
        ])

    output.seek(0)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="actors.csv"'
        },
    )


@router.get("/actors/json")
def export_actors_json(db: Session = Depends(get_db)):
    """
    Export all actors and identifiers as JSON.
    """
    actors = db.query(Actor).all()
    return [actor_to_dict(actor) for actor in actors]


@router.get("/actors/{actor_id}/report")
def export_actor_report(actor_id: str, db: Session = Depends(get_db)):
    """
    Return a structured report for one actor.
    """
    actor = db.query(Actor).filter(Actor.actor_id == actor_id).first()
    if not actor:
        ident = db.query(Identifier).filter(
            Identifier.identifier_value.ilike(actor_id)
        ).first()
        if ident and ident.actor:
            actor = ident.actor

    if not actor:
        raise HTTPException(status_code=404, detail=f"Actor '{actor_id}' not found")

    dossier = build_actor_dossier(actor, db, include_graph=True)

    return {
        "report_type": "actor_intelligence_report",
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "actor": dossier,
        "note": (
            "This report is based on synthetic or authorized "
            "threat-intelligence data."
        ),
    }


@router.get("/{actor_id}")
def export_actor_record(
    actor_id: str,
    format: str = Query("json", pattern="^(csv|json)$"),
    db: Session = Depends(get_db),
):
    """
    Export a single actor's full intelligence dossier or connection records as CSV or JSON.
    Used directly by the TraceVeil frontend export modal.
    """
    actor = db.query(Actor).filter(Actor.actor_id == actor_id).first()
    if not actor:
        ident = db.query(Identifier).filter(
            Identifier.identifier_value.ilike(actor_id)
        ).first()
        if ident and ident.actor:
            actor = ident.actor

    if not actor:
        actor = db.query(Actor).filter(Actor.primary_handle.ilike(actor_id)).first()

    if not actor:
        raise HTTPException(status_code=404, detail=f"Actor '{actor_id}' not found.")

    dossier = build_actor_dossier(actor, db, include_graph=True)
    clean_actor_id = actor.actor_id or str(actor.id)

    if format.lower() == "csv":
        output = io.StringIO()
        writer = csv.writer(output)

        # Write header
        writer.writerow([
            "Category",
            "Type",
            "Identifier / Value",
            "Relation",
            "Confidence (%)",
            "Observed Date",
            "Source",
            "Detail",
        ])

        # Primary handle row
        writer.writerow([
            "Profile",
            "primary_handle",
            actor.primary_handle,
            "PRIMARY",
            dossier.get("confidence", 85.0),
            dossier.get("lastSeen", ""),
            "TraceVeil Intelligence",
            f"Actor ID: {clean_actor_id}",
        ])

        # Aliases
        for alias in dossier.get("aliases", []):
            writer.writerow([
                "Alias",
                "handle",
                alias.get("handle", ""),
                "ALIAS_OF",
                alias.get("confidence", 90.0),
                dossier.get("lastSeen", ""),
                "Forum / Market Crawl",
                alias.get("detail", ""),
            ])

        # PGP Keys
        for key in dossier.get("keys", []):
            writer.writerow([
                "PGP Key",
                "pgp_key",
                key.get("value", ""),
                "USES_PGP",
                key.get("confidence", 95.0),
                dossier.get("lastSeen", ""),
                "Public Keyserver / Forum",
                key.get("algorithm", "RSA-4096 / PGP"),
            ])

        # Wallets
        for wallet in dossier.get("wallets", []):
            writer.writerow([
                "Wallet",
                "crypto_wallet",
                wallet.get("value", ""),
                "USES_WALLET",
                wallet.get("confidence", 85.0),
                dossier.get("lastSeen", ""),
                "Darkweb Ledger / Post",
                wallet.get("network", "Cryptocurrency"),
            ])

        # Sources
        for source in dossier.get("sources", []):
            writer.writerow([
                "Source",
                "source_feed",
                source.get("name", ""),
                "OBSERVED_ON",
                source.get("confidence", 80.0),
                source.get("observedAt", ""),
                source.get("name", ""),
                source.get("detail", ""),
            ])

        # Evidence
        for ev in dossier.get("evidence", []):
            writer.writerow([
                "Evidence",
                "evidence_item",
                ev.get("detail", ""),
                "EVIDENCE_FOR",
                ev.get("confidence", 85.0),
                ev.get("date", ""),
                ev.get("source", ""),
                ev.get("method", ""),
            ])

        # Timeline Events
        for event in dossier.get("events", []):
            writer.writerow([
                "Timeline Event",
                event.get("label", "POST"),
                event.get("title", ""),
                "POSTED_ON",
                event.get("confidence", 80.0),
                event.get("date", ""),
                event.get("source", ""),
                event.get("detail", ""),
            ])

        output.seek(0)
        filename = f"traceveil-{clean_actor_id}.csv"
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
            },
        )

    # JSON export
    export_data = {
        "report_type": "traceveil_account_intelligence_record",
        "version": "2.0.0",
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "actor": dossier,
        "note": "Authorized threat intelligence export generated from TraceVeil Platform.",
    }
    output = io.StringIO()
    json.dump(export_data, output, indent=2)
    output.seek(0)
    filename = f"traceveil-{clean_actor_id}.json"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )