
from pathlib import Path
import subprocess
import sys
import requests
import pandas as pd
import plotly.express as px
import streamlit as st

# ---------------- PAGE CONFIG ----------------
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
SOURCE_FILE = DATA_DIR / "raw_customers.csv"
SEGMENTED_FILE = DATA_DIR / "segmented_customers.csv"
PIPELINE_FILE = BASE_DIR / "pipeline.py"
CRM_API_URL = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="CustomerIQ",
    page_icon="📊",
    layout="wide",
)

# ---------------- DARK THEME ----------------
st.markdown("""
<style>
.stApp {
    background-color: #0b1020;
    color: #f1f5f9;
}
.block-container {
    max-width: 1450px;
    padding-top: 2rem;
}
[data-testid="stMetric"] {
    background: #151e33;
    border: 1px solid #293651;
    padding: 18px;
    border-radius: 14px;
}
h1, h2, h3 {
    color: #f8fafc;
}
</style>
""", unsafe_allow_html=True)

# ---------------- HEADER ----------------
st.title("📊 CustomerIQ")
st.caption("CUSTOMER INTELLIGENCE  /  SEGMENTATION  /  REVERSE ETL")
st.write(
    "Monitor customer segments, explore spending patterns, "
    "and prepare customer data for CRM synchronization."
)
st.divider()

# ---------------- SIDEBAR ----------------
st.sidebar.title("Control Center")

if st.sidebar.button("▶ Run Segmentation", use_container_width=True):
    if not PIPELINE_FILE.exists():
        st.sidebar.error("pipeline.py not found.")
    elif not SOURCE_FILE.exists():
        st.sidebar.error("raw_customers.csv not found.")
    else:
        with st.spinner("Running segmentation pipeline..."):
            result = subprocess.run(
                [sys.executable, str(PIPELINE_FILE)],
                cwd=str(BASE_DIR),
                capture_output=True,
                text=True,
                timeout=120,
            )

        if result.returncode == 0:
            st.sidebar.success("Pipeline completed successfully!")
            st.cache_data.clear()
            st.rerun()
        else:
            st.sidebar.error("Pipeline failed.")
            st.sidebar.code(result.stderr[-3000:])

st.sidebar.divider()
st.sidebar.write("📄 Customer CSV")
st.sidebar.write("🗄️ DuckDB warehouse")
st.sidebar.write("🔄 CRM export")

# ---------------- LOAD DATA ----------------
if not SEGMENTED_FILE.exists():
    st.warning("Run the segmentation pipeline first.")
    st.stop()

@st.cache_data
def load_customers(file_path, modified_time):
    return pd.read_csv(file_path)

df = load_customers(
    str(SEGMENTED_FILE),
    SEGMENTED_FILE.stat().st_mtime,
)

required = {
    "customer_id",
    "total_spend",
    "days_since_last_purchase",
    "segment",
}

missing = required - set(df.columns)

if missing:
    st.error(f"Missing columns: {', '.join(sorted(missing))}")
    st.stop()

df["total_spend"] = pd.to_numeric(
    df["total_spend"], errors="coerce"
)
df["days_since_last_purchase"] = pd.to_numeric(
    df["days_since_last_purchase"], errors="coerce"
)
df["segment"] = df["segment"].fillna("Unknown").astype(str)

# ---------------- FILTERS ----------------
st.subheader("Customer Overview")

segments = sorted(df["segment"].unique().tolist())

selected = st.multiselect(
    "Filter by segment",
    segments,
    default=segments,
)

filtered = df[df["segment"].isin(selected)].copy()

# ---------------- METRICS ----------------
c1, c2, c3, c4 = st.columns(4)

c1.metric("Total Customers", f"{len(filtered):,}")
c2.metric("Total Spend", f"{filtered['total_spend'].sum():,.2f}")

average = filtered["total_spend"].mean()
c3.metric("Average Spend", f"{average:,.2f}" if pd.notna(average) else "—")

at_risk = (filtered["segment"] == "At Risk").sum()
c4.metric("At-Risk Customers", f"{at_risk:,}")

st.divider()

# ---------------- CHARTS ----------------
st.subheader("Customer Analytics")

left, right = st.columns(2)

with left:
    counts = (
        filtered["segment"]
        .value_counts()
        .rename_axis("Segment")
        .reset_index(name="Customers")
    )

    pie = px.pie(
        counts,
        names="Segment",
        values="Customers",
        hole=0.58,
        title="Customer Segment Distribution",
        color="Segment",
        color_discrete_map={
            "High Value": "#34d399",
            "At Risk": "#fbbf24",
            "Regular": "#818cf8",
        },
    )
    pie.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(pie, use_container_width=True)

with right:
    spending = filtered.groupby(
        "segment", as_index=False
    )["total_spend"].sum()

    bar = px.bar(
        spending,
        x="segment",
        y="total_spend",
        color="segment",
        title="Total Spend by Segment",
        color_discrete_map={
            "High Value": "#34d399",
            "At Risk": "#fbbf24",
            "Regular": "#818cf8",
        },
    )
    bar.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
    )
    st.plotly_chart(bar, use_container_width=True)

# ---------------- CUSTOMER EXPLORER ----------------
st.divider()
st.subheader("Customer Explorer")

query = st.text_input(
    "Search customers",
    placeholder="Enter customer ID, name, or email",
)

table = filtered.copy()

if query.strip():
    mask = pd.Series(False, index=table.index)

    for column in ["customer_id", "name", "email"]:
        if column in table.columns:
            mask |= table[column].astype(str).str.contains(
                query.strip(),
                case=False,
                na=False,
                regex=False,
            )

    table = table[mask]

table = table.sort_values(
    "total_spend", ascending=False, na_position="last"
)

st.caption(f"{len(table)} customer records")
st.dataframe(table, use_container_width=True, hide_index=True)

# ---------------- CRM EXPORT ----------------

# ---------------- CRM SYNC ----------------
st.divider()
st.subheader("🔄 Reverse ETL & CRM Synchronization")

st.write(
    "Send the currently filtered customer records to the "
    "FastAPI mock CRM."
)

# Check CRM connection
crm_online = False
crm_count = 0

try:
    health_response = requests.get(
        f"{CRM_API_URL}/health", timeout=3
    )
    crm_online = health_response.ok

    if crm_online:
        crm_response = requests.get(
            f"{CRM_API_URL}/customers", timeout=5
        )
        crm_response.raise_for_status()
        crm_count = crm_response.json()["total_customers"]

except requests.RequestException:
    crm_online = False

col1, col2 = st.columns(2)

with col1:
    st.metric("CRM Connection", "Online" if crm_online else "Offline")

with col2:
    st.metric("Customers in CRM", crm_count)

if not crm_online:
    st.warning(
        "CRM API is offline. Start it using: "
        "python -m uvicorn crm_api:app --reload --port 8000"
    )

if st.button(
    "🚀 Sync Customers to CRM",
    disabled=not crm_online or filtered.empty,
    use_container_width=True,
):
    try:
        records = filtered.copy()

        records["customer_id"] = (
            records["customer_id"].astype(str)
        )

        # Keep only fields supported by the mock CRM API.
        required_fields = [
            "customer_id",
            "segment",
            "total_spend",
            "days_since_last_purchase",
        ]

        payload_df = records[required_fields].copy()
        payload_df["total_spend"] = pd.to_numeric(
            payload_df["total_spend"], errors="raise"
        )
        payload_df["days_since_last_purchase"] = pd.to_numeric(
            payload_df["days_since_last_purchase"],
            errors="raise",
        )

        if payload_df.isna().any().any():
            st.error("Customer records contain missing required values.")
        elif (
            (payload_df["total_spend"] < 0).any()
            or (payload_df["days_since_last_purchase"] < 0).any()
        ):
            st.error("Spend and purchase recency cannot be negative.")
        else:
            with st.spinner("Synchronizing customers..."):
                response = requests.post(
                    f"{CRM_API_URL}/customers/sync",
                    json=payload_df.to_dict(orient="records"),
                    timeout=15,
                )

            response.raise_for_status()
            result = response.json()

            st.session_state["last_sync_result"] = result
            st.session_state["last_sync_status"] = "Success"
            st.session_state["last_sync_records"] = len(payload_df)
            st.session_state["last_sync_time"] = result.get(
                "synced_at", ""
            )

            st.success(
                f"Sync successful! Created: {result['created']} | "
                f"Updated: {result['updated']}"
            )
            st.rerun()

    except requests.RequestException as exc:
        st.session_state["last_sync_status"] = "Failed"
        st.session_state["last_sync_records"] = len(filtered)
        st.session_state["last_sync_time"] = pd.Timestamp.now().isoformat()
        st.error(f"CRM synchronization failed: {exc}")

    except (ValueError, KeyError) as exc:
        st.error(f"Could not process CRM response: {exc}")

# ---------------- SYNC HISTORY ----------------
st.subheader("📋 Latest Sync Activity")

if "last_sync_result" in st.session_state:
    result = st.session_state["last_sync_result"]

    st.write(f"**Status:** {st.session_state['last_sync_status']}")
    st.write(f"**Time:** {st.session_state['last_sync_time']}")
    st.write(f"**Records submitted:** {st.session_state['last_sync_records']}")
    st.json(result)

elif "last_sync_status" in st.session_state:
    st.write(f"**Status:** {st.session_state['last_sync_status']}")
    st.write(f"**Time:** {st.session_state.get('last_sync_time', '')}")
    st.write(f"**Records submitted:** {st.session_state.get('last_sync_records', 0)}")

else:
    st.info("No synchronization attempts recorded in this session.")

# ---------------- CSV EXPORT ----------------
st.subheader("📥 CSV Export")

st.download_button(
    "Download Filtered CRM CSV",
    data=filtered.to_csv(index=False).encode("utf-8"),
    file_name="crm_export.csv",
    mime="text/csv",
)

st.caption(
    "CustomerIQ | Python · pandas · DuckDB · Streamlit · FastAPI"
)

