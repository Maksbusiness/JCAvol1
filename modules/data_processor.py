import pandas as pd
import streamlit as st

class DataProcessor:
    """
    Клас для обробки та агрегації даних для дашборду.
    """

    def process_top_products(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Повертає Топ-7 товарів.
        Логіка: Explode списку продуктів -> Нормалізація JSON -> Групування.
        """
        # Перевірки на цілісність даних
        if df.empty or 'products' not in df.columns:
            return pd.DataFrame()

        try:
            # 1. Розгортаємо список продуктів (один рядок = один товар у чеку)
            # Використовуємо dropna, бо можуть бути сервісні чеки без товарів
            df_exploded = df.explode('products').dropna(subset=['products'])
            
            if df_exploded.empty:
                return pd.DataFrame()

            # 2. Нормалізація: перетворюємо колонку словників у повноцінний DataFrame
            # product_details матиме колонки: product_id, product_name, count, payed_sum і т.д.
            product_details = pd.json_normalize(df_exploded['products'])

            # 3. Визначаємо правильні назви колонок (Poster іноді змінює ключі)
            name_col = 'product_name' if 'product_name' in product_details.columns else 'name'
            
            if name_col not in product_details.columns:
                return pd.DataFrame()

            # 4. Конвертація числових типів
            # payed_sum у товарах теж в копійках
            product_details['payed_sum'] = pd.to_numeric(product_details.get('payed_sum', 0), errors='coerce') / 100
            product_details['count'] = pd.to_numeric(product_details.get('count', 0), errors='coerce')

            # 5. Групування
            top_products = product_details.groupby(name_col)[['payed_sum', 'count']].sum()
            
            # 6. Сортування та вибірка топ-7
            top_products = top_products.sort_values(by='payed_sum', ascending=False).head(7)
            
            # Повертаємо index в колонку, щоб Plotly міг брати назви
            return top_products.reset_index()

        except Exception as e:
            st.error(f"Помилка при обробці товарів: {e}")
            return pd.DataFrame()

    def process_hourly_sales(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Агрегує продажі по годинах для графіка.
        """
        if df.empty or 'date_close' not in df.columns:
            return pd.DataFrame()

        try:
            temp_df = df.copy()

            # Конвертуємо час з мілісекунд
            temp_df['date_close'] = pd.to_datetime(temp_df['date_close'], unit='ms')
            
            # Витягуємо годину
            temp_df['hour'] = temp_df['date_close'].dt.hour
            
            # Визначаємо колонку суми
            sum_col = 'payed_sum' if 'payed_sum' in temp_df.columns else 'sum'
            
            # Конвертуємо у гривні
            temp_df[sum_col] = pd.to_numeric(temp_df.get(sum_col, 0), errors='coerce') / 100
            
            # Групуємо (reset_index важливий для Plotly)
            hourly_sales = temp_df.groupby('hour')[sum_col].sum().reset_index()
            
            # Перейменовуємо колонки для краси
            hourly_sales.columns = ['Година', 'Виторг']
            
            return hourly_sales

        except Exception as e:
            st.error(f"Помилка при обробці годин: {e}")
            return pd.DataFrame()
