import pandas as pd
import streamlit as st

class DataProcessor:
    """
    Клас для обробки та агрегації даних.
    """

    def process_top_products(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Визначає топ-10 товарів.
        Розгортає вкладені списки товарів з колонки 'products'.
        """
        if df.empty or 'products' not in df.columns:
            return pd.DataFrame()

        try:
            # 1. Розгортаємо список (Explode):
            # Було:  [ID чека, [{товар1}, {товар2}]]
            # Стане: [ID чека, {товар1}]
            #        [ID чека, {товар2}]
            df_exploded = df.explode('products')
            
            # Видаляємо порожні значення (чеки без товарів)
            df_exploded = df_exploded.dropna(subset=['products'])
            
            if df_exploded.empty:
                return pd.DataFrame()

            # 2. Нормалізуємо JSON (перетворюємо словники в колонки)
            # Це створить колонки типу 'product_id', 'product_name', 'price' тощо
            products_data = pd.json_normalize(df_exploded['products'])
            
            # Перевіряємо, як Poster назвав колонку з назвою (зазвичай 'name' або 'product_name')
            name_col = 'product_name' if 'product_name' in products_data.columns else 'name'
            
            if name_col not in products_data.columns:
                return pd.DataFrame()

            # 3. Чистимо дані
            # payed_sum в Poster зазвичай в копійках
            products_data['payed_sum'] = pd.to_numeric(products_data.get('payed_sum', 0), errors='coerce') / 100
            products_data['count'] = pd.to_numeric(products_data.get('count', 0), errors='coerce')
            
            # 4. Групуємо по назві товару
            top_products = products_data.groupby(name_col)[['count', 'payed_sum']].sum()
            
            # 5. Сортуємо від найбільшого
            top_products = top_products.sort_values(by='payed_sum', ascending=False).head(10)
            
            return top_products

        except Exception as e:
            st.error(f"Помилка при обробці товарів: {e}")
            return pd.DataFrame()

    def process_hourly_sales(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Агрегує продажі по годинах.
        Виправлено обробку Timestamp (ms).
        """
        if df.empty or 'date_close' not in df.columns:
            return pd.DataFrame()

        try:
            temp_df = df.copy()

            # --- ВИПРАВЛЕННЯ ЧАСУ ---
            # Poster віддає Unix timestamp у мілісекундах (наприклад 1764099349518)
            temp_df['date_close'] = pd.to_datetime(temp_df['date_close'], unit='ms')
            
            # Витягуємо годину
            temp_df['hour'] = temp_df['date_close'].dt.hour
            
            # Визначаємо колонку суми
            sum_col = 'payed_sum' if 'payed_sum' in temp_df.columns else 'sum'
            
            # Конвертуємо копійки у гривні
            temp_df[sum_col] = pd.to_numeric(temp_df.get(sum_col, 0), errors='coerce') / 100
            
            # Групуємо
            hourly_sales = temp_df.groupby('hour')[sum_col].sum()
            
            return hourly_sales

        except Exception as e:
            st.error(f"Помилка при обробці годин: {e}")
            return pd.DataFrame()
