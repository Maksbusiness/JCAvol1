import streamlit as st
import pandas as pd
from datetime import date

# Налаштування сторінки
st.set_page_config(page_title="Poster SaaS Admin", page_icon="🔐", layout="wide")

# --- AUTH SYSTEM ---
def check_password():
    """Проста перевірка пароля."""
    def password_entered():
        if st.session_state["password"] == st.secrets.get("admin_password", "admin123"):
            st.session_state["user_role"] = "Admin"
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # не зберігаємо пароль
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # Перший вхід
        st.text_input("Введіть пароль доступу", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        # Пароль невірний
        st.text_input("Введіть пароль доступу", type="password", on_change=password_entered, key="password")
        st.error("😕 Пароль невірний")
        return False
    else:
        # Пароль вірний
        return True

# --- PAGE LOADERS (Fault Tolerance) ---
def load_dashboard_page():
    """Безпечне завантаження дашборду."""
    try:
        from modules.data_processor import DataProcessor
        from modules.db_handler import GoogleSheetHandler
        import plotly.express as px

        st.title("📊 Аналітичний Дашборд")
        gs = GoogleSheetHandler()
        processor = DataProcessor()
        
        sheet_name = st.session_state.get('sheet_name', "Poster ERP Data")

        if st.button("🔄 Оновити дані"):
            with st.spinner("Завантаження..."):
                df = gs.read_data(sheet_name, "Transactions")
                if not df.empty:
                    df = processor.prepare_transactions(df)
                    st.session_state['dash_data'] = df
        
        if 'dash_data' in st.session_state:
            df = st.session_state['dash_data']
            kpi = processor.calculate_kpi(df)
            col1, col2 = st.columns(2)
            col1.metric("Виторг", f"{kpi['revenue']} ₴")
            col1.metric("Чеки", kpi['checks'])
            
            # Графік
            hourly = processor.get_hourly_sales(df)
            if not hourly.empty:
                st.plotly_chart(px.bar(hourly, x='Година', y='Виторг'), use_container_width=True)
        else:
            st.info("Натисніть кнопку оновлення.")

    except ImportError as e:
        st.error(f"⚠️ Помилка імпорту модуля: {e}")
    except Exception as e:
        st.error(f"⚠️ Критична помилка на сторінці: {e}")

def load_data_lake_page():
    """Сторінка синхронізації (Data Lake)."""
    try:
        from modules.api_client import PosterClient
        from modules.db_handler import GoogleSheetHandler

        st.title("💾 Data Lake Synchronization")
        
        poster = PosterClient()
        gs = GoogleSheetHandler()

        sheet_name = st.text_input("Google Sheet Name", value="Poster ERP Data")
        st.session_state['sheet_name'] = sheet_name # Зберігаємо глобально

        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Транзакційні дані")
            d_range = st.date_input("Період", value=(date.today(), date.today()))
            if st.button("📥 Завантажити Чеки"):
                if len(d_range) == 2:
                    data = poster.get_transactions(str(d_range[0]), str(d_range[1]))
                    if data:
                        gs.save_transactions(pd.DataFrame(data), sheet_name)
                        st.success(f"Збережено {len(data)} чеків.")

        with col2:
            st.subheader("Довідники (Master Data)")
            if st.button("📥 Завантажити Меню"):
                data = poster.get_menu()
                if data:
                    gs.save_menu(pd.DataFrame(data), sheet_name)
                    st.success(f"Збережено {len(data)} товарів.")
            
            if st.button("📥 Завантажити Категорії"):
                data = poster.get_categories()
                if data:
                    gs.save_categories(pd.DataFrame(data), sheet_name)
                    st.success(f"Збережено {len(data)} категорій.")

    except Exception as e:
        st.error(f"⚠️ Data Lake Error: {e}")

# --- MAIN ROUTER ---
def main():
    if not check_password():
        return

    # Sidebar Navigation
    st.sidebar.title(f"User: {st.session_state.get('user_role', 'Guest')}")
    
    page = st.sidebar.radio(
        "Навігація", 
        ["📊 Дашборд", "💾 Data Lake (Sync)", "⚙️ Налаштування"]
    )

    st.sidebar.divider()
    if st.sidebar.button("Вийти"):
        del st.session_state["password_correct"]
        st.rerun()

    # Page Routing
    if page == "📊 Дашборд":
        load_dashboard_page()
    elif page == "💾 Data Lake (Sync)":
        load_data_lake_page()
    elif page == "⚙️ Налаштування":
        st.title("⚙️ Налаштування системи")
        st.write("Тут будуть налаштування API ключів та доступів.")
        st.json(st.secrets.get("poster", {"status": "No secrets found"}))

if __name__ == "__main__":
    main()