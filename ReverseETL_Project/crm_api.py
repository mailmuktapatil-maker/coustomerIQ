
from datetime import datetime, timezone
from pathlib import Path
import json

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

# ---------------- CONFIGURATION ----------------
BASE_DIR = Path(__file__).resolve().parent
CRM_FILE = BASE_DIR / "data" / "mock_crm.json"

app = FastAPI(
    title="CustomerIQ Mock CRM",
    description="Mock CRM API for Reverse ETL customer synchronization",
    version="1.0.0",
)


# ---------------- DATA MODEL ----------------
class Customer(BaseModel):
    customer_id: str | int
    segment: str
    total_spend: float = Field(ge=0)
    days_since_last_purchase: int = Field(ge=0)


# ---------------- STORAGE HELPERS ----------------
def read_customers():
    if not CRM_FILE.exists():
        return {}

    try:
        with CRM_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        raise HTTPException(
            status_code=500,
            detail="Could not read CRM storage.",
        )


def write_customers(customers):
    CRM_FILE.parent.mkdir(parents=True, exist_ok=True)

    temporary_file = CRM_FILE.with_suffix(".tmp")

    with temporary_file.open("w", encoding="utf-8") as file:
        json.dump(customers, file, indent=2)

    temporary_file.replace(CRM_FILE)


# ---------------- API ENDPOINTS ----------------
@app.get("/")
def home():
    return {
        "message": "CustomerIQ Mock CRM is running",
        "docs": "/docs",
        "customers_endpoint": "/customers",
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/customers")
def get_customers():
    customers = read_customers()

    return {
        "total_customers": len(customers),
        "customers": list(customers.values()),
    }


@app.post("/customers/sync")
def sync_customers(records: list[Customer]):
    customers = read_customers()
    now = datetime.now(timezone.utc).isoformat()

    created = 0
    updated = 0

    for record in records:
        customer = record.model_dump()
        customer_id = str(customer["customer_id"])

        if customer_id in customers:
            updated += 1
        else:
            created += 1

        customer["customer_id"] = customer_id
        customer["last_synced_at"] = now
        customers[customer_id] = customer

    write_customers(customers)

    return {
        "status": "success",
        "received": len(records),
        "created": created,
        "updated": updated,
        "total_customers_in_crm": len(customers),
        "synced_at": now,
    }


@app.get("/customers/{customer_id}")
def get_customer(customer_id: str):
    customers = read_customers()
    customer = customers.get(customer_id)

    if customer is None:
        raise HTTPException(
            status_code=404,
            detail="Customer not found",
        )

    return customer
