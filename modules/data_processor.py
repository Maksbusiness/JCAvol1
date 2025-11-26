import pandas as pd
import streamlit as st

class DataProcessor:
    """
    Клас для обробки та агрегації даних для дашборду.
    """

    def process_top_products(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Визначає топ-10 товарів за сумою продажів.
        """
        # 1. Перевірка на порожній DataFrame
        if df.empty:
            return pd.DataFrame()

        # 2. Перевірка наявності колонки з товарами
        if 'products' not in df.columns:
            # Якщо даних про товари немає, повертаємо пустий DF, але не ламаємо код
            return pd.DataFrame()

        try:
            # 3. Розгортаємо список продуктів (explode)
            # Poster повертає список словників у кожній комірці колонки 'products'
            df_exploded = df.explode('products')
            
            # Видаляємо порожні рядки
            df_exploded = df_exploded.dropna(subset=['products'])
            
            if df_exploded.empty:
                return pd.DataFrame()

            # 4. Нормалізуємо JSON структуру (словники перетворюємо на колонки)
            products_data = pd.json_normalize(df_exploded['products'])
            
            # Перевірка, чи є колонка 'name' у розгорнутих даних
            if 'name' not in products_data.columns:
                return pd.DataFrame()

            # 5. Приведення типів даних (сума часто в копійках)
            # Використовуємо .get(), щоб уникнути помилки KeyError
            products_data['payed_sum'] = pd.to_numeric(products_data.get('payed_sum', 0), errors='coerce') / 100
            products_data['count'] = pd.to_numeric(products_data.get('count', 0), errors='coerce')
            
            # 6. Групування та сортування
            top_products = products_data.groupby('name')[['count', 'payed_sum']].sum()
            top_products = top_products.sort_values(by='payed_sum', ascending=False).head(10)
            
            return top_products

        except Exception as e:
            st.error(f"Помилка при обробці товарів: {e}")
            return pd.DataFrame()

    def process_hourly_sales(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Агрегує суму продажів по годинах доби.
        """
        if df.empty:
            return pd.DataFrame()

        try:
            # Створюємо копію
            temp_df = df.copy()

            # Перевірка наявності колонки дати
            if 'date_close' not in temp_df.columns:
                return pd.DataFrame()

            # Конвертація дати
            temp_df['date_close'] = pd.to_datetime(temp_df['date_close'])
            
            # Витягуємо годину
            temp_df['hour'] = temp_df['date_close'].dt.hour
            
            # Шукаємо колонку з сумою (може бути 'payed_sum' або 'sum')
            sum_col = 'payed_sum' if 'payed_sum' in temp_df.columns else 'sum'
            
            # Конвертуємо в числа та ділимо на 100 (копійки -> гривні)
            temp_df[sum_col] = pd.to_numeric(temp_df.get(sum_col, 0), errors='coerce') / 100
            
            # Групуємо
            hourly_sales = temp_df.groupby('hour')[sum_col].sum()
            
            return hourly_sales

        except Exception as e:
            st.error(f"Помилка при обробці погодинних продажів: {e}")
            return pd.DataFrame()
