
from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

SOURCE_FILE = DATA_DIR / "Online Retail.xlsx"
OUTPUT_FILE = DATA_DIR / "real_customers.csv"

print("Loading retail transactions...")
df = pd.read_excel(SOURCE_FILE)

print("Original transactions:", len(df))

# Remove transactions without a customer ID
df = df.dropna(subset=["CustomerID"]).copy()

# Convert data types
df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"])
df["CustomerID"] = df["CustomerID"].astype(int)

# Remove cancelled invoices
df = df[~df["InvoiceNo"].astype(str).str.startswith("C")]

# Remove invalid quantities and prices
df = df[(df["Quantity"] > 0) & (df["UnitPrice"] > 0)]

# Calculate the value of each transaction line
df["line_spend"] = df["Quantity"] * df["UnitPrice"]

# Use the day after the latest recorded transaction
reference_date = df["InvoiceDate"].max().normalize() + pd.Timedelta(days=1)

# Create one row per customer
customers = df.groupby("CustomerID").agg(
    total_spend=("line_spend", "sum"),
    purchase_frequency=("InvoiceNo", "nunique"),
    last_purchase=("InvoiceDate", "max"),
).reset_index()

# Calculate recency in days
customers["days_since_last_purchase"] = (
    reference_date - customers["last_purchase"]
).dt.days

# Add compatible customer IDs and simple placeholder details
customers["customer_id"] = customers["CustomerID"].astype(str)
customers["name"] = customers["customer_id"].apply(
    lambda x: f"Customer {x}"
)
customers["email"] = ""

# Apply the existing CustomerIQ segmentation rules
high_value = (
    (customers["total_spend"] >= 1000)
    & (customers["days_since_last_purchase"] <= 30)
)
at_risk = customers["days_since_last_purchase"] > 90

customers["segment"] = "Regular"
customers.loc[at_risk, "segment"] = "At Risk"
customers.loc[high_value, "segment"] = "High Value"

# Keep columns compatible with the current pipeline and dashboard
customers = customers[
    [
        "customer_id",
        "name",
        "email",
        "total_spend",
        "days_since_last_purchase",
        "purchase_frequency",
        "segment",
    ]
]

customers.to_csv(OUTPUT_FILE, index=False)

print("\nCustomer-level data prepared successfully!")
print("Unique customers:", len(customers))
print("\nSegment counts:")
print(customers["segment"].value_counts())
print("\nSaved to:", OUTPUT_FILE)
print("\nFirst five customers:")
print(customers.head().to_string(index=False))
