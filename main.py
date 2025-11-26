import streamlit as st
import pandas as pd
from datetime import date
from modules.api_client import PosterClient
from modules.db_handler import GoogleSheetHandler
from modules.data_processor import DataProcessor

# Налаштування сторінки
st.set_page_config(
    page_title="Poster Analytics Dashboard",
    page_icon="📊",
    layout="wide"
)

def main():
    st.title("📊 Poster Analytics Dashboard")

    # Ініціалізація модулів
    poster_client = PosterClient()
    data_processor = DataProcessor()

    # --- САЙДБАР ---
    st.sidebar.header("1. Отримання даних")
    
    selected_date = st.sidebar.date_input(
        "Оберіть період",
        value=(date.today(), date.today()),
        max_value=date.today()
    )

    # Логіка завантаження даних
    if st.sidebar.button("Завантажити з Poster", type="primary"):
        if isinstance(selected_date, tuple) and len(selected_date) == 2:
            start_date, end_date = selected_date
            
            with st.spinner("Отримання даних з Poster..."):
                date_from_str = start_date.strftime("%Y-%m-%d")
                date_to_str = end_date.strftime("%Y-%m-%d")

                transactions = poster_client.get_transactions(date_from_str, date_to_str)

                if transactions:
                    df = pd.DataFrame(transactions)
                    st.session_state['df'] = df
                    st.success(f"Завантажено {len(transactions)} записів!")
                else:
                    st.warning("Даних не знайдено.")
        else:
            st.error("Будь ласка, оберіть коректний діапазон дат.")

    # Перевірка наявності даних
    if 'df' in st.session_state and not st.session_state['df'].empty:
        df = st.session_state['df']
        
        # --- ВКЛАДКИ ---
        tab1, tab2 = st.tabs(["📊 Дашборд", "📋 Сирі дані"])

        # === Вкладка 1: Дашборд ===
        with tab1:
            st.subheader("Аналітика продажів")
            
            col1, col2 = st.columns(2)

            # Графік 1: Продажі по годинах
            with col1:
                st.markdown("**💸 Динаміка виторгу по годинах**")
                hourly_sales = data_processor.process_hourly_sales(df)
                if not hourly_sales.empty:
                    st.line_chart(hourly_sales)
                else:
                    st.info("Недостатньо даних для графіку по годинах.")

            # Графік 2: Топ товарів
            with col2:
                st.markdown("**🏆 Топ-10 товарів (за сумою)**")
                # Перевіряємо, чи є дані про продукти
                if 'products' in df.columns:
                    top_products = data_processor.process_top_products(df)
                    if not top_products.empty:
                        # Streamlit bar_chart очікує індекс або конкретну колонку
                        st.bar_chart(top_products['payed_sum'])
                    else:
                        st.info("Не вдалося розрахувати топ товарів.")
                else:
                    st.warning("⚠️ Дані про товари відсутні.")
                    st.caption("У `api_client.py` встановіть `include_products: 1`.")

        # === Вкладка 2: Сирі дані та Експорт ===
        with tab2:
            st.subheader("📋 Детальна таблиця транзакцій")
            st.dataframe(df, use_container_width=True)

            st.divider()
            st.subheader("💾 Експорт в Google Sheets")

            col_exp_1, col_exp_2 = st.columns([2, 1])
            
            with col_exp_1:
                sheet_name = st.text_input(
                    "Назва Google Таблиці", 
                    value="Poster Data",
                    key="sheet_name_input"
                )
            
            with col_exp_2:
                st.write("") 
                st.write("") 
                if st.button("Записати в таблицю"):
                    with st.spinner("З'єднання з Google Sheets..."):
                        gs_handler = GoogleSheetHandler()
                        
                        # Перед записом конвертуємо складні об'єкти (списки/словники) в рядки,
                        # бо Google Sheets не приймає python objects
                        df_to_save = df.astype(str)
                        
                        success = gs_handler.write_data(df_to_save, sheet_name)
                        
                        if success:
                            st.success(f"Дані успішно записано в '{sheet_name}'!")
                            st.balloons()

if __name__ == "__main__":
    main()
    
