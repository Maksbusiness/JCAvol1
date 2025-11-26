import streamlit as st
import pandas as pd
from datetime import date
from modules.api_client import PosterClient
from modules.db_handler import GoogleSheetHandler

# Налаштування сторінки
st.set_page_config(
    page_title="Poster Analytics Dashboard",
    page_icon="📊",
    layout="wide"
)

def main():
    st.title("📊 Poster Analytics Dashboard")

    # Ініціалізація клієнта Poster
    poster_client = PosterClient()

    # --- САЙДБАР ---
    st.sidebar.header("1. Отримання даних")
    
    # Вибір дати
    selected_date = st.sidebar.date_input(
        "Оберіть період",
        value=(date.today(), date.today()),
        max_value=date.today()
    )

    data_loaded = False
    df = pd.DataFrame()

    # Кнопка завантаження з API
    if st.sidebar.button("Завантажити з Poster", type="primary"):
        if isinstance(selected_date, tuple) and len(selected_date) == 2:
            start_date, end_date = selected_date
            
            with st.spinner("Отримання даних з Poster..."):
                date_from_str = start_date.strftime("%Y-%m-%d")
                date_to_str = end_date.strftime("%Y-%m-%d")

                transactions = poster_client.get_transactions(date_from_str, date_to_str)

                if transactions:
                    df = pd.DataFrame(transactions)
                    # Зберігаємо в сесії, щоб дані не зникали при перезавантаженні сторінки (наприклад, при кліку на кнопку збереження)
                    st.session_state['df'] = df
                    st.success(f"Завантажено {len(transactions)} записів!")
                else:
                    st.warning("Даних не знайдено.")
        else:
            st.error("Будь ласка, оберіть коректний діапазон дат.")

    # Перевіряємо, чи є дані в сесії
    if 'df' in st.session_state and not st.session_state['df'].empty:
        df = st.session_state['df']
        data_loaded = True

    # --- ОСНОВНА ЧАСТИНА ---
    if data_loaded:
        st.subheader("📋 Попередній перегляд даних")
        st.dataframe(df, use_container_width=True)

        st.divider()
        st.subheader("💾 2. Експорт в Google Sheets")

        col1, col2 = st.columns([2, 1])
        
        with col1:
            sheet_name = st.text_input(
                "Назва Google Таблиці", 
                value="Poster Data",
                help="Таблиця має бути вже створена на вашому Google Диску"
            )
        
        with col2:
            st.write("") # Відступ для вирівнювання
            st.write("") 
            if st.button("Записати в таблицю"):
                with st.spinner("З'єднання з Google Sheets..."):
                    # Ініціалізація хендлера
                    gs_handler = GoogleSheetHandler()
                    
                    # Спроба запису
                    success = gs_handler.write_data(df, sheet_name)
                    
                    if success:
                        st.success(f"Дані успішно записано в '{sheet_name}'!")
                        st.balloons()

if __name__ == "__main__":
    main()
