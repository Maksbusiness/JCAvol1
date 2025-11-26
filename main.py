import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date

# Імпорти модулів
from modules.api_client import PosterClient
from modules.db_handler import GoogleSheetHandler
from modules.data_processor import DataProcessor

# Налаштування сторінки
st.set_page_config(
    page_title="Poster Analytics Pro",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS STYLING (Card Design) ---
st.markdown("""
    <style>
    /* Стиль для метрик-карток */
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        border: 1px solid #f0f2f6;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    /* Заголовки графіків */
    .chart-title {
        font-size: 18px;
        font-weight: 600;
        color: #333;
        margin-bottom: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

def main():
    st.title("📈 Poster Analytics Pro")

    # Ініціалізація
    poster_client = PosterClient()
    data_processor = DataProcessor()

    # --- САЙДБАР ---
    st.sidebar.header("Налаштування")
    
    selected_date = st.sidebar.date_input(
        "Період аналізу",
        value=(date.today(), date.today()),
        max_value=date.today()
    )

    if st.sidebar.button("🔄 Оновити дані", type="primary"):
        if isinstance(selected_date, tuple) and len(selected_date) == 2:
            start_date, end_date = selected_date
            with st.spinner("Завантаження даних з Poster API..."):
                transactions = poster_client.get_transactions(
                    start_date.strftime("%Y-%m-%d"), 
                    end_date.strftime("%Y-%m-%d")
                )
                if transactions:
                    st.session_state['df'] = pd.DataFrame(transactions)
                    st.toast(f"Завантажено {len(transactions)} чеків!", icon="✅")
                else:
                    st.error("Даних не знайдено за цей період.")
        else:
            st.warning("Оберіть повний діапазон дат.")

    # --- ГОЛОВНИЙ ЕКРАН ---
    if 'df' in st.session_state and not st.session_state['df'].empty:
        df = st.session_state['df']
        
        # 1. Підготовка загальних метрик
        # Конвертуємо загальну суму чеків (вона в df в копійках)
        total_sum = pd.to_numeric(df.get('payed_sum', 0), errors='coerce').sum() / 100
        total_count = len(df)
        avg_check = total_sum / total_count if total_count > 0 else 0
        
        # Обробка топ-товару для метрики
        top_products_df = data_processor.process_top_products(df)
        top_item_name = "Немає даних"
        if not top_products_df.empty:
            # Беремо назву першого товару (ім'я колонки може бути product_name або name)
            top_item_name = top_products_df.iloc[0, 0] # Перша колонка, перший рядок

        # 2. ВІДОБРАЖЕННЯ МЕТРИК (КАРТКИ)
        st.markdown("### 📊 Ключові показники")
        m1, m2, m3, m4 = st.columns(4)
        
        m1.metric("Загальний виторг", f"{total_sum:,.0f} ₴")
        m2.metric("Кількість чеків", f"{total_count}")
        m3.metric("Середній чек", f"{avg_check:.0f} ₴")
        m4.metric("Топ товар", top_item_name)

        st.divider()

        # 3. ГРАФІКИ
        col_charts_1, col_charts_2 = st.columns([2, 1])

        # Графік 1: Погодинна динаміка (Bar Chart)
        with col_charts_1:
            st.markdown('<div class="chart-title">💸 Динаміка продажів по годинах</div>', unsafe_allow_html=True)
            hourly_df = data_processor.process_hourly_sales(df)
            
            if not hourly_df.empty:
                fig_bar = px.bar(
                    hourly_df, 
                    x='Година', 
                    y='Виторг',
                    text_auto='.2s', # Скорочений формат чисел на стовпчиках
                    color='Виторг',  # Градієнт
                    color_continuous_scale='Blues'
                )
                fig_bar.update_layout(
                    xaxis=dict(tickmode='linear', dtick=1), # Показувати кожну годину
                    showlegend=False,
                    height=400,
                    margin=dict(l=0, r=0, t=0, b=0)
                )
                st.plotly_chart(fig_bar, use_container_width=True)
            else:
                st.info("Немає даних для графіка.")

        # Графік 2: Топ товарів (Donut Chart)
        with col_charts_2:
            st.markdown('<div class="chart-title">🏆 Топ-7 товарів (частка)</div>', unsafe_allow_html=True)
            
            if not top_products_df.empty:
                # Визначаємо назву колонки з іменами (перша колонка)
                name_col = top_products_df.columns[0]
                
                fig_pie = px.pie(
                    top_products_df, 
                    values='payed_sum', 
                    names=name_col,
                    hole=0.6, # Робить "пончик"
                    color_discrete_sequence=px.colors.qualitative.Pastel
                )
                fig_pie.update_traces(textposition='inside', textinfo='percent+label')
                fig_pie.update_layout(
                    showlegend=False,
                    height=400,
                    margin=dict(l=0, r=0, t=0, b=0)
                )
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.warning("Товари не знайдено.")

        # 4. ТАБЛИЦЯ ТА ЕКСПОРТ (в експандері, щоб не заважало)
        with st.expander("📋 Детальна таблиця та Експорт в Google Sheets"):
            st.dataframe(df, use_container_width=True)
            
            col_exp_1, col_exp_2 = st.columns([3, 1])
            sheet_name = col_exp_1.text_input("Назва Google Таблиці", value="Poster Report")
            
            if col_exp_2.button("💾 Зберегти"):
                gs = GoogleSheetHandler()
                if gs.write_data(df.astype(str), sheet_name):
                    st.success("Збережено!")

if __name__ == "__main__":
    main()
