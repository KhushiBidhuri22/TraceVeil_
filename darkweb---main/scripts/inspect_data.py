from pathlib import Path
import pandas as pd


# Find the project folder automatically
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Location of our raw CSV files
DATA_DIR = PROJECT_ROOT / "data" / "raw"


def inspect_csv(file_path: Path) -> None:
    """Inspect one CSV file and print useful information."""

    print("\n" + "=" * 70)
    print(f"FILE: {file_path.name}")
    print("=" * 70)

    # Read the CSV
    df = pd.read_csv(file_path)

    # Basic information
    print(f"Rows: {len(df):,}")
    print(f"Columns: {len(df.columns)}")

    print("\nColumns:")
    for column in df.columns:
        print(f"  - {column}")

    # Missing values
    print("\nMissing values:")
    missing = df.isnull().sum()

    missing_found = False

    for column, count in missing.items():
        if count > 0:
            missing_found = True
            percentage = (count / len(df)) * 100
            print(f"  - {column}: {count:,} ({percentage:.2f}%)")

    if not missing_found:
        print("  No missing values")

    # Show first 3 records
    print("\nFirst 3 records:")
    print(df.head(3).to_string(index=False))


def main() -> None:
    """Inspect every CSV file in the raw data directory."""

    if not DATA_DIR.exists():
        print(f"ERROR: Data directory not found: {DATA_DIR}")
        return

    csv_files = sorted(DATA_DIR.glob("*.csv"))

    if not csv_files:
        print(f"ERROR: No CSV files found in {DATA_DIR}")
        return

    print("=" * 70)
    print("SIH DARK WEB DATASET INSPECTOR")
    print("=" * 70)
    print(f"Data directory: {DATA_DIR}")
    print(f"CSV files found: {len(csv_files)}")

    for file_path in csv_files:
        inspect_csv(file_path)

    print("\n" + "=" * 70)
    print("INSPECTION COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()