import csv
from datetime import datetime
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import Post

SQLALCHEMY_DATABASE_URL = "sqlite:///./app.db"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def load_sources(sources_path: Path) -> dict[str, str]:
    """
    Load sources.csv and return a mapping: source_id -> source_name.
    """
    source_map = {}

    with sources_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            sid = row["source_id"].strip()
            sname = row["source_name"].strip()
            source_map[sid] = sname

    return source_map


def parse_timestamp(ts_str: str) -> datetime:
    """
    Parse ISO8601 timestamp, handling 'Z' suffix.
    Falls back to now if parsing fails.
    """
    ts_str = ts_str.strip()
    if not ts_str:
        return datetime.utcnow()

    try:
        # Handle Z suffix
        if ts_str.endswith("Z"):
            ts_str = ts_str[:-1] + "+00:00"
        return datetime.fromisoformat(ts_str)
    except ValueError:
        return datetime.utcnow()


def load_observations(sources_path: Path, observations_path: Path):
    source_map = load_sources(sources_path)

    db = SessionLocal()
    try:
        with observations_path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for row in reader:
                source_id = row["source_id"].strip()
                source_name = source_map.get(source_id, f"UnknownSource({source_id})")

                handle = row["handle"].strip()
                if not handle:
                    # Skip observations without a handle
                    continue

                content = row["content"].strip()
                pgp_key = row.get("pgp_key", "").strip() or None
                wallet = row.get("wallet_address", "").strip() or None

                ts = parse_timestamp(row.get("timestamp", ""))

                post = Post(
                    source=source_name,
                    handle=handle,
                    pgp_key=pgp_key,
                    wallet=wallet,
                    text=content,
                    timestamp=ts,
                )

                db.add(post)

        db.commit()
        print("Observations loaded successfully into posts table.")
    except Exception as e:
        db.rollback()
        print("Error loading observations:", e)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    base_data_dir = Path(__file__).parent.parent / "data"

    sources_csv = base_data_dir / "sources.csv"
    observations_csv = base_data_dir / "observations.csv"

    load_observations(sources_csv, observations_csv)