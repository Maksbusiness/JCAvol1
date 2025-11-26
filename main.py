import streamlit as st
import pandas as pd
from datetime import date, timedelta
from modules.api_client import PosterClient

# Налаштування сторінки
st.set_page_config(
    page_title="Poster Analytics Dashboard",
    page_icon="📊",
    layout="wide"
)

def main():
    st.title("📊 Poster Analytics: Перевірка зв'язку")

    # Ініціалізація клієнта
    client = PosterClient()

    # Сайдбар для фільтрів
    st.sidebar.header("Налаштування")
    
    # Вибір дати (за замовчуванням - сьогодні)
    selected_date = st.sidebar.date_input(
        "Оберіть період",
        value=(date.today(), date.today()),
        max_value=date.today()
    )

    # Перевірка коректності вибору дати (start і end)
    if isinstance(selected_date, tuple) and len(selected_date) == 2:
        start_date, end_date = selected_date
    else:
        st.info("Оберіть дату початку та кінця.")
        return

    # Кнопка завантаження
    if st.sidebar.button("Завантажити дані", type="primary"):
        with st.spinner("Отримання даних з Poster..."):
            # Форматуємо дати у стрічку YYYY-MM-DD
            date_from_str = start_date.strftime("%Y-%m-%d")
            date_to_str = end_date.strftime("%Y-%m-%d")

            # Отримуємо дані
            transactions = client.get_transactions(date_from_str, date_to_str)

            if transactions:
                st.success(f"Завантажено {len(transactions)} записів!")
                
                # Створюємо DataFrame для відображення
                df = pd.DataFrame(transactions)
                
                # Відображаємо таблицю
                st.subheader("📋 Останні транзакції")
                st.dataframe(df, use_container_width=True)
                
                # Виводимо сирий JSON першого запису для аналізу (для розробника)
                with st.expander("🔍 Подивитися структуру даних (JSON)"):
                    st.json(transactions[0])
            else:
                st.warning("За обраний період даних не знайдено або сталася помилка.")

if __name__ == "__main__":
    main()
