import pandas as pd
import streamlit as st
from typing import Optional

class DataProcessor:
    """
    Клас для обробки та агрегації даних для дашборду.
    """

    def process_top_products(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Визначає топ-10 товарів за сумою продажів.
        Потребує наявності колонки 'products' (include_products=1 в API).
        """
        # Перевірка наявності даних про товари
        if 'products' not in df.columns:
            return pd.DataFrame()

        try:
            # 1. "Вибухаємо" список продуктів: кожен товар стає окремим рядком
            # Poster повертає products як список словників всередині комірки
            df_exploded = df.explode('products')
            
            # Видаляємо рядки, де немає товарів (NaN)
            df_exploded = df_exploded.dropna(subset=['products'])
            
            if df_exploded.empty:
                return pd.DataFrame()

            # 2. Витягуємо дані зі словників у колонці 'products'
            # Нормалізація JSON структури
            products_data = pd.json_normalize(df_exploded['products'])
            
            # 3. Вибираємо потрібні колонки та приводимо типи
            # Зазвичай Poster повертає: name, count, payed_sum (або price)
            # payed_sum часто в копійках, тому ділимо на 100
            products_data['payed_sum'] = pd.to_numeric(products_data['payed_sum'], errors='coerce') / 100
            products_data['count'] = pd.to_numeric(products_data['count'], errors='coerce')
            
            # 4. Групуємо за назвою
            top_products = products_data.groupby('name')[['count', 'payed_sum']].sum()
            
            # 5. Сортуємо та беремо топ-10
            top_products = top_products.sort_values(by='payed_sum', ascending=False).head(10)
            
            return top_products

        except Exception as e:
            st.warning(f"Помилка при обробці товарів: {e}")
            return pd.DataFrame()

    def process_hourly_sales(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Агрегує суму продажів по годинах доби.
        """
        try:
            # Створюємо копію, щоб не змінювати оригінал
            temp_df = df.copy()

            # Конвертуємо дату закриття (Posters v3 date_close: 'YYYY-MM-DD HH:MM:SS')
            temp_df['date_close'] = pd.to_datetime(temp_df['date_close'])
            
            # Витягуємо годину (0-23)
            temp_df['hour'] = temp_df['date_close'].dt.hour
            
            # Визначаємо колонку з сумою (payed_sum або sum)
            sum_col = 'payed_sum' if 'payed_sum' in temp_df.columns else 'sum'
            
            # Конвертуємо в числа та ділимо на 100 (з копійок у гривні)
            temp_df[sum_col] = pd.to_numeric(temp_df[sum_col], errors='coerce') / 100
            
            # Групуємо
            hourly_sales = temp_df.groupby('hour')[sum_col].sum()
            
            return hourly_sales

        except Exception as e:
            st.error(f"Помилка при обробці погодинних продажів: {e}")
            return pd.DataFrame()import streamlit as st
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
