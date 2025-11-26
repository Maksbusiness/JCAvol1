import gspread
import json
import pandas as pd
import streamlit as st
from oauth2client.service_account import ServiceAccountCredentials
from gspread_dataframe import set_with_dataframe

class GoogleSheetHandler:
    """
    Клас для роботи з Google Sheets.
    Відповідає за I/O операції (читання/запис).
    """
    
    SCOPE = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]

    def __init__(self):
        try:
            creds_json = st.secrets["google"]["credentials_json"]
            creds_dict = json.loads(creds_json)
            
            if "private_key" in creds_dict:
                creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
            
            self.creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, self.SCOPE)
            self.client = gspread.authorize(self.creds)

        except Exception as e:
            st.error(f"Google Auth Error: {e}")
            st.stop()

    def _get_worksheet(self, sheet_name: str, tab_name: str, create_if_missing: bool = False):
        """Отримує або створює аркуш."""
        try:
            spreadsheet = self.client.open(sheet_name)
        except gspread.exceptions.SpreadsheetNotFound:
            st.error(f"❌ Таблицю '{sheet_name}' не знайдено на Google Drive.")
            return None

        try:
            return spreadsheet.worksheet(tab_name)
        except gspread.exceptions.WorksheetNotFound:
            if create_if_missing:
                return spreadsheet.add_worksheet(title=tab_name, rows=1000, cols=20)
            return None

    def write_data(self, df: pd.DataFrame, sheet_name: str, tab_name: str) -> bool:
        """
        Записує DataFrame у вкладку.
        Конвертує ВСЕ в рядки перед записом для уникнення JSON-помилок.
        """
        try:
            worksheet = self._get_worksheet(sheet_name, tab_name, create_if_missing=True)
            if not worksheet:
                return False

            worksheet.clear()
            
            # --- CRITICAL FIX: Serialization ---
            # Перетворюємо складні об'єкти (списки, дати, числа) на текст
            df_str = df.astype(str)
            
            set_with_dataframe(worksheet, df_str)
            return True
        except Exception as e:
            st.error(f"Write Error ({tab_name}): {e}")
            return False

    def read_data(self, sheet_name: str, tab_name: str) -> pd.DataFrame:
        """Читає дані з вкладки."""
        try:
            worksheet = self._get_worksheet(sheet_name, tab_name)
            if not worksheet:
                return pd.DataFrame() # Повертаємо пустий DF, якщо вкладки немає
            
            data = worksheet.get_all_records()
            return pd.DataFrame(data)
        except Exception as e:
            st.error(f"Read Error ({tab_name}): {e}")
            return pd.DataFrame()
