import pandas as pd
import streamlit as st
import ast  # Бібліотека для безпечного парсингу стрічок "[...]" у список

class DataProcessor:
    """
    Обробка даних, отриманих з БД (Google Sheets).
    """

    def _safe_literal_eval(self, val):
        """Перетворює рядок списку назад у список Python."""
        if pd.isna(val) or val == "":
            return []
        if isinstance(val, list):
            return val
        try:
            return ast.literal_eval(val)
        except (ValueError, SyntaxError):
            return []

    def process_top_products(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Топ товарів. Враховує, що дані прийшли з Google Sheets (все - текст).
        """
        if df.empty or 'products' not in df.columns:
            return pd.DataFrame()

        try:
            # Створюємо копію
            temp_df = df.copy()

            # 1. Відновлюємо список продуктів зі стрічки
            # Google Sheet зберігає: "[{'id':1, ...}, {'id':2...}]" як текст
            temp_df['products'] = temp_df['products'].apply(self._safe_literal_eval)

            # 2. Explode
            df_exploded = temp_df.explode('products').dropna(subset=['products'])
            if df_exploded.empty:
                return pd.DataFrame()

            # 3. Normalize
            product_details = pd.json_normalize(df_exploded['products'])

            name_col = 'product_name' if 'product_name' in product_details.columns else 'name'
            if name_col not in product_details.columns:
                return pd.DataFrame()

            # 4. Конвертація чисел (обов'язкова після читання з Sheets)
            product_details['payed_sum'] = pd.to_numeric(product_details.get('payed_sum', 0), errors='coerce') / 100
            product_details['count'] = pd.to_numeric(product_details.get('count', 0), errors='coerce')

            # 5. Group & Sort
            top_products = product_details.groupby(name_col)[['payed_sum', 'count']].sum()
            top_products = top_products.sort_values(by='payed_sum', ascending=False).head(7)
            
            return top_products.reset_index()

        except Exception as e:
            st.error(f"Processor Error (Products): {e}")
            return pd.DataFrame()

    def process_hourly_sales(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Погодинні продажі.
        """
        if df.empty or 'date_close' not in df.columns:
            return pd.DataFrame()

        try:
            temp_df = df.copy()

            # --- ВИПРАВЛЕННЯ ДАТИ ---
            # Прибираємо unit='ms', дозволяємо Pandas самому розібратися
            temp_df['date_close'] = pd.to_datetime(temp_df['date_close'], errors='coerce')
            
            # Видаляємо некоректні дати
            temp_df = temp_df.dropna(subset=['date_close'])
            
            # Година
            temp_df['hour'] = temp_df['date_close'].dt.hour
            
            # --- ВИПРАВЛЕННЯ ЧИСЕЛ ---
            sum_col = 'payed_sum' if 'payed_sum' in temp_df.columns else 'sum'
            
            # З Google Sheets числа можуть прийти як "12500" (str)
            temp_df[sum_col] = pd.to_numeric(temp_df.get(sum_col, 0), errors='coerce') / 100
            
            # Групування
            hourly_sales = temp_df.groupby('hour')[sum_col].sum().reset_index()
            hourly_sales.columns = ['Година', 'Виторг']
            
            return hourly_sales

        except Exception as e:
            st.error(f"Processor Error (Hourly): {e}")
            return pd.DataFrame()
