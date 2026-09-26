import os
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv

# Load .env
load_dotenv()

POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "sih_darkweb")
POSTGRES_USER = os.getenv("POSTGRES_USER", "sih_user")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "sih_password")
ENV_POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")


def create_resilient_engine():
    raw_db_url = os.getenv("DATABASE_URL")
    if raw_db_url:
        url = raw_db_url.replace("postgresql://", "postgresql+psycopg://")
        try:
            eng = create_engine(url, pool_pre_ping=True, connect_args={"connect_timeout": 1})
            with eng.connect() as conn:
                conn.execute(text("SELECT 1"))
            return eng
        except Exception:
            pass

    # Instant SQLite fallback for local development
    backend_dir = Path(__file__).resolve().parents[1]
    db_path = backend_dir / "app.db"
    return create_engine(
        f"sqlite:///{db_path.as_posix()}",
        connect_args={"check_same_thread": False},
    )


engine = create_resilient_engine()

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    # Import models here (not at module top) to avoid circular imports,
    # while still guaranteeing every model class is registered on Base
    # before create_all() runs.
    from . import models  # noqa: F401

    Base.metadata.create_all(bind=engine)

    # Auto-seed if database has 0 actors
    db = SessionLocal()
    try:
        if db.query(models.Actor).count() == 0:
            csv_path = None
            for p in [
                Path(__file__).resolve().parents[2] / "04_identifiers.csv",
                Path(__file__).resolve().parents[2] / "data" / "raw" / "04_identifiers.csv",
            ]:
                if p.exists():
                    csv_path = p
                    break
            if csv_path:
                import pandas as pd
                df = pd.read_csv(csv_path)
                df["first_seen"] = pd.to_datetime(df["first_seen"], errors="coerce")
                df["last_seen"] = pd.to_datetime(df["last_seen"], errors="coerce")
                actor_ids = df["actor_id"].unique()
                actors = [models.Actor(actor_id=str(aid)) for aid in actor_ids]
                db.add_all(actors)
                db.commit()

                idents = []
                for _, r in df.iterrows():
                    idents.append(models.Identifier(
                        identifier_id=str(r["identifier_id"]),
                        actor_id=str(r["actor_id"]),
                        identifier_type=str(r["identifier_type"]),
                        identifier_value=str(r["identifier_value"]),
                        source_id=str(r["source_id"]),
                        first_seen=r["first_seen"] if pd.notnull(r["first_seen"]) else None,
                        last_seen=r["last_seen"] if pd.notnull(r["last_seen"]) else None,
                        confidence=float(r["confidence"]) if pd.notnull(r["confidence"]) else 0.85,
                        status=str(r["status"]) if pd.notnull(r["status"]) else None,
                        observation_id=str(r["observation_id"]) if pd.notnull(r["observation_id"]) else None,
                    ))
                db.bulk_save_objects(idents)
                db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()