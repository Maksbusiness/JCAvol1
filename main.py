import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date

from modules.api_client import PosterClient
from modules.db_handler import GoogleSheetHandler
from modules.data_processor import DataProcessor

st.set_page_config(page_title="Poster ERP Sync", page_icon="🔄", layout="wide")

# Стилі
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
    st.title("🔄 Poster ERP Connector")

    poster = PosterClient()
    gs = GoogleSheetHandler()
    processor = DataProcessor()

    tab_sync, tab_analytics = st.tabs(["⚙️ Синхронізація (ERP)", "📊 Аналітика"])

    # ==========================
    # Вкл 1: СИНХРОНІЗАЦІЯ
    # ==========================
    with tab_sync:
        st.header("Оновлення даних")
        st.info("Виберіть дані для завантаження в Google Sheets.")
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            sheet_name = st.text_input("Назва Google Таблиці", value="Poster ERP Data")
            
            entities = st.multiselect(
                "Сутності:",
                ["Чеки", "Товари", "Інгредієнти", "Постачальники", "Постачання"],
                default=["Чеки"]
            )
            
            date_range = st.date_input(
                "Період вибірки",
                value=(date.today(), date.today()),
                max_value=date.today()
            )
            
            start_btn = st.button("🚀 Запустити", type="primary")

        with col2:
            if start_btn:
                # Валідація дати
                if not (isinstance(date_range, tuple) and len(date_range) == 2):
                    st.error("Оберіть повний діапазон дат.")
                    st.stop()
                
                d_start = date_range[0].strftime("%Y-%m-%d")
                d_end = date_range[1].strftime("%Y-%m-%d")

                # Використовуємо st.status для групування логів
                with st.status("⏳ Виконується синхронізація...", expanded=True) as status:
                    
                    # 1. ЧЕКИ
                    if "Чеки" in entities:
                        st.write("📥 Завантажую чеки...")
                        data = poster.get_transactions(d_start, d_end)
                        if data:
                            df = pd.DataFrame(data)
                            gs.write_data(df.astype(str), sheet_name, "Transactions")
                            st.write(f"✅ Чеки: {len(data)} записів.")
                        else:
                            st.write("⚠️ Чеки: даних не знайдено.")

                    # 2. ТОВАРИ
                    if "Товари" in entities:
                        st.write("📥 Завантажую меню...")
                        data = poster.get_products()
                        if data:
                            df = pd.DataFrame(data)
                            gs.write_data(df.astype(str), sheet_name, "Products")
                            st.write(f"✅ Товари: {len(data)} записів.")
                    
                    # 3. ІНГРЕДІЄНТИ
                    if "Інгредієнти" in entities:
                        st.write("📥 Завантажую інгредієнти...")
                        data = poster.get_ingredients()
                        if data:
                            df = pd.DataFrame(data)
                            gs.write_data(df.astype(str), sheet_name, "Ingredients")
                            st.write(f"✅ Інгредієнти: {len(data)} записів.")

                    # 4. ПОСТАЧАЛЬНИКИ
                    if "Постачальники" in entities:
                        st.write("📥 Завантажую постачальників...")
                        data = poster.get_suppliers()
                        if data:
                            df = pd.DataFrame(data)
                            gs.write_data(df.astype(str), sheet_name, "Suppliers")
                            st.write(f"✅ Постачальники: {len(data)} записів.")

                    # 5. ПОСТАЧАННЯ
                    if "Постачання" in entities:
                        st.write("📥 Завантажую накладні...")
                        data = poster.get_supplies(d_start, d_end)
                        if data:
                            df = pd.DataFrame(data)
                            gs.write_data(df.astype(str), sheet_name, "Supplies")
                            st.write(f"✅ Постачання: {len(data)} записів.")

                    status.update(label="🎉 Синхронізацію завершено!", state="complete", expanded=False)
                
                st.success("Дані успішно збережено в Google Sheets!")

    # ==========================
    # Вкл 2: АНАЛІТИКА
    # ==========================
    with tab_analytics:
        st.header("Аналітика продажів")
        
        if st.button("🔄 Завантажити з БД"):
            with st.spinner("Зчитування даних..."):
                raw_df = gs.read_data(sheet_name, "Transactions")
                if not raw_df.empty:
                    clean_df = processor.prepare_transactions(raw_df)
                    st.session_state['data'] = clean_df
                else:
                    st.warning("Таблиця 'Transactions' порожня.")

        st.divider()

        if 'data' in st.session_state:
            df = st.session_state['data']
            
            # Фільтри
            d_min = df['date_close'].min().date()
            d_max = df['date_close'].max().date()
            
            filter_range = st.date_input("Період звіту", value=(d_min, d_max), min_value=d_min, max_value=d_max)
            
            # Обробка та відображення
            filtered_df = processor.get_filtered_data(df, filter_range)
            kpi = processor.calculate_kpi(filtered_df)
            
            k1, k2, k3 = st.columns(3)
            k1.metric("Виторг", f"{kpi['revenue']:,.2f} ₴")
            k2.metric("Чеки", kpi['checks'])
            k3.metric("Сер. чек", f"{kpi['avg_check']:.2f} ₴")
            
            c1, c2 = st.columns([2, 1])
            with c1:
                st.subheader("Динаміка")
                h_df = processor.get_hourly_sales(filtered_df)
                if not h_df.empty:
                    st.plotly_chart(px.bar(h_df, x='Година', y='Виторг'), use_container_width=True)
            with c2:
                st.subheader("Топ товарів")
                top_df = processor.get_top_products(filtered_df)
                if not top_df.empty:
                    st.plotly_chart(px.pie(top_df, values='real_sum', names=top_df.columns[0], hole=0.5), use_container_width=True)

if __name__ == "__main__":
    main()
