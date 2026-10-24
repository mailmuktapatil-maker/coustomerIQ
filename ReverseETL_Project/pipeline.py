
from pathlib import Path

import duckdb
import pandas as pd


# Project file paths
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

SOURCE_FILE = DATA_DIR / "real_customers.csv"
SEGMENTED_FILE = DATA_DIR / "segmented_customers.csv"
DATABASE_FILE = DATA_DIR / "warehouse.duckdb"
EXPORT_FILE = DATA_DIR / "crm_export.csv"


def main():
    print("\n=== REVERSE ETL CUSTOMER SEGMENTATION ===")

    # 1. Read customer data
    if not SOURCE_FILE.exists():
        raise FileNotFoundError(
            f"Dataset not found: {SOURCE_FILE}"
        )

    customers = pd.read_csv(SOURCE_FILE)
    print(f"\nLoaded {len(customers)} customers.")

    # 2. Assign customer segments
    high_value = (
        (customers["total_spend"] >= 1000)
        & (customers["days_since_last_purchase"] <= 30)
    )

    at_risk = customers["days_since_last_purchase"] > 90

    customers["segment"] = "Regular"
    customers.loc[at_risk, "segment"] = "At Risk"
    customers.loc[high_value, "segment"] = "High Value"

    customers.to_csv(SEGMENTED_FILE, index=False)
    print("Customer segmentation completed.")

    # 3. Store data in DuckDB
    with duckdb.connect(str(DATABASE_FILE)) as connection:
        connection.register("customer_data", customers)

        connection.execute("""
            CREATE OR REPLACE TABLE customer_segments AS
            SELECT * FROM customer_data
        """)

        # 4. Validate results using SQL
        summary = connection.execute("""
            SELECT segment, COUNT(*) AS total_customers
            FROM customer_segments
            GROUP BY segment
            ORDER BY segment
        """).df()

        # 5. Prepare data for export
        export_data = connection.execute("""
            SELECT *
            FROM customer_segments
            ORDER BY customer_id
        """).df()

    # 6. Export CRM-ready data
    export_data.to_csv(EXPORT_FILE, index=False)

    print("\nCustomer Segment Summary")
    print(summary.to_string(index=False))

    print(f"\nTotal customers processed: {len(export_data)}")
    print(f"Database saved: {DATABASE_FILE.name}")
    print(f"Segmented data saved: {SEGMENTED_FILE.name}")
    print(f"CRM export saved: {EXPORT_FILE.name}")
    print("\nPipeline completed successfully!")


if __name__ == "__main__":
    main()
