import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date

from modules.api_client import PosterClient
from modules.db_handler import GoogleSheetHandler
from modules.data_processor import DataProcessor

st.set_page_config(page_title="Poster Sync Center", page_icon="🔄", layout="wide")

# --- CSS FIX: BLACK TEXT IN CARDS ---
st.markdown("""
    <style>
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    div[data-testid="stMetric"] label {
        color: #000000 !important; /* Чорний заголовок */
    }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        color: #000000 !important; /* Чорне значення */
    }
    </style>
    """, unsafe_allow_html=True)

def main():
    st.title("🔄 Poster Sync & Analytics")

    # Ініціалізація
    poster = PosterClient()
    gs = GoogleSheetHandler()
    processor = DataProcessor()

    # Вкладки
    tab_analytics, tab_sync = st.tabs(["📊 Аналітика", "⚙️ Синхронізація"])

    # ==========================
    # Вкл 1: СИНХРОНІЗАЦІЯ (Write)
    # ==========================
    with tab_sync:
        st.header("Центр керування даними")
        
        col_s1, col_s2 = st.columns([1, 2])
        
        with col_s1:
            st.success("API Poster: Підключено ✅")
            
            # Налаштування
            sheet_name = st.text_input("Google Таблиця", value="Poster Data")
            
            sync_types = st.multiselect(
                "Що синхронізувати?",
                ["Чеки (Transactions)", "Товари (Menu)", "Поставки (Supplies)"],
                default=["Чеки (Transactions)"]
            )
            
            date_range = st.date_input(
                "Період синхронізації",
                value=(date.today(), date.today()),
                max_value=date.today()
            )

            start_sync = st.button("🚀 Запустити Синхронізацію", type="primary")

        with col_s2:
            st.info("ℹ️ Дані будуть записані в окремі вкладки Google Таблиці.")
            
            if start_sync:
                if isinstance(date_range, tuple) and len(date_range) == 2:
                    d_start = date_range[0].strftime("%Y-%m-%d")
                    d_end = date_range[1].strftime("%Y-%m-%d")
                    
                    progress_bar = st.progress(0)
                    log_area = st.empty()
                    
                    step = 0
                    total_steps = len(sync_types)
                    
                    # 1. Transactions
                    if "Чеки (Transactions)" in sync_types:
                        log_area.info("⏳ Завантаження чеків...")
                        data = poster.get_transactions(d_start, d_end)
                        if data:
                            gs.write_data(pd.DataFrame(data), sheet_name, "Transactions")
                            log_area.success(f"✅ Чеки: {len(data)} записів збережено.")
                        else:
                            log_area.warning("⚠️ Чеки: Даних не знайдено.")
                        step += 1
                        progress_bar.progress(step / total_steps)

                    # 2. Menu
                    if "Товари (Menu)" in sync_types:
                        log_area.info("⏳ Завантаження меню...")
                        data = poster.get_menu_products()
                        if data:
                            gs.write_data(pd.DataFrame(data), sheet_name, "Menu")
                            log_area.success(f"✅ Меню: {len(data)} товарів збережено.")
                        step += 1
                        progress_bar.progress(step / total_steps)

                    # 3. Supplies
                    if "Поставки (Supplies)" in sync_types:
                        log_area.info("⏳ Завантаження поставок...")
                        data = poster.get_supplies(d_start, d_end)
                        if data:
                            gs.write_data(pd.DataFrame(data), sheet_name, "Supplies")
                            log_area.success(f"✅ Поставки: {len(data)} записів збережено.")
                        else:
                            log_area.warning("⚠️ Поставки: Даних не знайдено.")
                        step += 1
                        progress_bar.progress(step / total_steps)
                    
                    st.balloons()
                else:
                    st.error("Оберіть коректний період.")

    # ==========================
    # Вкл 2: АНАЛІТИКА (Read)
    # ==========================
    with tab_analytics:
        col_ctrl, col_info = st.columns([1, 4])
        with col_ctrl:
            sheet_name_read = st.text_input("Джерело даних (Google Sheet)", value="Poster Data", key="read_sh")
            if st.button("🔄 Оновити з БД"):
                # Читаємо тільки транзакції для графіків
                with st.spinner("Читання даних..."):
                    df = gs.read_data(sheet_name_read, "Transactions")
                    st.session_state['df_analytics'] = df
        
        st.divider()

        if 'df_analytics' in st.session_state and not st.session_state['df_analytics'].empty:
            df = st.session_state['df_analytics']
            
            # --- МЕТРИКИ ---
            # Потрібно явно конвертувати payed_sum, бо це string
            df['payed_sum'] = pd.to_numeric(df.get('payed_sum', 0), errors='coerce')
            
            total_sum = (df['payed_sum'].sum()) / 100
            total_count = len(df)
            avg_check = total_sum / total_count if total_count > 0 else 0
            
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Загальний виторг", f"{total_sum:,.0f} ₴")
            m2.metric("Кількість чеків", f"{total_count}")
            m3.metric("Середній чек", f"{avg_check:.0f} ₴")
            
            # Топ товар
            top_products_df = processor.process_top_products(df)
            top_item = top_products_df.iloc[0, 0] if not top_products_df.empty else "-"
            m4.metric("Хіт продажів", top_item)

            # --- ГРАФІКИ ---
            c1, c2 = st.columns([2, 1])
            
            with c1:
                st.subheader("Динаміка по годинах")
                hourly_df = processor.process_hourly_sales(df)
                if not hourly_df.empty:
                    fig = px.bar(hourly_df, x='Година', y='Виторг', color='Виторг')
                    st.plotly_chart(fig, use_container_width=True)
            
            with c2:
                st.subheader("Топ товарів")
                if not top_products_df.empty:
                    fig_pie = px.pie(top_products_df, values='payed_sum', names=top_products_df.columns[0], hole=0.5)
                    st.plotly_chart(fig_pie, use_container_width=True)
        
        else:
            st.info("👈 Натисніть 'Оновити з БД', щоб завантажити дані з Google Таблиці.")

if __name__ == "__main__":
    main()
