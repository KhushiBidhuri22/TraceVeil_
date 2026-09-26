import csv
import os

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
OUTPUT_PATH = os.path.join(DATA_DIR, "00_actors.csv")

# file -> list of columns that contain actor_id values
SOURCES = {
    "02_observations.csv": ["actor_id"],
    "03_posts.csv": ["actor_id"],
    "04_identifiers.csv": ["actor_id"],
    "05_infrastructure.csv": ["actor_id"],
    "07_wallet_transactions.csv": ["actor_from", "actor_to"],
    "08_activity_timeline.csv": ["actor_id"],
}


def main():
    actor_ids = set()

    for filename, columns in SOURCES.items():
        path = os.path.join(DATA_DIR, filename)
        if not os.path.exists(path):
            print(f"  [SKIP] {filename} not found")
            continue

        with open(path, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                for col in columns:
                    val = row.get(col)
                    if val and val.strip():
                        actor_ids.add(val.strip())

    print(f"Found {len(actor_ids)} unique actor_id values")

    with open(OUTPUT_PATH, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["actor_id"])
        for actor_id in sorted(actor_ids):
            writer.writerow([actor_id])

    print(f"Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()