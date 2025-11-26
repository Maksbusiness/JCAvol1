import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

class DatabaseHandler:
    """
    Клас для роботи з PostgreSQL (Neon).
    Реалізує інкрементальне завантаження (перевірка на дублікати).
    """

    def __init__(self):
        try:
            # Очікується формат: postgresql://user:password@host:port/dbname
            # Переконайтесь, що у secrets.toml connection_string вказано правильно
            connection_string = st.secrets["db"]["connection_string"]
            self.engine = create_engine(connection_string)
            self.connected = True
        except Exception as e:
            st.error(f"🔌 Помилка підключення до БД: {e}")
            self.connected = False

    def save_data(self, df: pd.DataFrame, table_name: str, unique_col: str = None) -> bool:
        """
        Зберігає дані в SQL.
        
        Args:
            df: DataFrame з новими даними.
            table_name: Назва таблиці в БД.
            unique_col: Назва колонки з унікальним ID (напр. 'transaction_id'). 
                        Якщо None — просто додає дані (append).
        """
        if not self.connected or df.empty:
            return False

        try:
            # Конвертуємо складні об'єкти в строки, щоб SQL не лаявся
            df_safe = df.astype(str)

            # --- ЛОГІКА ПЕРЕВІРКИ ДУБЛІКАТІВ ---
            if unique_col:
                try:
                    # 1. Спробуємо отримати існуючі ID з бази
                    existing_ids_query = f"SELECT {unique_col} FROM {table_name}"
                    existing_df = pd.read_sql(existing_ids_query, self.engine)
                    
                    # Приводимо до string для коректного порівняння
                    existing_ids = existing_df[unique_col].astype(str).tolist()
                    
                    # 2. Фільтруємо нові дані: залишаємо тільки ті, яких немає в базі
                    # ~ означає "НЕ" (NOT in)
                    df_safe = df_safe[~df_safe[unique_col].astype(str).isin(existing_ids)]
                    
                    if df_safe.empty:
                        # Якщо всі дані вже є, нічого не робимо, але повертаємо True (успіх)
                        return True
                        
                except SQLAlchemyError:
                    # Якщо таблиці ще не існує, помилка SELECT - це нормально.
                    # Ми просто створимо нову таблицю з усіма даними.
                    pass

            # 3. Записуємо дані (додаємо до існуючих)
            df_safe.to_sql(table_name, self.engine, if_exists='append', index=False)
            
            return True

        except SQLAlchemyError as e:
            st.error(f"❌ Помилка SQL при запису в '{table_name}': {e}")
            return False
        except Exception as e:
            st.error(f"❌ Загальна помилка при запису '{table_name}': {e}")
            return False

    def load_data(self, table_name: str) -> pd.DataFrame:
        """
        Читає дані з SQL.
        """
        if not self.connected:
            return pd.DataFrame()

        try:
            query = f"SELECT * FROM {table_name}"
            return pd.read_sql(query, self.engine)
        except SQLAlchemyError:
            return pd.DataFrame()
        except Exception as e:
            st.warning(f"⚠️ Не вдалося завантажити '{table_name}': {e}")
            return pd.DataFrame()
