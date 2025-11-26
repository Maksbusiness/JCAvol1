import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

class DatabaseHandler:
    """
    Handles interactions with PostgreSQL (Supabase).
    Implements 'Data Lake' logic: Overwrites tables with fresh data.
    """

    def __init__(self):
        try:
            # Expected secret format: postgresql://user:password@host:port/dbname
            connection_string = st.secrets["db"]["connection_string"]
            self.engine = create_engine(connection_string)
            self.connected = True
        except Exception as e:
            st.error(f"🔌 DB Connection Error: {e}")
            self.connected = False

    def save_data(self, df: pd.DataFrame, table_name: str) -> bool:
        """
        Overwrites the SQL table with the provided DataFrame.
        Handles list/dict columns by converting them to strings to avoid SQL errors.
        """
        if not self.connected or df.empty:
            return False

        try:
            # Sanitize: SQL cannot store Python lists/dicts directly in standard columns.
            # We convert complex objects to strings to ensure safe storage.
            df_safe = df.astype(str)
            
            # if_exists='replace' drops the table and recreates it (Data Lake style)
            df_safe.to_sql(table_name, self.engine, if_exists='replace', index=False)
            return True
        except SQLAlchemyError as e:
            st.error(f"❌ Failed to save table '{table_name}': {e}")
            return False
        except Exception as e:
            st.error(f"❌ General Error saving '{table_name}': {e}")
            return False

    def load_data(self, table_name: str) -> pd.DataFrame:
        """
        Reads data from SQL. Returns empty DataFrame on failure to prevent App Crash.
        """
        if not self.connected:
            return pd.DataFrame()

        try:
            # Using text() for safe SQL execution
            query = f"SELECT * FROM {table_name}"
            return pd.read_sql(query, self.engine)
        except SQLAlchemyError:
            # This usually happens if the table doesn't exist yet
            # We return empty DF so the UI can simply say "No Data"
            return pd.DataFrame()
        except Exception as e:
            st.warning(f"⚠️ Could not load '{table_name}': {e}")
            return pd.DataFrame()
