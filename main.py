import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date

# Safe Imports (Dependency Injection pattern)
try:
    from modules.db_handler import DatabaseHandler
except ImportError:
    st.error("❌ Critical: Modules not found.")
    st.stop()

st.set_page_config(page_title="Poster SQL Analytics", page_icon="🐘", layout="wide")

# --- AUTHENTICATION ---
def check_auth():
    """Simple Role-Based Access Control."""
    if "user_role" not in st.session_state:
        st.session_state["user_role"] = None

    if st.session_state["user_role"]:
        return True

    # Login Form
    pwd = st.text_input("Enter Password", type="password")
    if pwd:
        if pwd == st.secrets["auth"]["admin_password"]:
            st.session_state["user_role"] = "Admin"
            st.rerun()
        elif pwd == st.secrets["auth"]["user_password"]:
            st.session_state["user_role"] = "User"
            st.rerun()
        else:
            st.error("Invalid password")
    return False

# --- FAULT TOLERANT LOADER ---
def safe_load_page(page_function):
    """Wraps page logic in a global try-except to prevent app crashes."""
    try:
        page_function()
    except Exception as e:
        st.error(f"💥 An unexpected error occurred on this page: {e}")
        st.info("Try refreshing or contacting support.")

# --- PAGES ---

def page_dashboard():
    st.title("📊 Business Dashboard")
    
    # Init DB only (No API connection here)
    db = DatabaseHandler()
    
    # Load Data
    with st.spinner("Fetching cached data from SQL..."):
        df_trans = db.load_data("transactions")
    
    if df_trans.empty:
        st.warning("📭 No data found in Database. Please ask Admin to Sync.")
        return

    # Data Processing (On the fly)
    try:
        # Basic transformations
        df_trans['date_close'] = pd.to_datetime(df_trans['date_close'])
        df_trans['payed_sum'] = pd.to_numeric(df_trans['payed_sum'], errors='coerce') / 100.0
        
        # Metrics
        total_rev = df_trans['payed_sum'].sum()
        total_checks = df_trans['transaction_id'].nunique()
        
        m1, m2 = st.columns(2)
        m1.metric("Total Revenue", f"{total_rev:,.2f} ₴")
        m2.metric("Total Checks", total_checks)
        
        # Visualization
        st.subheader("Revenue Timeline")
        hourly_sales = df_trans.groupby(df_trans['date_close'].dt.hour)['payed_sum'].sum().reset_index()
        hourly_sales.columns = ['Hour', 'Revenue']
        
        fig = px.bar(hourly_sales, x='Hour', y='Revenue', title="Sales by Hour")
        st.plotly_chart(fig, use_container_width=True)
        
    except Exception as e:
        st.error(f"Error processing data for visualization: {e}")

def page_sync():
    st.title("⚙️ Data Synchronization (Admin)")
    st.info("This module connects to Poster API and updates the PostgreSQL Database.")
    
    # Safe Import of API Client (Only needed here)
    try:
        from modules.api_client import PosterClient
    except ImportError:
        st.error("API Client module missing.")
        return

    # Controls
    col1, col2 = st.columns(2)
    with col1:
        d_range = st.date_input("Sync Period", value=(date.today(), date.today()))
    
    with col2:
        sync_btn = st.button("🚀 Start Full Sync", type="primary")

    if sync_btn and len(d_range) == 2:
        d_start, d_end = str(d_range[0]), str(d_range[1])
        
        api = PosterClient()
        db = DatabaseHandler()
        
        # Sync Process
        progress = st.progress(0)
        status_log = st.empty()
        
        steps = [
            ("Transactions", api.get_transactions, [d_start, d_end]),
            ("Products", api.get_menu_products, []),
            ("Ingredients", api.get_menu_ingredients, []),
            ("Employees", api.get_employees, []),
            ("Supplies", api.get_supplies, [d_start, d_end]),
            ("Wastes", api.get_wastes, [d_start, d_end]),
            ("Inventories", api.get_inventories, [d_start, d_end])
        ]
        
        total_steps = len(steps)
        
        for i, (name, func, args) in enumerate(steps):
            status_log.write(f"📥 Fetching {name}...")
            
            # Fetch
            df = func(*args)
            
            # Save
            if not df.empty:
                success = db.save_data(df, name.lower())
                if success:
                    status_log.write(f"✅ {name}: Saved {len(df)} records to DB.")
                else:
                    status_log.write(f"❌ {name}: Database save failed.")
            else:
                status_log.write(f"⚠️ {name}: API returned no data.")
            
            progress.progress((i + 1) / total_steps)
            
        status_log.success("🎉 Sync Cycle Completed!")

# --- ROUTER ---
def main():
    if not check_auth():
        return

    # Navigation
    st.sidebar.title("Navigation")
    role = st.session_state.get("user_role")
    
    pages = {"Dashboard": page_dashboard}
    
    if role == "Admin":
        pages["Data Sync"] = page_sync
        
    selection = st.sidebar.radio("Go to", list(pages.keys()))
    
    st.sidebar.divider()
    if st.sidebar.button("Logout"):
        st.session_state["user_role"] = None
        st.rerun()

    # Load Selected Page safely
    safe_load_page(pages[selection])

if __name__ == "__main__":
    main()
