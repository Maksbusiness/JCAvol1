import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date

from modules.api_client import PosterClient
from modules.db_handler import GoogleSheetHandler
from modules.data_processor import DataProcessor

st.set_page_config(page_title="Poster Analytics V1.0", page_icon="🚀", layout="wide")

# CSS: Чорний текст для карток
st.markdown("""
    <style>
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        border: 1px solid #ddd;
        padding: 10px;
        border-radius: 5px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    div[data-testid="stMetric"] label { color: #000000 !important; }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] { color: #000000 !important; }
    </style>
    """, unsafe_allow_html=True)

def main():
    st.title("🚀 Poster ERP Analytics")

    # Ініціалізація
    poster = PosterClient()
    gs = GoogleSheetHandler()
    processor = DataProcessor()

    # Вкладки
    tab_sync, tab_analytics = st.tabs(["⚙️ Синхронізація (ERP)", "📊 Аналітика"])

    # ==========================================
    # 1. СИНХРОНІЗАЦІЯ (SYNC)
    # ==========================================
    with tab_sync:
        st.header("Оновлення бази даних")
        st.info("Цей модуль завантажує дані з Poster API та зберігає їх у Google Sheets.")
        
        col1, col2 = st.columns([1, 2])
        with col1:
            sheet_name = st.text_input("Назва Google Таблиці", value="Poster ERP Data")
            
            entities = st.multiselect(
                "Оберіть сутності для оновлення:",
                ["Чеки (Transactions)", "Товари (Menu)", "Інгредієнти", "Постачальники", "Постачання"],
                default=["Чеки (Transactions)"]
            )
            
            date_range_sync = st.date_input(
                "Період (для документів)",
                value=(date.today(), date.today()),
                max_value=date.today()
            )
            
            btn_sync = st.button("🚀 Запустити", type="primary")

        with col2:
            if btn_sync:
                if len(date_range_sync) != 2:
                    st.error("Оберіть дату початку та кінця.")
                else:
                    d_start = date_range_sync[0].strftime("%Y-%m-%d")
                    d_end = date_range_sync[1].strftime("%Y-%m-%d")
                    
                    log = st.container()
                    
                    # --- SYNC LOGIC ---
                    
                    # 1. Transactions
                    if "Чеки (Transactions)" in entities:
                        data = poster.get_transactions(d_start, d_end)
                        if data:
                            gs.write_data(pd.DataFrame(data), sheet_name, "Transactions")
                            log.success(f"✅ Чеки: {len(data)} завантажено.")
                        else:
                            log.warning("⚠️ Чеки: немає даних.")

                    # 2. Products
                    if "Товари (Menu)" in entities:
                        data = poster.get_products()
                        if data:
                            gs.write_data(pd.DataFrame(data), sheet_name, "Products")
                            log.success(f"✅ Товари: {len(data)} завантажено.")
                    
                    # 3. Ingredients
                    if "Інгредієнти" in entities:
                        data = poster.get_ingredients()
                        if data:
                            gs.write_data(pd.DataFrame(data), sheet_name, "Ingredients")
                            log.success(f"✅ Інгредієнти: {len(data)} завантажено.")

                    # 4. Suppliers
                    if "Постачальники" in entities:
                        data = poster.get_suppliers()
                        if data:
                            gs.write_data(pd.DataFrame(data), sheet_name, "Suppliers")
                            log.success(f"✅ Постачальники: {len(data)} завантажено.")

                    # 5. Supplies
                    if "Постачання" in entities:
                        data = poster.get_supplies(d_start, d_end)
                        if data:
                            gs.write_data(pd.DataFrame(data), sheet_name, "Supplies")
                            log.success(f"✅ Постачання: {len(data)} завантажено.")

    # ==========================================
    # 2. АНАЛІТИКА (ANALYTICS)
    # ==========================================
    with tab_analytics:
        st.header("Дашборд продажів")
        
        # Завантаження даних
        if st.button("🔄 Оновити з Google Sheets"):
            with st.spinner("Читання бази даних..."):
                raw_df = gs.read_data(sheet_name, "Transactions")
                if not raw_df.empty:
                    # Попередня обробка (типи, гроші, статус)
                    clean_df = processor.prepare_transactions(raw_df)
                    st.session_state['clean_data'] = clean_df
                    st.toast("Дані успішно оновлено!", icon="🎉")
                else:
                    st.error("Вкладка 'Transactions' порожня або не знайдена.")

        st.divider()

        # Відображення
        if 'clean_data' in st.session_state:
            df = st.session_state['clean_data']
            
            # Фільтр дат для відображення
            min_date = df['date_close'].min().date()
            max_date = df['date_close'].max().date()
            
            date_filter = st.date_input(
                "Фільтр періоду",
                value=(min_date, max_date),
                min_value=min_date,
                max_value=max_date
            )
            
            # Фільтруємо вже чисті дані
            filtered_df = processor.get_filtered_data(df, date_filter)
            
            # KPI
            metrics = processor.calculate_kpi(filtered_df)
            
            m1, m2, m3 = st.columns(3)
            m1.metric("Виторг (Netto)", f"{metrics['revenue']:,.2f} ₴")
            m2.metric("Кількість чеків", f"{metrics['checks']}")
            m3.metric("Середній чек", f"{metrics['avg_check']:.2f} ₴")
            
            # Charts
            col_chart1, col_chart2 = st.columns([2, 1])
            
            with col_chart1:
                st.subheader("Динаміка по годинах")
                hourly = processor.get_hourly_sales(filtered_df)
                if not hourly.empty:
                    fig = px.bar(hourly, x='Година', y='Виторг', color='Виторг')
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("Немає даних для графіка.")

            with col_chart2:
                st.subheader("Топ товарів")
                top_prods = processor.get_top_products(filtered_df)
                if not top_prods.empty:
                    fig_pie = px.pie(
                        top_prods, 
                        values='real_sum', 
                        names=top_prods.columns[0], 
                        hole=0.6
                    )
                    st.plotly_chart(fig_pie, use_container_width=True)
                else:
                    st.info("Товари не знайдено.")

        else:
            st.info("👈 Натисніть 'Оновити з Google Sheets', щоб побудувати звіт.")

if __name__ == "__main__":
    main()
