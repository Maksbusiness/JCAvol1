import pandas as pd
import streamlit as st
import ast  # Для безпечного парсингу списків зі стрічок

class DataProcessor:
    """
    Клас для очищення, типізації та агрегації даних.
    """

    def _safe_literal_eval(self, val):
        """Перетворює рядок списку '[...]' назад у список Python."""
        if pd.isna(val) or str(val).strip() == "":
            return []
        try:
            return ast.literal_eval(val)
        except (ValueError, SyntaxError):
            return []

    def _clean_currency(self, val):
        """Перетворює рядок/число у float (копійки -> гривні)."""
        try:
            # Видаляємо пробіли, замінюємо коми
            clean_val = str(val).replace(" ", "").replace(",", ".")
            # Конвертуємо у float і ділимо на 100 (бо Poster дає копійки)
            return float(clean_val) / 100.0
        except (ValueError, TypeError):
            return 0.0

    def prepare_transactions(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Готує сирий DataFrame транзакцій до аналітики:
        1. Парсинг дат.
        2. Конвертація грошей.
        3. Фільтрація статусів (тільки успішні).
        """
        if df.empty:
            return pd.DataFrame()

        try:
            # Робимо копію
            df = df.copy()

            # 1. Дата (Pandas сам розбереться з форматом 'YYYY-MM-DD HH:MM:SS')
            df['date_close'] = pd.to_datetime(df['date_close'], errors='coerce')
            
            # Видаляємо рядки без дати
            df = df.dropna(subset=['date_close'])

            # 2. Статус (залишаємо тільки 2 - закриті/успішні)
            if 'status' in df.columns:
                df['status'] = pd.to_numeric(df['status'], errors='coerce')
                df = df[df['status'] == 2]

            # 3. Гроші (payed_sum)
            col_sum = 'payed_sum' if 'payed_sum' in df.columns else 'sum'
            df['clean_revenue'] = df[col_sum].apply(self._clean_currency)

            return df

        except Exception as e:
            st.error(f"Data Prep Error: {e}")
            return pd.DataFrame()

    def get_filtered_data(self, df: pd.DataFrame, date_range: tuple) -> pd.DataFrame:
        """Фільтрує підготовлений DF за діапазоном дат."""
        if df.empty or len(date_range) != 2:
            return df
        
        start_date = pd.to_datetime(date_range[0])
        # Додаємо час 23:59:59 до кінцевої дати, щоб включити весь день
        end_date = pd.to_datetime(date_range[1]) + pd.Timedelta(days=1, microseconds=-1)
        
        mask = (df['date_close'] >= start_date) & (df['date_close'] <= end_date)
        return df.loc[mask]

    def calculate_kpi(self, df: pd.DataFrame) -> dict:
        """Рахує основні метрики."""
        if df.empty:
            return {"revenue": 0, "checks": 0, "avg_check": 0}
        
        revenue = df['clean_revenue'].sum()
        checks = df['transaction_id'].nunique() # Рахуємо унікальні ID
        avg_check = revenue / checks if checks > 0 else 0
        
        return {
            "revenue": revenue,
            "checks": checks,
            "avg_check": avg_check
        }

    def get_top_products(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Рахує топ-7 товарів.
        Включає складний парсинг колонки 'products' (string -> list -> explode).
        """
        if df.empty or 'products' not in df.columns:
            return pd.DataFrame()

        try:
            temp_df = df.copy()
            
            # 1. Відновлюємо списки
            temp_df['products'] = temp_df['products'].apply(self._safe_literal_eval)
            
            # 2. Explode
            exploded = temp_df.explode('products').dropna(subset=['products'])
            
            if exploded.empty:
                return pd.DataFrame()

            # 3. Normalize
            items = pd.json_normalize(exploded['products'])
            
            # Шукаємо назву
            name_col = 'product_name' if 'product_name' in items.columns else 'name'
            if name_col not in items.columns:
                return pd.DataFrame()

            # 4. Гроші товару (теж в копійках!)
            items['real_sum'] = items.get('payed_sum', 0).apply(self._clean_currency)
            
            # 5. Групуємо
            top = items.groupby(name_col)['real_sum'].sum().reset_index()
            top = top.sort_values(by='real_sum', ascending=False).head(7)
            
            return top

        except Exception as e:
            st.warning(f"Product Calc Warning: {e}")
            return pd.DataFrame()
            
    def get_hourly_sales(self, df: pd.DataFrame) -> pd.DataFrame:
        """Динаміка по годинах."""
        if df.empty: return pd.DataFrame()
        
        try:
            df['hour'] = df['date_close'].dt.hour
            hourly = df.groupby('hour')['clean_revenue'].sum().reset_index()
            hourly.columns = ['Година', 'Виторг']
            return hourly
        except:
            return pd.DataFrame()
